"""Expert review pack: HTML image sheets + CSV forms for the agronomist, and import of their answers.

    # 1. create the pack (HTML pages + blank CSV forms) in <data-root>/review/
    python data/scripts/review_pack.py build --data-root E:/Datasets

    # 2. after the expert fills a CSV form, turn it into manifest overrides
    python data/scripts/review_pack.py import E:/Datasets/review/label_audit.csv --decided-by "Dr. Name"

Review tasks:
    label_audit      50 random usable images per (dataset, label): is the label right?
    soynet_relabel   every SoyNet diseased photo: which disease is it?
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_manifest as bm  # noqa: E402

FORM_FIELDS = ["image_id", "dataset_id", "source_label", "current_class", "verdict", "correct_class", "notes"]
VERDICTS = {"correct", "wrong", "unsure", "not_a_leaf", "unusable"}
AUDIT_PER_GROUP = 50
# larger samples where EDA found conflicting labels (decision D-15)
AUDIT_OVERRIDES = {("kaggle_wheat_plant_diseases", "black_rust"): 100,
                   ("kaggle_wheat_plant_diseases", "brown_rust"): 100}


def write_sheet(path: Path, title: str, intro: str, df: pd.DataFrame, classes: list[str]) -> None:
    """Static HTML page of thumbnails; images load from the local thumbnail cache."""
    tiles = []
    for r in df.itertuples():
        tiles.append(
            f'<figure><img loading="lazy" src="../cache/thumbs_384/{r.image_id}.jpg">'
            f"<figcaption><b>{r.image_id}</b><br>{html.escape(str(r.source_label))} → "
            f"{html.escape(str(r.current_class))}</figcaption></figure>"
        )
    path.write_text(f"""<!doctype html><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{font:14px system-ui,sans-serif;margin:24px;background:#faf8f3;color:#1c1b17}}
h1{{font-family:Georgia,serif}} .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}}
figure{{margin:0;background:#fff;border:1px solid #e4dfd2;border-radius:8px;padding:8px}}
img{{width:100%;height:200px;object-fit:contain;background:#f1ede1}} figcaption{{font:12px monospace;margin-top:6px}}
.note{{background:#f5e6d3;border-left:3px solid #a05a1e;padding:10px 14px;margin:12px 0}}
</style>
<h1>{html.escape(title)}</h1>
<div class="note">{intro}<br><br><b>Allowed verdicts:</b> {", ".join(sorted(VERDICTS))}<br>
<b>Class ids:</b> {", ".join(classes)}</div>
<p>{len(df):,} images</p><div class="grid">{"".join(tiles)}</div>""", encoding="utf-8")


def write_form(path: Path, df: pd.DataFrame) -> None:
    if path.exists():
        print(f"  kept existing form (may contain answers): {path}")
        return
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FORM_FIELDS)
        w.writeheader()
        for r in df.itertuples():
            w.writerow({"image_id": r.image_id, "dataset_id": r.dataset_id, "source_label": r.source_label,
                        "current_class": r.current_class})


def build(args: argparse.Namespace) -> int:
    m = pd.read_csv(args.data_root / "manifests" / f"manifest_{bm.MANIFEST_VERSION}.csv",
                    dtype={"source_label": str}, keep_default_na=False)
    m["current_class"] = m["class_id"].where(m["class_id"] != "", "(none)")
    out = args.data_root / "review"
    out.mkdir(parents=True, exist_ok=True)
    classes = sorted(bm.load_taxonomy(bm.DEFAULT_TAXONOMY))

    shuffled = m[m.status == "use"].sample(frac=1, random_state=7)
    rank = shuffled.groupby(["dataset_id", "source_label"]).cumcount()
    limit = [AUDIT_OVERRIDES.get(k, AUDIT_PER_GROUP) for k in zip(shuffled.dataset_id, shuffled.source_label)]
    audit = shuffled[rank < limit].sort_values(["dataset_id", "source_label"])
    write_sheet(out / "label_audit.html", "Label audit",
                "For each image, fill <code>label_audit.csv</code>: <b>verdict</b> = correct if the label is right; "
                "if wrong, put the right class id in <b>correct_class</b>.", audit, classes)
    write_form(out / "label_audit.csv", audit)

    soy = m[(m.dataset_id == "soynet") & (m.status == "hold")].sort_values("member_path")
    write_sheet(out / "soynet_relabel.html", "SoyNet: diseased photos to label",
                "These Jabalpur photos are only marked 'diseased'. In <code>soynet_relabel.csv</code> set "
                "<b>verdict</b> = correct and write the disease class id in <b>correct_class</b> "
                "(or unsure / not_a_leaf / unusable).", soy, [c for c in classes if c.startswith("SOY_")])
    write_form(out / "soynet_relabel.csv", soy)

    print(f"Review pack written to {out}: label_audit ({len(audit):,} images), soynet_relabel ({len(soy):,} images)")
    return 0


def import_form(args: argparse.Namespace) -> int:
    """Convert a filled form into rows of data/review/image_overrides.csv."""
    classes = bm.load_taxonomy(bm.DEFAULT_TAXONOMY)
    new_rows, errors = [], []
    with args.form.open(encoding="utf-8", newline="") as fh:
        for n, r in enumerate(csv.DictReader(fh), start=2):
            verdict = (r.get("verdict") or "").strip().lower()
            correct = (r.get("correct_class") or "").strip()
            if not verdict:
                continue  # not reviewed yet
            if verdict not in VERDICTS:
                errors.append(f"line {n}: unknown verdict {verdict!r}")
            elif correct and correct not in classes:
                errors.append(f"line {n}: unknown class {correct!r}")
            elif correct:  # expert gave the right class
                new_rows.append((r["image_id"], "use", correct, f"expert_label:{args.form.stem}"))
            elif verdict == "correct" and r.get("current_class") in classes:
                continue  # label confirmed; nothing to change
            elif verdict in ("wrong", "not_a_leaf", "unusable"):
                new_rows.append((r["image_id"], "exclude", "", f"expert_{verdict}"))
            elif verdict == "unsure":
                new_rows.append((r["image_id"], "exclude", "", "expert_unsure"))
    if errors:
        print("Fix these lines first:\n  " + "\n  ".join(errors))
        return 1

    target = bm.DEFAULT_OVERRIDES
    existing = {}
    if target.exists():
        with target.open(encoding="utf-8", newline="") as fh:
            existing = {r["image_id"]: r for r in csv.DictReader(fh)}
    for image_id, action, cls, reason in new_rows:  # newest decision for an image wins
        existing[image_id] = {"image_id": image_id, "action": action, "class_id": cls, "reason": reason,
                              "decided_by": args.decided_by, "status": "approved"}
    with target.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["image_id", "action", "class_id", "reason", "decided_by", "status"])
        w.writeheader()
        w.writerows(sorted(existing.values(), key=lambda r: (r["reason"], r["image_id"])))
    print(f"{len(new_rows)} decisions written to {target}. Re-run build_manifest.py to apply them.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="create HTML sheets and blank CSV forms")
    b.add_argument("--data-root", type=Path, default=os.environ.get("KISANSHIELD_DATA_ROOT"))
    i = sub.add_parser("import", help="turn a filled CSV form into image overrides")
    i.add_argument("form", type=Path)
    i.add_argument("--decided-by", required=True, help="name of the expert who filled the form")
    args = p.parse_args(argv)
    if args.cmd == "build":
        if not args.data_root:
            p.error("--data-root is required (or set KISANSHIELD_DATA_ROOT)")
        return build(args)
    return import_form(args)


if __name__ == "__main__":
    sys.exit(main())
