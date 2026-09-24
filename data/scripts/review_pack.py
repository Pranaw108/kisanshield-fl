"""Expert review pack: HTML image sheets + CSV forms for the agronomist, and import of their answers.

    # 1. create the pack in <data-root>/review/<manifest version>/
    python data/scripts/review_pack.py build --data-root E:/Datasets

    # 2. after the expert fills a CSV form, turn it into manifest overrides
    python data/scripts/review_pack.py import E:/Datasets/review/public_v2/label_audit.csv --decided-by "Dr. Name"

Review tasks:
    label_audit      sample of usable images per (dataset, label): is the label right?
    soynet_relabel   every SoyNet diseased photo: which disease is it?

Verdicts the expert may use (one per row):
    correct        the current class is right                      -> nothing changes
    wrong          plus correct_class: the right class             -> image is used with that class
    label          plus correct_class: photo had no class yet      -> image is used with that class
    wrong_unknown  class is wrong, right one unknown               -> image excluded
    not_a_leaf     not a crop leaf or plant                        -> image excluded
    unusable       too blurry, dark or damaged to judge            -> image excluded
    unsure         cannot decide                                   -> image held out of training
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_manifest as bm  # noqa: E402

FORM_FIELDS = ["manifest_version", "image_id", "dataset_id", "crop", "source_label", "current_class",
               "verdict", "correct_class", "notes"]
OVERRIDE_FIELDS = ["image_id", "action", "class_id", "reason", "decided_by", "decided_at", "status"]
HISTORY_PATH = bm.DEFAULT_OVERRIDES.with_name("review_history.csv")

# verdict -> (manifest action, correct_class required?)
VERDICTS = {
    "correct": (None, False),
    "wrong": ("use", True),
    "label": ("use", True),
    "wrong_unknown": ("exclude", False),
    "not_a_leaf": ("exclude", False),
    "unusable": ("exclude", False),
    "unsure": ("hold", False),
}
# manifest crop -> taxonomy crop
CROP_ALIASES = {"chickpea": "pulses", "pea": "pulses", "urd": "pulses", "moong": "pulses"}
THUMB_DIR = "thumbs_384"   # written by build_thumbnails.py
NO_CLASS = "(none)"
DEFAULT_AUDIT_PER_GROUP = 50


def load_classes_by_crop(path: Path) -> dict[str, set[str]]:
    """Taxonomy classes the model can predict, grouped by crop ('all' classes fit every crop)."""
    by_crop: dict[str, set[str]] = {}
    with path.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["in_model"] == "true"]
    shared = {r["class_id"] for r in rows if r["crop"] == "all"}
    for r in rows:
        by_crop.setdefault(r["crop"], set()).add(r["class_id"])
    return {crop: ids | shared for crop, ids in by_crop.items()} | {"all": shared}


def allowed_classes(by_crop: dict[str, set[str]], crop: str) -> set[str]:
    return by_crop.get(CROP_ALIASES.get(crop, crop), by_crop["all"])


def load_review_config(path: Path) -> tuple[int, dict[tuple[str, str], int]]:
    cfg = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("review") or {}
    overrides = {(o["dataset_id"], o["source_label"]): int(o["sample_size"])
                 for o in cfg.get("audit_overrides", [])}
    return int(cfg.get("audit_per_group", DEFAULT_AUDIT_PER_GROUP)), overrides


def write_sheet(path: Path, title: str, intro: str, df: pd.DataFrame, by_crop: dict[str, set[str]]) -> None:
    """Static HTML page of thumbnails; images load from the local thumbnail cache."""
    tiles = []
    for r in df.itertuples():
        src = f"../../cache/{THUMB_DIR}/{r.image_id}.jpg"
        tiles.append(
            f'<figure><a href="{src}" target="_blank"><img loading="lazy" src="{src}"></a>'
            f"<figcaption><b>{r.image_id}</b><br>{html.escape(str(r.dataset_id))}<br>"
            f"{html.escape(str(r.source_label))} → {html.escape(str(r.current_class))}</figcaption></figure>"
        )
    classes = sorted(set().union(*(allowed_classes(by_crop, c) for c in df["crop"].unique())))
    verdicts = "<br>".join(f"<code>{v}</code> → {d}" for v, d in [
        ("correct", "current class is right"), ("wrong / label", "+ correct_class: the right class"),
        ("wrong_unknown", "class is wrong, right one unknown"), ("not_a_leaf", "not a crop leaf"),
        ("unusable", "too blurry or dark to judge"), ("unsure", "cannot decide")])
    path.write_text(f"""<!doctype html><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{font:14px system-ui,sans-serif;margin:24px;background:#faf8f3;color:#1c1b17}}
h1{{font-family:Georgia,serif}} .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}}
figure{{margin:0;background:#fff;border:1px solid #e4dfd2;border-radius:8px;padding:8px}}
img{{width:100%;height:200px;object-fit:contain;background:#f1ede1}} figcaption{{font:12px monospace;margin-top:6px}}
.note{{background:#f5e6d3;border-left:3px solid #a05a1e;padding:10px 14px;margin:12px 0}}
code{{background:#f1ede1;padding:1px 4px;border-radius:3px}}
</style>
<h1>{html.escape(title)}</h1>
<div class="note">{intro}<br>Click an image to open it larger.<br><br>
<b>Verdicts:</b><br>{verdicts}<br><br>
<b>Class ids for this sheet:</b> {", ".join(classes)}</div>
<p>{len(df):,} images · manifest {bm.MANIFEST_VERSION}</p><div class="grid">{"".join(tiles)}</div>""",
                    encoding="utf-8")


def write_form(path: Path, df: pd.DataFrame, force: bool) -> None:
    if path.exists() and not force:
        print(f"  kept existing form (may contain answers): {path}")
        return
    if path.exists() and force and any(row.get("verdict") for row in csv.DictReader(path.open(encoding="utf-8"))):
        raise SystemExit(f"refusing --force: {path} already has answered rows. Review or move it first.")
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FORM_FIELDS)
        w.writeheader()
        for r in df.itertuples():
            w.writerow({"manifest_version": bm.MANIFEST_VERSION, "image_id": r.image_id,
                        "dataset_id": r.dataset_id, "crop": r.crop, "source_label": r.source_label,
                        "current_class": r.current_class})


def build(args: argparse.Namespace) -> int:
    manifest = args.data_root / "manifests" / f"manifest_{bm.MANIFEST_VERSION}.csv"
    if not manifest.exists():
        print(f"manifest not found: {manifest} (run build_manifest.py first)")
        return 1
    m = pd.read_csv(manifest, dtype={"source_label": str}, keep_default_na=False)
    m["current_class"] = m["class_id"].where(m["class_id"] != "", NO_CLASS)
    by_crop = load_classes_by_crop(bm.DEFAULT_TAXONOMY)
    per_group, overrides = load_review_config(bm.DEFAULT_CONFIG)

    out = args.data_root / "review" / bm.MANIFEST_VERSION
    out.mkdir(parents=True, exist_ok=True)

    shuffled = m[(m.status == "use") & (m.source_label != "")].sample(frac=1, random_state=7)
    rank = shuffled.groupby(["dataset_id", "source_label"]).cumcount()
    limit = [overrides.get(k, per_group) for k in zip(shuffled.dataset_id, shuffled.source_label)]
    audit = shuffled[rank < limit].sort_values(["dataset_id", "source_label"])
    write_sheet(out / "label_audit.html", "Label audit",
                "Check each image against its current class. Fill <code>label_audit.csv</code>.", audit, by_crop)
    write_form(out / "label_audit.csv", audit, args.force)

    soy = m[(m.dataset_id == "soynet") & (m.status == "hold")].sort_values("member_path")
    write_sheet(out / "soynet_relabel.html", "SoyNet: diseased photos to label",
                "These Jabalpur photos are only marked 'diseased'. Use verdict <code>label</code> plus the disease "
                "class id in <b>correct_class</b>. Fill <code>soynet_relabel.csv</code>.", soy, by_crop)
    write_form(out / "soynet_relabel.csv", soy, args.force)

    thumbs = args.data_root / "cache" / THUMB_DIR
    missing = sum(1 for i in [*audit.image_id, *soy.image_id] if not (thumbs / f"{i}.jpg").exists())
    if missing:
        print(f"WARNING: {missing} thumbnails are missing; run build_thumbnails.py or the sheets show gaps")
    print(f"Review pack written to {out}: label_audit ({len(audit):,} images), soynet_relabel ({len(soy):,} images)")
    return 0


def check_row(n: int, r: dict, known: dict[str, str], by_crop: dict[str, set[str]]) -> tuple[list[str], tuple | None]:
    """Validate one filled form row. Returns (errors, override or None)."""
    verdict = (r.get("verdict") or "").strip().lower()
    correct = (r.get("correct_class") or "").strip()
    image_id = (r.get("image_id") or "").strip()
    errors: list[str] = []
    if not verdict:
        return [], None  # not reviewed yet
    if verdict not in VERDICTS:
        return [f"line {n}: unknown verdict {verdict!r}; use one of {', '.join(sorted(VERDICTS))}"], None
    if image_id not in known:
        return [f"line {n}: image_id {image_id!r} is not in manifest {bm.MANIFEST_VERSION}"], None
    if (r.get("manifest_version") or bm.MANIFEST_VERSION).strip() != bm.MANIFEST_VERSION:
        return [f"line {n}: form was built for manifest {r['manifest_version']!r}, current is "
                f"{bm.MANIFEST_VERSION}; rebuild the review pack"], None

    action, needs_class = VERDICTS[verdict]
    permitted = allowed_classes(by_crop, known[image_id])
    if needs_class and not correct:
        errors.append(f"line {n}: verdict '{verdict}' needs correct_class")
    elif not needs_class and correct:
        errors.append(f"line {n}: verdict '{verdict}' must leave correct_class empty")
    elif correct and correct not in permitted:
        errors.append(f"line {n}: class {correct!r} is not valid for crop {known[image_id]!r} "
                      f"(allowed: {', '.join(sorted(permitted))})")
    if verdict == "correct" and (r.get("current_class") or NO_CLASS).strip() == NO_CLASS:
        errors.append(f"line {n}: this image has no class yet; use 'label' with correct_class instead of 'correct'")
    if errors or action is None:
        return errors, None
    return [], (image_id, action, correct, f"expert_{verdict}")


def import_form(args: argparse.Namespace) -> int:
    """Convert a filled form into rows of data/review/image_overrides.csv (plus an append-only history)."""
    manifest = args.data_root / "manifests" / f"manifest_{bm.MANIFEST_VERSION}.csv"
    if not manifest.exists():
        print(f"manifest not found: {manifest}")
        return 1
    if not args.form.exists():
        print(f"form not found: {args.form}")
        return 1
    with manifest.open(encoding="utf-8") as fh:
        known = {r["image_id"]: r["crop"] for r in csv.DictReader(fh)}
    by_crop = load_classes_by_crop(bm.DEFAULT_TAXONOMY)

    new_rows, errors = [], []
    with args.form.open(encoding="utf-8", newline="") as fh:
        for n, r in enumerate(csv.DictReader(fh), start=2):
            row_errors, override = check_row(n, r, known, by_crop)
            errors.extend(row_errors)
            if override:
                new_rows.append(override)
    if errors:
        print(f"{len(errors)} problem(s) found, nothing imported:\n  " + "\n  ".join(errors[:40]))
        return 1

    decided_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    target = bm.DEFAULT_OVERRIDES
    existing: dict[str, dict] = {}
    if target.exists():
        with target.open(encoding="utf-8", newline="") as fh:
            existing = {r["image_id"]: r for r in csv.DictReader(fh)}
    fresh = [{"image_id": i, "action": a, "class_id": c, "reason": f"{why}:{args.form.stem}",
              "decided_by": args.decided_by, "decided_at": decided_at, "status": "approved"}
             for i, a, c, why in new_rows]
    for row in fresh:  # newest decision for an image wins; the history file keeps the older ones
        existing[row["image_id"]] = row

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=OVERRIDE_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(sorted(existing.values(), key=lambda r: (r["reason"], r["image_id"])))
    with HISTORY_PATH.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=OVERRIDE_FIELDS, extrasaction="ignore")
        if HISTORY_PATH.stat().st_size == 0:
            w.writeheader()
        w.writerows(fresh)

    print(f"{len(fresh)} decisions imported to {target} (history: {HISTORY_PATH.name}). "
          f"Re-run build_manifest.py to apply them.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, help_text in [("build", "create HTML sheets and blank CSV forms"),
                            ("import", "turn a filled CSV form into image overrides")]:
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument("--data-root", type=Path, default=os.environ.get("KISANSHIELD_DATA_ROOT"))
        if name == "build":
            sp.add_argument("--force", action="store_true",
                            help="Regenerate forms even if they exist (refuses if any row already has a verdict)")
        if name == "import":
            sp.add_argument("form", type=Path)
            sp.add_argument("--decided-by", required=True, help="name of the expert who filled the form")
    args = p.parse_args(argv)
    if not args.data_root:
        p.error("--data-root is required (or set KISANSHIELD_DATA_ROOT)")
    return build(args) if args.cmd == "build" else import_form(args)


if __name__ == "__main__":
    sys.exit(main())
