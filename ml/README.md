# ML

| Path | Purpose |
|---|---|
| `requirements.txt` | Python packages for data, EDA and training (install into the project `.venv`) |
| `notebooks/01_eda.ipynb` | Exploratory data analysis of the public datasets. Findings: [docs/eda/EDA_FINDINGS.md](../docs/eda/EDA_FINDINGS.md) |
| `preprocessing/` | Resize, pad and normalise, plus photo quality checks. Must match the Android pipeline exactly (parity-tested) |
| `training/` | Transfer-learning baselines, confidence calibration (temperature scaling), Grad-CAM checks |
| `export/` | LiteRT int8 inference model and trainable model (head-only `train`/`infer`/`save`/`restore` signatures), benchmarks |
| `configs/` | YAML experiment configs, tracked in MLflow |

**Notebooks are committed without outputs.** Their outputs show dataset images, and some licences restrict republishing them.
Run a notebook with the **KisanShield (.venv)** kernel. Charts go to `docs/eda/figures/`.

**Headline metric:** macro-F1 on the held-out **field** test set (unseen district and season). Public-data results are
reported per source and never presented as field accuracy (decision D-13).
