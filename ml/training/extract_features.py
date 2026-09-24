"""Extract frozen EfficientNetB0 (ImageNet) features for every image in the train/val/test split.

The backbone stays frozen; only a small head is trained on these cached features (train_baseline.py).
This matches the project's head-only architecture (see README "How it works") and is fast enough to
run on CPU, unlike fine-tuning the whole backbone.

Usage:
    python ml/training/extract_features.py --data-root E:/Datasets
Output:
    <data-root>/cache/features_<version>.npz   (image_id array, feature matrix, split, class_id)
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data.scripts import build_manifest as bm  # noqa: E402
from ml.preprocessing.image_prep import IMAGE_SIZE, load_and_letterbox  # noqa: E402

BATCH_SIZE = 64


def build_model():
    from tensorflow.keras.applications import EfficientNetB0
    return EfficientNetB0(include_top=False, pooling="avg", weights="imagenet",
                          input_shape=(IMAGE_SIZE, IMAGE_SIZE, 3))


def batched(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-root", type=Path, default=os.environ.get("KISANSHIELD_DATA_ROOT"))
    args = p.parse_args(argv)
    if not args.data_root:
        p.error("--data-root is required (or set KISANSHIELD_DATA_ROOT)")

    splits_path = args.data_root / "manifests" / f"splits_{bm.MANIFEST_VERSION}.csv"
    with splits_path.open(encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh) if r["split"] != "unused"]
    thumbs = args.data_root / "cache" / "thumbs_384"

    from tensorflow.keras.applications.efficientnet import preprocess_input
    model = build_model()
    print(f"extracting features for {len(rows):,} images ...")
    t0 = time.time()
    feats, ids = [], []
    for batch in batched(rows, BATCH_SIZE):
        arrs = []
        for r in batch:
            data = (thumbs / f"{r['image_id']}.jpg").read_bytes()
            arrs.append(np.asarray(load_and_letterbox(data), dtype=np.float32))
        x = preprocess_input(np.stack(arrs))
        feats.append(model.predict(x, verbose=0))
        ids.extend(r["image_id"] for r in batch)
        if len(ids) % (BATCH_SIZE * 20) < BATCH_SIZE:
            print(f"  {len(ids):,}/{len(rows):,} ({time.time() - t0:.0f}s)")

    by_id = {r["image_id"]: r for r in rows}
    out = args.data_root / "cache" / f"features_{bm.MANIFEST_VERSION}.npz"
    np.savez_compressed(
        out,
        image_id=np.array(ids),
        features=np.concatenate(feats).astype(np.float32),
        split=np.array([by_id[i]["split"] for i in ids]),
        class_id=np.array([by_id[i]["class_id"] for i in ids]),
        dataset_id=np.array([by_id[i]["dataset_id"] for i in ids]),
    )
    print(f"done in {(time.time() - t0) / 60:.1f} min. Saved: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
