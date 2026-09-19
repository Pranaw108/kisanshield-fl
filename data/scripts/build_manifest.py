"""Build the public-data image manifest for KisanShield-FL.

Scans the downloaded dataset archives listed in data/datasets.yaml, labels every image
using the taxonomy mapping, hashes it, finds exact and near-duplicate images, and writes:

    <out>/manifest_<version>.csv    one row per image (use / hold / exclude, with reason)
    <out>/duplicates_<version>.csv  every duplicate group, with the kept (canonical) image
    <out>/hash_cache.csv            cached hashes, reused for unchanged archive members (same path, CRC, size)
    <out>/summary_<version>.md      human-readable report (also copied to data/manifests/)

Review decisions are applied from data/datasets.yaml (class_map, quality) and
data/review/image_overrides.csv (per-image). See data/review/DECISIONS.md.

Images are read directly from the zip archives (including nested zips), so nothing is extracted
and no extra disk space is needed.

Usage:
    python data/scripts/build_manifest.py --data-root E:/Datasets --list-only   # check rules, fast
    python data/scripts/build_manifest.py --data-root E:/Datasets               # full run
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import logging
import os
import re
import sys
import time
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

import imagehash
import numpy as np
import yaml
from PIL import Image, ImageOps

MANIFEST_VERSION = "public_v2"
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "data" / "datasets.yaml"
DEFAULT_TAXONOMY = REPO_ROOT / "taxonomy" / "classes_v1.csv"
REPO_SUMMARY_DIR = REPO_ROOT / "data" / "manifests"
DEFAULT_OVERRIDES = REPO_ROOT / "data" / "review" / "image_overrides.csv"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
NESTED_SEP = "!/"
MAP_HOLD_VALUES = {None: "pending_taxonomy", "review": "needs_expert_review"}
MAP_DROP = "drop"

MANIFEST_FIELDS = [
    "image_id", "dataset_id", "crop", "archive", "member_path", "split_source",
    "source_label", "class_id", "severity", "status", "reason", "duplicate_of", "dup_group",
    "sha256", "phash", "width", "height", "mode", "is_grayscale", "file_bytes",
    "sharpness_256", "brightness", "error_detail",
]
HASH_FIELDS = ["sha256", "phash", "width", "height", "mode", "is_grayscale", "sharpness_256", "brightness", "error"]
# bump when hash_image() changes, so cached results from the old code are not reused
HASH_VERSION = "1"
CACHE_FIELDS = ["key", "hash_version", *HASH_FIELDS]

log = logging.getLogger("build_manifest")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    pattern: re.Pattern
    label: str | None = None
    exclude: str | None = None
    skip: str | None = None


@dataclass
class ArchiveSpec:
    file: str
    rules: list[Rule]
    downloaded: str | None = None


@dataclass
class DatasetSpec:
    id: str
    crop: str
    class_map: dict[str, str | None]
    severity_map: dict[str, int]
    strip_suffixes: list[str]
    archives: list[ArchiveSpec]
    priority: int = 0
    min_short_side: int = 0     # pixels; smaller images are excluded as too_small
    min_sharpness: float = 0.0  # sharpness_256; lower is excluded as too_blurry


def normalise_label(raw: str, strip_suffixes: list[str] | tuple[str, ...] = ()) -> str:
    """'Black Rust' -> 'black_rust'; 'blast_test_valid' -> 'blast' (with suffixes _valid, _test)."""
    label = re.sub(r"[^0-9a-z]+", "_", raw.strip().lower()).strip("_")
    changed = True
    while changed:
        changed = False
        for suffix in strip_suffixes:
            if label.endswith(suffix) and len(label) > len(suffix):
                label = label[: -len(suffix)]
                changed = True
    return label


def load_taxonomy(path: Path) -> set[str]:
    with path.open(encoding="utf-8") as fh:
        return {row["class_id"] for row in csv.DictReader(fh)}


def load_config(path: Path, taxonomy_ids: set[str]) -> list[DatasetSpec]:
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    specs: list[DatasetSpec] = []
    errors: list[str] = []
    for priority, ds in enumerate(cfg.get("datasets", [])):
        local = ds.get("local")
        if not local:
            errors.append(f"{ds.get('id')}: missing 'local' block")
            continue
        strip = list(local.get("label_strip_suffixes", []))
        class_map = {normalise_label(str(k), strip): v for k, v in (ds.get("class_map") or {}).items()}
        for label, target in class_map.items():
            if target not in MAP_HOLD_VALUES and target != MAP_DROP and target not in taxonomy_ids:
                errors.append(f"{ds['id']}: class_map '{label}' -> '{target}' is not a taxonomy class_id")
        severity = {normalise_label(str(k), strip): int(v) for k, v in (ds.get("severity_map") or {}).items()}
        archives = []
        for arc in local.get("archives", []):
            rules = []
            for r in arc.get("rules", []):
                try:
                    rules.append(Rule(re.compile(r["pattern"]), r.get("label"), r.get("exclude"), r.get("skip")))
                except re.error as exc:
                    errors.append(f"{ds['id']}: bad regex {r.get('pattern')!r}: {exc}")
            archives.append(ArchiveSpec(arc["file"], rules, str(arc.get("downloaded") or "") or None))
        quality = ds.get("quality") or {}
        specs.append(DatasetSpec(ds["id"], ds["crop"], class_map, severity, strip, archives, priority,
                                 int(quality.get("min_short_side", 0)), float(quality.get("min_sharpness", 0))))
    if errors:
        raise ValueError("Invalid datasets.yaml:\n  - " + "\n  - ".join(errors))
    return specs


# ---------------------------------------------------------------------------
# Archive walking
# ---------------------------------------------------------------------------

@dataclass
class Member:
    """One image file inside an archive (possibly inside a nested zip)."""
    path: str          # outer path, or "outer.zip!/inner/path.jpg"
    crc: int
    size: int
    read: object       # callable returning bytes; only valid while the archive is open


@dataclass
class ScanStats:
    skipped: Counter = field(default_factory=Counter)      # reason -> count of archive members skipped
    non_image: Counter = field(default_factory=Counter)    # extension -> count
    unmatched: list[str] = field(default_factory=list)


def match_rule(rules: list[Rule], path: str) -> tuple[Rule, re.Match] | None:
    for rule in rules:
        m = rule.pattern.search(path)
        if m:
            return rule, m
    return None


def iter_members(zip_path: Path, rules: list[Rule], stats: ScanStats) -> Iterator[Member]:
    """Yield image members in file order (keeps reads sequential, which matters for nested zips)."""
    with zipfile.ZipFile(zip_path) as zf:
        for info in sorted(zf.infolist(), key=lambda i: i.header_offset):
            if info.is_dir():
                continue
            hit = match_rule(rules, info.filename)
            if hit and hit[0].skip:
                stats.skipped[hit[0].skip] += 1
                continue
            ext = os.path.splitext(info.filename)[1].lower()
            if ext == ".zip":
                yield from _iter_nested(zf, info, rules, stats)
            elif ext in IMAGE_EXTS:
                yield Member(info.filename, info.CRC, info.file_size, lambda i=info: zf.read(i))
            else:
                stats.non_image[ext or "<none>"] += 1


def _iter_nested(outer: zipfile.ZipFile, info: zipfile.ZipInfo, rules: list[Rule], stats: ScanStats) -> Iterator[Member]:
    log.info("  opening nested zip %s (%.0f MB)", info.filename, info.file_size / 2**20)
    with outer.open(info) as fh, zipfile.ZipFile(fh) as inner:
        for sub in sorted(inner.infolist(), key=lambda i: i.header_offset):
            if sub.is_dir():
                continue
            path = f"{info.filename}{NESTED_SEP}{sub.filename}"
            hit = match_rule(rules, path)
            if hit and hit[0].skip:
                stats.skipped[hit[0].skip] += 1
                continue
            ext = os.path.splitext(sub.filename)[1].lower()
            if ext in IMAGE_EXTS:
                yield Member(path, sub.CRC, sub.file_size, lambda s=sub: inner.read(s))
            else:
                stats.non_image[ext or "<none>"] += 1


def make_image_id(dataset_id: str, archive: str, member_path: str) -> str:
    """Stable id from where the image lives, so it survives re-runs."""
    return hashlib.sha1(f"{dataset_id}|{archive}|{member_path}".encode()).hexdigest()[:16]


def classify(ds: DatasetSpec, archive: str, member: Member, rules: list[Rule], stats: ScanStats) -> dict:
    """Decide label, class and initial status for one image (no image decoding here)."""
    row = {k: "" for k in MANIFEST_FIELDS}
    row.update(
        image_id=make_image_id(ds.id, archive, member.path),
        dataset_id=ds.id, crop=ds.crop, archive=archive, member_path=member.path, file_bytes=member.size,
    )
    hit = match_rule(rules, member.path)
    if hit is None:
        stats.unmatched.append(member.path)
        row.update(status="exclude", reason="no_rule_matched")
        return row
    rule, m = hit
    groups = m.groupdict()
    row["split_source"] = groups.get("split") or ""
    if rule.exclude:
        row.update(status="exclude", reason=rule.exclude)
        return row
    raw_label = rule.label or groups.get("label")
    if not raw_label:
        row.update(status="exclude", reason="rule_has_no_label")
        return row
    label = normalise_label(raw_label, ds.strip_suffixes)
    row["source_label"] = label
    if label not in ds.class_map:
        row.update(status="hold", reason="label_not_in_class_map")
        return row
    target = ds.class_map[label]
    if target == MAP_DROP:
        row.update(status="exclude", reason="class_dropped")
    elif target in MAP_HOLD_VALUES:
        row.update(status="hold", reason=MAP_HOLD_VALUES[target])
    else:
        row.update(status="use", class_id=target)
    if label in ds.severity_map:
        row["severity"] = ds.severity_map[label]
    return row


# ---------------------------------------------------------------------------
# Image hashing (runs in worker processes)
# ---------------------------------------------------------------------------

def hash_image(data: bytes) -> dict:
    """SHA-256 of the file bytes plus perceptual hash and simple quality measures."""
    out = {k: "" for k in HASH_FIELDS}
    out["sha256"] = hashlib.sha256(data).hexdigest()
    try:
        with Image.open(io.BytesIO(data)) as img:
            w, h = img.size                                   # true size, before any reduced decoding
            if img.getexif().get(0x0112, 1) in (5, 6, 7, 8):  # EXIF orientation rotates by 90 degrees
                w, h = h, w
            orig_mode = img.mode
            if img.format == "JPEG":
                img.draft("RGB", (512, 512))  # decode at reduced scale: much faster for 12-64 MP photos
            rgb = ImageOps.exif_transpose(img).convert("RGB")
        # heuristic: near-identical colour channels = likely grayscale (a very pale photo can also match)
        small = np.asarray(rgb.resize((64, 64)), dtype=np.int16)
        channel_spread = np.abs(small[..., 0] - small[..., 1]).mean() + np.abs(small[..., 1] - small[..., 2]).mean()
        gray = np.asarray(rgb.convert("L").resize((256, 256)), dtype=np.float32)
        lap = gray[1:-1, 1:-1] * -4 + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
        out.update(
            phash=str(imagehash.phash(rgb)),
            width=w, height=h, mode=orig_mode,
            is_grayscale=int(orig_mode in ("L", "LA", "1") or channel_spread < 2.0),
            sharpness_256=round(float(lap.var()), 1),
            brightness=round(float(gray.mean()), 1),
        )
    except Exception as exc:  # corrupt or unsupported image: recorded, never fatal
        out["error"] = f"{type(exc).__name__}: {exc}"[:200]
    return out


def cache_key(archive: str, member: Member) -> str:
    return f"{archive}|{member.path}|{member.crc}|{member.size}"


def load_cache(path: Path) -> dict[str, dict]:
    """Cached hash results for the current HASH_VERSION only."""
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if rows and "hash_version" not in rows[0]:  # cache written before versioning: those rows are version 1
        for r in rows:
            r["hash_version"] = "1"
        with path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=CACHE_FIELDS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
    return {r["key"]: r for r in rows if r["hash_version"] == HASH_VERSION}


# ---------------------------------------------------------------------------
# Duplicates
# ---------------------------------------------------------------------------

def group_near_duplicates(phashes: list[str], threshold: int) -> list[list[int]]:
    """Greedy leader clustering over 64-bit pHashes, given in keep-preference order.

    The first unassigned image becomes a group leader and claims every unassigned image within
    `threshold` of IT. Unlike single-linkage (union-find), this never chains A~B~C into one group
    when A and C are far apart: every member is within `threshold` of the image that is kept.
    Returns groups (lists of indices, leader first) with at least two members.

    Cost is O(N^2) in the worst case: ~20 s for 33k images, ~100 s for 100k. Beyond that, switch to an
    indexed Hamming search (e.g. multi-index hashing) to find candidates first.
    """
    values = np.array([int(h, 16) for h in phashes], dtype=np.uint64)
    unassigned = np.ones(len(values), dtype=bool)
    groups: list[list[int]] = []
    for leader in range(len(values)):
        if not unassigned[leader]:
            continue
        unassigned[leader] = False
        cand = np.flatnonzero(unassigned)
        if cand.size == 0:
            break
        close = cand[np.bitwise_count(values[cand] ^ values[leader]) <= threshold]
        if close.size:
            unassigned[close] = False
            groups.append([leader, *close.tolist()])
    return groups


def is_reviewed(row: dict) -> bool:
    return row["reason"].startswith(REVIEW_PREFIX)


def label_identity(row: dict) -> str:
    """What the image claims to show: its taxonomy class, or its source label while it has none."""
    return row["class_id"] or f"{row['dataset_id']}:{row['source_label']}"


def resolve_duplicates(rows: list[dict], threshold: int, priority: dict[str, int]) -> list[dict]:
    """Group exact + near duplicates and keep one image per group. Runs after review overrides.

    Keep preference: reviewed images first, then use before hold, higher resolution, dataset order.
    - A group led by an expert-rejected image: all its copies are excluded too.
    - Copies that disagree on the label (class, or source label for held images): all excluded (D-06),
      unless an expert labelled one of them, in which case the expert label wins.
    - Expert decisions on individual images are never changed here.
    Returns duplicate-report rows. Mutates manifest rows (status, reason, duplicate_of, dup_group).
    """
    status_rank = {"use": 0, "hold": 1, "exclude": 2}
    idx = [i for i, r in enumerate(rows) if r["phash"] and
           (r["status"] in ("use", "hold") or (r["status"] == "exclude" and is_reviewed(r)))]
    idx.sort(key=lambda i: (not is_reviewed(rows[i]), status_rank[rows[i]["status"]],
                            -(int(rows[i]["width"] or 0) * int(rows[i]["height"] or 0)),
                            priority[rows[i]["dataset_id"]], rows[i]["member_path"]))

    report = []
    for group_no, members in enumerate(group_near_duplicates([rows[i]["phash"] for i in idx], threshold), 1):
        gid = f"D{group_no:05d}"
        member_rows = [rows[idx[k]] for k in members]
        leader = member_rows[0]
        rejected = is_reviewed(leader) and leader["status"] == "exclude"
        expert_classes = {r["class_id"] for r in member_rows if is_reviewed(r) and r["status"] == "use"}
        if rejected:
            outcome = "copies_of_rejected"
        elif len(expert_classes) > 1 or (not expert_classes and
                                         len({label_identity(r) for r in member_rows}) > 1):
            outcome = "label_conflict"
        else:
            outcome = "kept_one"

        for r in member_rows:
            r["dup_group"] = gid
            if outcome == "label_conflict" and not (is_reviewed(r) and len(expert_classes) < 2):
                r.update(status="exclude", reason="duplicate_label_conflict")
            elif is_reviewed(r) or r is leader:
                continue
            elif outcome == "copies_of_rejected":
                r.update(status="exclude", reason="duplicate_of_rejected", duplicate_of=leader["image_id"])
            else:
                kind = "exact_duplicate" if r["sha256"] == leader["sha256"] else "near_duplicate"
                r.update(status="exclude", reason=kind, duplicate_of=leader["image_id"])
        datasets = sorted({r["dataset_id"] for r in member_rows})
        labels = {(r["dataset_id"], r["source_label"]) for r in member_rows}
        report.append({
            "dup_group": gid, "size": len(member_rows), "outcome": outcome,
            "label_conflict": int(outcome == "label_conflict"),
            "datasets": " | ".join(datasets),
            "cross_dataset": int(len(datasets) > 1),
            "cross_split": int(len({r["split_source"] for r in member_rows if r["split_source"]}) > 1),
            "canonical": "" if outcome != "kept_one" else leader["image_id"],
            "members": " | ".join(f"{r['image_id']}:{r['dataset_id']}:{r['source_label']}" for r in member_rows),
            "labels": " | ".join(sorted(f"{d}:{l}" for d, l in labels)),
        })
    return report


def apply_quality_rules(rows: list[dict], specs: dict[str, DatasetSpec]) -> None:
    """Exclude images below each dataset's minimum size or sharpness (runs before duplicate checks)."""
    for r in rows:
        if r["status"] not in ("use", "hold") or r["width"] == "":
            continue
        ds = specs[r["dataset_id"]]
        if min(int(r["width"]), int(r["height"])) < ds.min_short_side:
            r.update(status="exclude", reason="too_small")
        elif float(r["sharpness_256"]) < ds.min_sharpness:
            r.update(status="exclude", reason="too_blurry")


