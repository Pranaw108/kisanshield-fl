"""Cache small copies of the images selected by the manifest, for fast EDA and expert review.

The manifest is the source of truth: each selected row's `archive` + `member_path` says where the
image lives (nested zips use "outer.zip!/inner/path"), so datasets.yaml is not re-read here.
Each image is saved as a JPEG that fits in a 384x384 box (aspect ratio kept).

A thumbnail is (re)built when it is missing or when the source image changed (SHA-256 differs from
the one recorded in thumbs_384/index.csv). Thumbnails no longer selected are kept unless --prune.

Usage:
    python data/scripts/build_thumbnails.py --data-root E:/Datasets
    python data/scripts/build_thumbnails.py --data-root E:/Datasets --prune   # also delete stale files
Output:
    <data-root>/cache/thumbs_384/<image_id>.jpg  and  index.csv (image_id, sha256)
"""

from __future__ import annotations

import argparse
import csv
import io
import logging
import os
import sys
import zipfile
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path
from typing import Iterator

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_manifest as bm  # noqa: E402  (only shared constants are used)

THUMB_SIZE = 384
JPEG_QUALITY = 90  # high enough to see small lesions during expert review
STATUSES = ("use", "hold", "exclude")
log = logging.getLogger("build_thumbnails")


def save_thumbnail(data: bytes, out_path: str) -> str | None:
    """Returns an error message, or None on success. Writes atomically, so a crash never leaves half a file."""
    tmp_path = out_path + ".tmp"
    try:
        with Image.open(io.BytesIO(data)) as img:
            if img.format == "JPEG":
                img.draft("RGB", (THUMB_SIZE, THUMB_SIZE))  # faster decode for large photos
            thumb = ImageOps.exif_transpose(img).convert("RGB")
        thumb.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
        thumb.save(tmp_path, "JPEG", quality=JPEG_QUALITY)
        os.replace(tmp_path, out_path)
        return None
    except Exception as exc:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return f"{type(exc).__name__}: {exc}"


def read_selected(data_root: Path, rows: list[dict]) -> Iterator[tuple[dict, bytes | None, str | None]]:
    """Yield (row, bytes, error) for each row, reading every archive once in file order."""
    by_archive: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_archive[r["archive"]].append(r)

    for archive, arc_rows in by_archive.items():
        path = data_root / archive
        if not path.exists():
            for r in arc_rows:
                yield r, None, f"archive not found: {path}"
            continue
        log.info("%s (%d images)", archive, len(arc_rows))
        with zipfile.ZipFile(path) as zf:
            plain, nested = [], defaultdict(list)
            for r in arc_rows:
                outer, sep, inner = r["member_path"].partition(bm.NESTED_SEP)
                if sep:
                    nested[outer].append((inner, r))
                else:
                    plain.append((outer, r))
            yield from _read_members(zf, plain)
            for outer, members in nested.items():
                try:
                    with zf.open(outer) as fh, zipfile.ZipFile(fh) as inner_zf:
                        yield from _read_members(inner_zf, members)
                except KeyError:
                    for _, r in members:
                        yield r, None, f"nested zip not found in archive: {outer}"


def _read_members(zf: zipfile.ZipFile, members: list[tuple[str, dict]]) -> Iterator[tuple[dict, bytes | None, str | None]]:
    """Read in header order so compressed (nested) streams are read forward only."""
    found, missing = [], []
    for name, r in members:
        try:
            found.append((zf.getinfo(name), r))
        except KeyError:
            missing.append(r)
    for r in missing:
        yield r, None, f"member not found in archive: {r['member_path']}"
    for info, r in sorted(found, key=lambda x: x[0].header_offset):
        yield r, zf.read(info), None


def load_index(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as fh:
        return {r["image_id"]: r["sha256"] for r in csv.DictReader(fh)}


def write_index(path: Path, index: dict[str, str]) -> None:
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["image_id", "sha256"])
        w.writerows(sorted(index.items()))
    os.replace(tmp, path)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-root", type=Path, default=os.environ.get("KISANSHIELD_DATA_ROOT"))
    p.add_argument("--manifest", type=Path, help="Default: <data-root>/manifests/manifest_<version>.csv")
    p.add_argument("--statuses", nargs="+", default=["use", "hold"], choices=STATUSES)
    p.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    p.add_argument("--prune", action="store_true", help="Delete thumbnails not selected by this manifest")
    args = p.parse_args(argv)
    if not args.data_root:
        p.error("--data-root is required (or set KISANSHIELD_DATA_ROOT)")
    manifest = args.manifest or args.data_root / "manifests" / f"manifest_{bm.MANIFEST_VERSION}.csv"
    if not manifest.exists():
        p.error(f"manifest not found: {manifest} (run build_manifest.py first)")

    out_dir = args.data_root / "cache" / f"thumbs_{THUMB_SIZE}"
    out_dir.mkdir(parents=True, exist_ok=True)
    index_path = out_dir / "index.csv"
    index = load_index(index_path)

    with manifest.open(encoding="utf-8") as fh:
        selected = [r for r in csv.DictReader(fh) if r["status"] in args.statuses]
    wanted = {r["image_id"] for r in selected}

    def up_to_date(r: dict) -> bool:
        return (out_dir / f"{r['image_id']}.jpg").exists() and index.get(r["image_id"]) == r["sha256"]

    todo = [r for r in selected if not up_to_date(r)]
    stats = {"wanted": len(wanted), "up_to_date": len(wanted) - len(todo), "built": 0, "failed": 0, "pruned": 0}
    log.info("%d selected, %d up to date, %d to build", stats["wanted"], stats["up_to_date"], len(todo))

    if todo:
        pending: dict = {}

        def collect(keep: int) -> None:
            while len(pending) > keep:
                done, _ = wait(list(pending), return_when=FIRST_COMPLETED)
                for fut in done:
                    finish(pending.pop(fut), fut.result())

        def finish(r: dict, error: str | None) -> None:
            if error:
                stats["failed"] += 1
                log.error("thumbnail failed %s (%s): %s", r["image_id"], r["member_path"], error)
            else:
                stats["built"] += 1
                index[r["image_id"]] = r["sha256"]

        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            for r, data, error in read_selected(args.data_root, todo):
                if error:
                    finish(r, error)
                    continue
                pending[pool.submit(save_thumbnail, data, str(out_dir / f"{r['image_id']}.jpg"))] = r
                collect(keep=args.workers * 2)  # rolling window: bounded memory, workers never idle
            collect(keep=0)
        write_index(index_path, index)

    if args.prune:
        for path in out_dir.glob("*.jpg"):
            if path.stem not in wanted:
                path.unlink()
                index.pop(path.stem, None)
                stats["pruned"] += 1
        write_index(index_path, index)

    missing = sum(1 for i in wanted if not (out_dir / f"{i}.jpg").exists())
    stale = sum(1 for p_ in out_dir.glob("*.jpg") if p_.stem not in wanted)
    log.info("Selected %d | up to date %d | built %d | failed %d | missing %d | pruned %d | not selected %d%s",
             stats["wanted"], stats["up_to_date"], stats["built"], stats["failed"], missing, stats["pruned"],
             stale, " (use --prune to delete)" if stale else "")
    log.info("Thumbnails: %s", out_dir)
    return 0 if stats["failed"] == 0 and missing == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
