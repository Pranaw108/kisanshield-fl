"""Loads the trained model once and runs predictions.

v0 architecture: a frozen EfficientNetB0 backbone (ImageNet weights) plus a small trained head,
run on the server. This is the same split used in training (extract_features.py /
train_baseline.py), so training and serving share one preprocessing function — see
ml/preprocessing/image_prep.py and the ML guideline in that module's docstring.

Production target (see mobile/README.md): this same head, exported to LiteRT and run on the
phone. Swapping v0's server call for an on-device one is a mobile-side change; this module's
predict() contract does not need to change.
"""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

from app import config
from ml.preprocessing.image_prep import load_and_letterbox, to_array

log = logging.getLogger("kisanshield.inference")


@dataclass(frozen=True)
class ClassInfo:
    crop: str
    name_en: str
    name_hi: str


@dataclass(frozen=True)
class Prediction:
    class_id: str
    name_en: str
    name_hi: str
    crop: str
    confidence: float


def load_taxonomy(path) -> dict[str, ClassInfo]:
    with open(path, encoding="utf-8") as fh:
        return {r["class_id"]: ClassInfo(r["crop"], r["name_en"], r["name_hi"])
               for r in csv.DictReader(fh) if r["in_model"] == "true"}


class Predictor:
    """Wraps the frozen backbone + trained head. One instance per process, loaded at startup."""

    def __init__(self, model_dir, taxonomy_path, manifest_version: str):
        labels_path = model_dir / f"labels_{manifest_version}.json"
        head_path = model_dir / f"head_{manifest_version}.keras"
        if not labels_path.exists() or not head_path.exists():
            raise FileNotFoundError(
                f"trained model not found in {model_dir} for version {manifest_version!r} "
                f"(run ml/training/extract_features.py and train_baseline.py first)")

        meta = json.loads(labels_path.read_text(encoding="utf-8"))
        self.labels: list[str] = meta["labels"]
        self.taxonomy = load_taxonomy(taxonomy_path)
        missing = [c for c in self.labels if c not in self.taxonomy]
        if missing:
            raise ValueError(f"model was trained on classes not in the current taxonomy: {missing}")

        from tensorflow import keras
        from tensorflow.keras.applications import EfficientNetB0
        self.backbone = EfficientNetB0(include_top=False, pooling="avg", weights="imagenet",
                                       input_shape=(meta["image_size"], meta["image_size"], 3))
        self.head = keras.models.load_model(head_path)
        log.info("loaded model %s: %d classes", manifest_version, len(self.labels))

    def predict(self, image_bytes: bytes, top_k: int = 3) -> list[Prediction]:
        img = load_and_letterbox(image_bytes)
        x = to_array(img)
        features = self.backbone.predict(x, verbose=0)
        probs = self.head.predict(features, verbose=0)[0]

        order = np.argsort(probs)[::-1][:top_k]
        out = []
        for idx in order:
            cls = self.labels[idx]
            info = self.taxonomy[cls]
            out.append(Prediction(cls, info.name_en, info.name_hi, info.crop, round(float(probs[idx]), 4)))
        return out


@lru_cache(maxsize=1)
def get_predictor() -> Predictor:
    return Predictor(config.MODEL_DIR, config.TAXONOMY_PATH, config.MANIFEST_VERSION)