# ---------------------------------------------------------------------------
# Review decisions (per-image overrides)
# ---------------------------------------------------------------------------

OVERRIDE_ACTIONS = {"exclude", "use", "hold"}
REVIEW_PREFIX = "review:"


def apply_overrides(rows: list[dict], path: Path, taxonomy_ids: set[str]) -> dict:
    """Apply expert / cleaning decisions from a CSV, before duplicate checks.

    Overrides win over automatic rules. Every reviewed row gets reason "review:<reason>" (use rows too),
    so resolve_duplicates() can keep expert decisions and apply them to near-identical copies.
    CSV columns: image_id, action (exclude|use|hold), class_id (needed for use), reason, decided_by, status
    """
    result = {"applied": 0, "unknown_ids": [], "by_reason": Counter()}
    if not path or not path.exists():
        return result
    by_id = {r["image_id"]: r for r in rows}
    with path.open(encoding="utf-8", newline="") as fh:
        for line_no, o in enumerate(csv.DictReader(fh), start=2):
            action = (o.get("action") or "").strip()
            class_id = (o.get("class_id") or "").strip()
            if action not in OVERRIDE_ACTIONS:
                raise ValueError(f"{path.name}:{line_no}: action must be one of {sorted(OVERRIDE_ACTIONS)}")
            if action == "use" and class_id not in taxonomy_ids:
                raise ValueError(f"{path.name}:{line_no}: 'use' needs a valid taxonomy class_id, got {class_id!r}")
            row = by_id.get(o["image_id"].strip())
            if row is None:
                result["unknown_ids"].append(o["image_id"])
                continue
            if action == "use" and not row["phash"]:
                raise ValueError(f"{path.name}:{line_no}: image {row['image_id']} was never hashed "
                                 f"({row['reason']}); change the archive rule instead of overriding it")
            reason = f"{REVIEW_PREFIX}{(o.get('reason') or 'unspecified').strip()}"
            row.update(status=action, reason=reason,
                       class_id=class_id if action == "use" else ("" if action == "exclude" else row["class_id"]))
            result["applied"] += 1
            result["by_reason"][reason] += 1
    return result


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def scan(specs: list[DatasetSpec], data_root: Path, out_dir: Path, workers: int,
         list_only: bool, use_cache: bool) -> tuple[list[dict], dict]:
    cache_path = out_dir / "hash_cache.csv"
    cache = load_cache(cache_path) if use_cache and not list_only else {}
    new_cache_rows: list[dict] = []
    rows: list[dict] = []
    archive_info: dict = {}
    stats_by_archive: dict[str, ScanStats] = {}

    executor = None if list_only else ProcessPoolExecutor(max_workers=workers)
    try:
        for ds in specs:
            for arc in ds.archives:
                zpath = data_root / arc.file
                if not zpath.exists():
                    raise FileNotFoundError(f"{ds.id}: archive not found: {zpath}")
                st = zpath.stat()
                archive_info[arc.file] = {
                    "dataset_id": ds.id, "size_gb": round(st.st_size / 2**30, 2),
                    "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
                    "downloaded": arc.downloaded or "",
                }
                stats = stats_by_archive.setdefault(arc.file, ScanStats())
                log.info("[%s] %s", ds.id, arc.file)
                t0 = time.time()
                pending: dict = {}
                n_hashed = 0
                for member in iter_members(zpath, arc.rules, stats):
                    row = classify(ds, arc.file, member, arc.rules, stats)
                    rows.append(row)
                    if list_only or row["status"] not in ("use", "hold"):
                        continue
                    key = cache_key(arc.file, member)
                    if key in cache:
                        _apply_hash(row, cache[key])
                        continue
                    fut = executor.submit(hash_image, member.read())
                    pending[fut] = (row, key)
                    if len(pending) >= workers * 4:  # bounded in-flight work keeps memory flat
                        n_hashed += _drain(pending, new_cache_rows, keep=workers * 2)
                n_hashed += _drain(pending, new_cache_rows, keep=0)
                log.info("  %d images listed, %d newly hashed (%.0fs)",
                         sum(1 for r in rows if r["archive"] == arc.file), n_hashed, time.time() - t0)
                if new_cache_rows:
                    _append_cache(cache_path, new_cache_rows)
                    new_cache_rows.clear()
    finally:
        if executor:
            executor.shutdown()

    meta = {"archives": archive_info, "stats": stats_by_archive}
    return rows, meta


