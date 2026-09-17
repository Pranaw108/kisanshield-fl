# ML

| Path | Purpose |
|---|---|
| `preprocessing/` | Resize, normalise and photo quality checks. Must match the Android pipeline exactly (parity-tested). |
| `training/` | Transfer-learning baselines, confidence calibration (temperature scaling), Grad-CAM checks |
| `export/` | LiteRT int8 inference model + trainable model (head-only `train`/`infer`/`save`/`restore` signatures), benchmarks |
| `configs/` | YAML experiment configs, tracked in MLflow |

Headline metric: **macro-F1 on the held-out field test set** (unseen district and season). Lab-image accuracy is reported separately.
