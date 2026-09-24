"""Train the baseline classifier head on cached EfficientNetB0 features, and evaluate honestly.

The backbone is frozen (see extract_features.py); this trains only a small head on top, matching
the on-device head-only training architecture planned for the app.

Per decision D-14, class weights correct for the ~16x train imbalance (see build_splits.py).
Per decision D-13, results are reported per source dataset as well as overall — a class with two
sources scoring very differently between them is exactly the shortcut-learning risk found in EDA
(docs/eda/EDA_FINDINGS.md), not just a theoretical concern.

Usage:
    python ml/training/train_baseline.py --data-root E:/Datasets
Output:
    <data-root>/models/head_<version>.keras   trained head
    <data-root>/models/labels_<version>.json  class_id <-> index mapping
    ml/training/RESULTS.md                    metrics report (committed; no images or weights)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from data.scripts import build_manifest as bm  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SEED = 20260918
EPOCHS = 60
PATIENCE = 8
HIDDEN_UNITS = 128
DROPOUT = 0.3


def load_features(path: Path) -> dict:
    z = np.load(path, allow_pickle=True)
    return {k: z[k] for k in z.files}


def build_head(input_dim: int, num_classes: int):
    import tensorflow as tf
    from tensorflow import keras
    tf.random.set_seed(SEED)
    model = keras.Sequential([
        keras.layers.Input((input_dim,)),
        keras.layers.Dropout(DROPOUT),
        keras.layers.Dense(HIDDEN_UNITS, activation="relu", kernel_regularizer=keras.regularizers.l2(1e-4)),
        keras.layers.Dropout(DROPOUT),
        keras.layers.Dense(num_classes, activation="softmax"),
    ])
    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="sparse_categorical_crossentropy",
                  metrics=["accuracy"])
    return model


def evaluate(model, X: np.ndarray, y: np.ndarray, datasets: np.ndarray, labels: list[str]) -> dict:
    from sklearn.metrics import classification_report, confusion_matrix, f1_score
    pred = model.predict(X, verbose=0).argmax(axis=1)
    report = classification_report(y, pred, target_names=labels, output_dict=True, zero_division=0)
    cm = confusion_matrix(y, pred, labels=range(len(labels)))

    per_source = {}  # decision D-13: per (class, source dataset) accuracy where a class has 2+ sources
    for cls_idx, cls in enumerate(labels):
        mask = y == cls_idx
        sources = sorted(set(datasets[mask]))
        if len(sources) < 2:
            continue
        per_source[cls] = {}
        for ds in sources:
            sub = mask & (datasets == ds)
            per_source[cls][ds] = {"n": int(sub.sum()), "accuracy": round(float((pred[sub] == cls_idx).mean()), 3)}

    return {"macro_f1": round(f1_score(y, pred, average="macro"), 4), "report": report,
            "confusion_matrix": cm.tolist(), "per_source": per_source}


def write_results_md(path: Path, labels: list[str], counts: dict, val: dict, test: dict, seconds: float) -> None:
    L = ["# Baseline model results", "",
        f"Trained {time.strftime('%Y-%m-%d')} on frozen EfficientNetB0 features "
        f"({sum(counts.values())} images across train/val/test), {seconds:.0f}s training time.", "",
        "**This is a public-data baseline, not a field-tested model.** Per "
        "[EDA finding F1](../../docs/eda/EDA_FINDINGS.md), class is correlated with source dataset "
        "within this data, so the per-source breakdown below matters more than the headline number.",
        "", "## Headline", "",
        f"| Split | macro-F1 |", "|---|---:|",
        f"| Validation | {val['macro_f1']} |", f"| Test | {test['macro_f1']} |", "",
        "## Per class (test)", "", "| class | precision | recall | f1 | support |", "|---|---:|---:|---:|---:|"]
    for cls in labels:
        r = test["report"][cls]
        L.append(f"| {cls} | {r['precision']:.2f} | {r['recall']:.2f} | {r['f1-score']:.2f} | {int(r['support'])} |")
    L += ["", "## Per source, where a class has 2+ sources (test) — decision D-13", "",
         "A class scoring very differently between its sources means the model is partly reading "
         "*which dataset the photo came from*, not the disease.", "",
         "| class | source | n | accuracy |", "|---|---|---:|---:|"]
    for cls, sources in test["per_source"].items():
        for ds, s in sources.items():
            L.append(f"| {cls} | {ds} | {s['n']} | {s['accuracy']} |")
    L += ["", "## Confusion matrix (test)", "", "Rows = true class, columns = predicted class.", "",
         "| | " + " | ".join(labels) + " |", "|" + "---|" * (len(labels) + 1)]
    for cls, row in zip(labels, test["confusion_matrix"]):
        L.append(f"| **{cls}** | " + " | ".join(str(v) for v in row) + " |")
    path.write_text("\n".join(L), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-root", type=Path, default=os.environ.get("KISANSHIELD_DATA_ROOT"))
    args = p.parse_args(argv)
    if not args.data_root:
        p.error("--data-root is required (or set KISANSHIELD_DATA_ROOT)")

    feat_path = args.data_root / "cache" / f"features_{bm.MANIFEST_VERSION}.npz"
    if not feat_path.exists():
        p.error(f"features not found: {feat_path} (run extract_features.py first)")
    d = load_features(feat_path)

    labels = sorted(set(d["class_id"]))
    label_to_idx = {c: i for i, c in enumerate(labels)}
    y_all = np.array([label_to_idx[c] for c in d["class_id"]])
    split = d["split"]

    def subset(name):
        mask = split == name
        return d["features"][mask], y_all[mask], d["dataset_id"][mask]

    X_train, y_train, _ = subset("train")
    X_val, y_val, ds_val = subset("val")
    X_test, y_test, ds_test = subset("test")
    print(f"train {len(y_train):,} | val {len(y_val):,} | test {len(y_test):,} | classes {len(labels)}")

    from sklearn.utils.class_weight import compute_class_weight
    from tensorflow import keras
    weights = compute_class_weight("balanced", classes=np.arange(len(labels)), y=y_train)
    class_weight = dict(enumerate(weights))

    model = build_head(X_train.shape[1], len(labels))
    t0 = time.time()
    early_stop = keras.callbacks.EarlyStopping(monitor="val_loss", patience=PATIENCE, restore_best_weights=True)
    model.fit(X_train, y_train, validation_data=(X_val, y_val), epochs=EPOCHS, batch_size=32,
             class_weight=class_weight, callbacks=[early_stop], verbose=2)
    seconds = time.time() - t0

    val_metrics = evaluate(model, X_val, y_val, ds_val, labels)
    test_metrics = evaluate(model, X_test, y_test, ds_test, labels)
    print(f"val macro-F1 {val_metrics['macro_f1']} | test macro-F1 {test_metrics['macro_f1']} "
         f"({seconds:.0f}s train)")

    models_dir = args.data_root / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    model.save(models_dir / f"head_{bm.MANIFEST_VERSION}.keras")
    (models_dir / f"labels_{bm.MANIFEST_VERSION}.json").write_text(
        json.dumps({"labels": labels, "input_dim": int(X_train.shape[1]),
                   "backbone": "EfficientNetB0", "image_size": 224}, indent=2), encoding="utf-8")

    results_dir = REPO_ROOT / "ml" / "training"
    write_results_md(results_dir / "RESULTS.md", labels, Counter(d["class_id"].tolist()), val_metrics,
                     test_metrics, seconds)
    print(f"Model: {models_dir / f'head_{bm.MANIFEST_VERSION}.keras'}")
    print(f"Results: {results_dir / 'RESULTS.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