def _apply_hash(row: dict, h: dict) -> None:
    for k in HASH_FIELDS:
        if k != "error":
            row[k] = h.get(k, "")
    if h.get("error"):
        row.update(status="exclude", reason="unreadable_image", error_detail=h["error"])


def _drain(pending: dict, new_cache_rows: list[dict], keep: int) -> int:
    """Collect finished hash jobs until at most `keep` are still running."""
    done_count = 0
    while len(pending) > keep:
        done, _ = wait(list(pending), return_when=FIRST_COMPLETED)
        for fut in done:
            row, key = pending.pop(fut)
            h = fut.result()
            _apply_hash(row, h)
            new_cache_rows.append({"key": key, "hash_version": HASH_VERSION, **h})
            done_count += 1
    return done_count


def _append_cache(path: Path, new_rows: list[dict]) -> None:
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CACHE_FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerows(new_rows)


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def build_summary(rows: list[dict], dups: list[dict], meta: dict, threshold: int | None, list_only: bool,
                  overrides: dict | None = None) -> str:
    L: list[str] = []
    L.append(f"# Public data manifest — {MANIFEST_VERSION}")
    L.append("")
    L.append(f"Generated {date.today().isoformat()} by `data/scripts/build_manifest.py`"
             + (" in **list-only** mode (no hashing or duplicate checks)." if list_only else "."))
    L.append("")
    L.append("**Status meaning:** `use` = ready for training · `hold` = waiting on a taxonomy or expert "
             "decision · `exclude` = never used (reason recorded).")
    L.append("")

    L.append("## Archives")
    L.append("")
    L.append("| Archive | Dataset | Size (GB) | Downloaded | Images listed | Skipped members |")
    L.append("|---|---|---:|---|---:|---|")
    per_archive = Counter(r["archive"] for r in rows)
    for arc, info in meta["archives"].items():
        st: ScanStats = meta["stats"][arc]
        skipped = ", ".join(f"{k}: {v}" for k, v in st.skipped.items()) or "—"
        L.append(f"| {arc} | {info['dataset_id']} | {info['size_gb']} | {info['downloaded'] or info['modified']} "
                 f"| {per_archive[arc]:,} | {skipped} |")
    L.append("")

    L.append("## Status by dataset")
    L.append("")
    L.append("| Dataset | use | hold | exclude | total |")
    L.append("|---|---:|---:|---:|---:|")
    by_ds = defaultdict(Counter)
    for r in rows:
        by_ds[r["dataset_id"]][r["status"]] += 1
    for ds, c in by_ds.items():
        L.append(f"| {ds} | {c['use']:,} | {c['hold']:,} | {c['exclude']:,} | {sum(c.values()):,} |")
    tot = Counter(r["status"] for r in rows)
    L.append(f"| **Total** | **{tot['use']:,}** | **{tot['hold']:,}** | **{tot['exclude']:,}** | **{len(rows):,}** |")
    L.append("")

    L.append("## Usable images per taxonomy class")
    L.append("")
    L.append("| class_id | images | from datasets |")
    L.append("|---|---:|---|")
    cls = defaultdict(Counter)
    for r in rows:
        if r["status"] == "use":
            cls[r["class_id"]][r["dataset_id"]] += 1
    for cid in sorted(cls):
        L.append(f"| {cid} | {sum(cls[cid].values()):,} | "
                 + ", ".join(f"{d} ({n:,})" for d, n in cls[cid].most_common()) + " |")
    L.append("")

    L.append("## Held images (need a decision)")
    L.append("")
    L.append("| Dataset | Source label | Reason | Images |")
    L.append("|---|---|---|---:|")
    held = Counter((r["dataset_id"], r["source_label"], r["reason"]) for r in rows if r["status"] == "hold")
    for (d, lbl, why), n in sorted(held.items()):
        L.append(f"| {d} | {lbl} | {why} | {n:,} |")
    L.append("")

    L.append("## Exclusion reasons")
    L.append("")
    L.append("| Reason | Images |")
    L.append("|---|---:|")
    for why, n in Counter(r["reason"] for r in rows if r["status"] == "exclude").most_common():
        L.append(f"| {why} | {n:,} |")
    L.append("")

    if not list_only:
        L.append(f"## Duplicates (exact SHA-256 + near-duplicate pHash, Hamming distance ≤ {threshold})")
        L.append("")
        cross_ds = Counter(g["datasets"].replace(" | ", " ↔ ") for g in dups if g["cross_dataset"])
        L.append(f"- Duplicate groups: **{len(dups):,}** covering "
                 f"**{sum(g['size'] for g in dups):,}** images")
        L.append(f"- Images removed as exact duplicates: **{tot_reason(rows, 'exact_duplicate'):,}**; "
                 f"as near duplicates: **{tot_reason(rows, 'near_duplicate'):,}**")
        L.append(f"- Groups spanning two datasets: **{sum(g['cross_dataset'] for g in dups):,}**"
                 + (" (" + ", ".join(f"{k}: {v}" for k, v in cross_ds.most_common()) + ")" if cross_ds else ""))
        L.append(f"- Groups spanning a dataset's own train/valid/test split (leakage in the source split): "
                 f"**{sum(g['cross_split'] for g in dups):,}**")
        L.append(f"- Groups with conflicting labels, including held images (all members excluded): "
                 f"**{sum(g['label_conflict'] for g in dups):,}**")
        L.append(f"- Groups that copy an expert-rejected image (copies excluded): "
                 f"**{sum(g['outcome'] == 'copies_of_rejected' for g in dups):,}**")
        L.append("")

        L.append("## Review decisions applied (data/review/image_overrides.csv)")
        L.append("")
        if overrides and overrides["applied"]:
            L.append("| Reason | Images |")
            L.append("|---|---:|")
            for why, n in overrides["by_reason"].most_common():
                L.append(f"| {why} | {n:,} |")
        else:
            L.append("- None")
        L.append("")

        L.append("## Image quality flags (use + hold images)")
        L.append("")
        active = [r for r in rows if r["status"] in ("use", "hold") and r["width"] != ""]
        small = sum(1 for r in active if min(int(r["width"]), int(r["height"])) < 224)
        gray = sum(1 for r in active if str(r["is_grayscale"]) == "1")
        sharp = sorted(float(r["sharpness_256"]) for r in active if r["sharpness_256"] != "")
        L.append(f"- Smaller than 224 px on the short side: **{small:,}**")
        L.append(f"- Grayscale: **{gray:,}**")
        if sharp:
            L.append(f"- Sharpness (Laplacian variance at 256 px): median {sharp[len(sharp)//2]:.0f}, "
                     f"lowest 5% below {sharp[len(sharp)//20]:.0f}. Review the blurriest images before training.")
        L.append("")

    warnings = []
    for arc, st in meta["stats"].items():
        if st.unmatched:
            warnings.append(f"- {arc}: {len(st.unmatched)} files matched no rule (e.g. `{st.unmatched[0]}`)")
        if st.non_image:
            warnings.append(f"- {arc}: ignored non-image files: " + ", ".join(f"{k} ×{v}" for k, v in st.non_image.items()))
    unmapped = Counter((r["dataset_id"], r["source_label"]) for r in rows if r["reason"] == "label_not_in_class_map")
    for (d, lbl), n in unmapped.items():
        warnings.append(f"- {d}: label `{lbl}` ({n} images) is not in class_map. Add it to datasets.yaml.")
    if overrides and overrides["unknown_ids"]:
        warnings.append(f"- {len(overrides['unknown_ids'])} override rows point to unknown image ids "
                        f"(e.g. `{overrides['unknown_ids'][0]}`)")
    unreadable = tot_reason(rows, "unreadable_image")
    if unreadable:
        warnings.append(f"- {unreadable} images could not be decoded (reason `unreadable_image`)")
    L.append("## Warnings")
    L.append("")
    L.extend(warnings or ["- None"])
    L.append("")
    return "\n".join(L)


