"""Split usable images into train/val/test, grouped by (dataset, class) so every source is
represented in every split. Applies decisions from data/review/DECISIONS.md:

  D-11  ignore each dataset's own train/valid/test split (some leak into each other, see EDA)
  D-14  cap the YELLOW-RUST-19 contribution to WHT_YELLOW_RUST in train, to ease the 20x imbalance

This is a public-data split, not a field split — see docs/eda/EDA_FINDINGS.md (F1): class is
still correlated with source dataset within it, so held-out accuracy on this split will not
predict field accuracy. Per D-13, evaluation must also be reported per source.

Usage:
    python data/scripts/build_splits.py --data-root E:/Datasets
Output:
    <data-root>/manifests/splits_<version>.csv   (image_id, dataset_id, class_id, split)
"""

from __future__ import annotations

import argparse
import csv
import os
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_manifest as bm  # noqa: E402

TRAIN, VAL, TEST = 0.8, 0.1, 0.1
SEED = 20260918
YELLOW_RUST_CAP = 1500  # D-14: max YELLOW-RUST-19 images kept in train for WHT_YELLOW_RUST


def split_stratum(image_ids: list[str], rng: random.Random) -> dict[str, str]:
    """Shuffle and cut one (dataset, class) group into train/val/test. Tiny groups still get
    at least one val and one test image where there are enough to spare, so a stratum with 4
    images does not silently get zero validation or test coverage."""
    ids = image_ids[:]
    rng.shuffle(ids)
    n = len(ids)
    n_val = min(max(1, round(n * VAL)), n - 1) if n >= 3 else 0
    n_test = min(max(1, round(n * TEST)), n - n_val - 1) if n - n_val >= 2 else 0
    return {**{i: "test" for i in ids[:n_test]},
            **{i: "val" for i in ids[n_test:n_test + n_val]},
            **{i: "train" for i in ids[n_test + n_val:]}}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-root", type=Path, default=os.environ.get("KISANSHIELD_DATA_ROOT"))
    args = p.parse_args(argv)
    if not args.data_root:
        p.error("--data-root is required (or set KISANSHIELD_DATA_ROOT)")

    manifest = args.data_root / "manifests" / f"manifest_{bm.MANIFEST_VERSION}.csv"
    with manifest.open(encoding="utf-8") as fh:
        use = [r for r in csv.DictReader(fh) if r["status"] == "use"]

    by_stratum: dict[tuple[str, str], list[str]] = defaultdict(list)
    for r in use:
        by_stratum[(r["dataset_id"], r["class_id"])].append(r["image_id"])

    rng = random.Random(SEED)
    split_of: dict[str, str] = {}
    for key, ids in sorted(by_stratum.items()):
        split_of.update(split_stratum(ids, rng))

    # D-14: subsample YELLOW-RUST-19's train contribution to WHT_YELLOW_RUST down to the cap
    train_yr19 = [i for i in by_stratum.get(("yellow_rust_19", "WHT_YELLOW_RUST"), [])
                  if split_of[i] == "train"]
    if len(train_yr19) > YELLOW_RUST_CAP:
        rng.shuffle(train_yr19)
        for image_id in train_yr19[YELLOW_RUST_CAP:]:
            split_of[image_id] = "unused"

    out_path = args.data_root / "manifests" / f"splits_{bm.MANIFEST_VERSION}.csv"
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["image_id", "dataset_id", "class_id", "split"])
        for r in use:
            w.writerow([r["image_id"], r["dataset_id"], r["class_id"], split_of[r["image_id"]]])

    counts = Counter(split_of.values())
    print(f"train {counts['train']:,} | val {counts['val']:,} | test {counts['test']:,} "
          f"| unused (D-14 cap) {counts['unused']:,}")
    by_class = defaultdict(Counter)
    for r in use:
        by_class[r["class_id"]][split_of[r["image_id"]]] += 1
    print(f"{'class_id':<22}{'train':>8}{'val':>8}{'test':>8}")
    for cls, c in sorted(by_class.items()):
        print(f"{cls:<22}{c['train']:>8}{c['val']:>8}{c['test']:>8}")
    print(f"Splits: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