def tot_reason(rows: list[dict], reason: str) -> int:
    return sum(1 for r in rows if r["reason"] == reason)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-root", type=Path, default=os.environ.get("KISANSHIELD_DATA_ROOT"),
                   help="Folder holding the downloaded archives (or set KISANSHIELD_DATA_ROOT)")
    p.add_argument("--out", type=Path, help="Output folder (default: <data-root>/manifests)")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    p.add_argument("--overrides", type=Path, default=DEFAULT_OVERRIDES,
                   help="CSV of per-image review decisions (default: data/review/image_overrides.csv)")
    p.add_argument("--only", nargs="+", metavar="DATASET_ID", help="Process only these dataset ids")
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    p.add_argument("--near-dup-threshold", type=int, default=4,
                   help="Max pHash Hamming distance (0-64) to call two images near duplicates (default 4)")
    p.add_argument("--list-only", action="store_true", help="Apply rules and count images; no hashing")
    p.add_argument("--no-cache", action="store_true", help="Ignore the hash cache and re-hash everything")
    args = p.parse_args(argv)
    if not args.data_root:
        p.error("--data-root is required (or set KISANSHIELD_DATA_ROOT)")
    if not 0 <= args.near_dup_threshold <= 64:
        p.error("--near-dup-threshold must be between 0 and 64")
    args.out = args.out or args.data_root / "manifests"
    return args


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    args = parse_args(argv)
    taxonomy_ids = load_taxonomy(args.taxonomy)
    specs = load_config(args.config, taxonomy_ids)
    if args.only:
        unknown = set(args.only) - {s.id for s in specs}
        if unknown:
            log.error("Unknown dataset id(s): %s", ", ".join(sorted(unknown)))
            return 2
        specs = [s for s in specs if s.id in args.only]
    args.out.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    rows, meta = scan(specs, args.data_root, args.out, args.workers, args.list_only, not args.no_cache)
    rows.sort(key=lambda r: (r["dataset_id"], r["archive"], r["member_path"]))

    dups: list[dict] = []
    overrides: dict = {}
    if not args.list_only:
        # order matters: automatic rules -> human decisions -> duplicates resolved on the final state
        apply_quality_rules(rows, {s.id: s for s in specs})
        overrides = apply_overrides(rows, args.overrides, taxonomy_ids)
        if overrides["applied"]:
            log.info("Applied %d review overrides from %s", overrides["applied"], args.overrides)
        log.info("Checking duplicates across %d images ...", sum(1 for r in rows if r["status"] in ("use", "hold")))
        dups = resolve_duplicates(rows, args.near_dup_threshold, {s.id: s.priority for s in specs})
        suffix = "" if not args.only else "_partial"
        write_csv(args.out / f"manifest_{MANIFEST_VERSION}{suffix}.csv", rows, MANIFEST_FIELDS)
        write_csv(args.out / f"duplicates_{MANIFEST_VERSION}{suffix}.csv", dups,
                  ["dup_group", "size", "outcome", "label_conflict", "datasets", "cross_dataset", "cross_split",
                   "canonical", "labels", "members"])

    summary = build_summary(rows, dups, meta, args.near_dup_threshold, args.list_only, overrides)
    name = f"summary_{MANIFEST_VERSION}{'_list_only' if args.list_only else ''}{'_partial' if args.only else ''}.md"
    (args.out / name).write_text(summary, encoding="utf-8")
    REPO_SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    (REPO_SUMMARY_DIR / name).write_text(summary, encoding="utf-8")

    c = Counter(r["status"] for r in rows)
    log.info("Done in %.1f min: %d images | use %d | hold %d | exclude %d",
             (time.time() - t0) / 60, len(rows), c["use"], c["hold"], c["exclude"])
    log.info("Summary: %s", REPO_SUMMARY_DIR / name)
    if not args.list_only:
        log.info("Manifest: %s", args.out / f"manifest_{MANIFEST_VERSION}.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
