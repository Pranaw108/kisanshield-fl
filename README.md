# KisanShield-FL

**Privacy-preserving crop disease prediction and farmer advisory for Madhya Pradesh, built on federated learning and on-device AI.**

KisanShield-FL is an offline-first Android app for smallholder farmers growing soybean, wheat and pulses. A farmer takes a photo of a leaf, and the app identifies the disease on the phone within seconds, even without internet. It then gives expert-approved advice in Hindi, with voice.

The model gets better over time through **federated learning**: phones improve the model locally, and only small, protected model updates are sent to the server. **Farmer photos never leave the device.**

> **Status:** early research phase (setup and data assessment). No production code yet. See [docs/ROADMAP.md](docs/ROADMAP.md).

---

## How it works

```
 FARMER'S PHONE (offline-first)                          SERVER (India region)
 +------------------------------+                        +------------------------------+
 | Camera + photo quality check |                        | Admin panel (RBAC, audit)    |
 | On-device model (int8)       | <--- signed model ---- | Model registry               |
 | Advice pack (Hindi, offline) | <--- advice pack ----- | FastAPI service              |
 | Result + "Was this right?"   |                        | PostgreSQL + object storage  |
 | Encrypted local photo store  |                        |                              |
 | Background training (head)   |                        | Flower aggregation           |
 | FL client (Flower)           | -- weights only, TLS ->| FedAvg/FedProx + SecAgg + DP |
 +------------------------------+                        +------------------------------+
```

- **Predict first, train later.** Prediction and advice are instant and offline. Training only runs in the background when the phone is charging and idle.
- **Head-only on-device training.** The backbone stays frozen, and only the final classifier layer trains on the phone. Each update is about 100 KB.
- **Privacy layers.** TLS with certificate pinning, secure aggregation, differential privacy, signed models, and encrypted storage on the device.
- **Safe advice.** Advice comes from a rule-based knowledge base built on ICAR sources and approved by a named expert. None of it is AI-generated.

## Crops in scope (v1)

| Crop | Example diseases (draft, pending expert review) |
|---|---|
| Soybean | Yellow mosaic virus, rust, frogeye leaf spot, aerial blight, anthracnose |
| Wheat | Brown rust, yellow rust, black rust, spot blotch, powdery mildew |
| Pulses | Chickpea Fusarium wilt, pea diseases (Ascochyta blight, powdery mildew, and others), urd/moong YMV |

The full draft class list is in [taxonomy/classes_v1.csv](taxonomy/classes_v1.csv).

## Datasets

This project uses the following public datasets. **No images are redistributed in this repository.** Download each dataset from its source and follow its licence.

| Crop | Dataset | Source | Images | Origin | Licence |
|---|---|---|---|---|---|
| Wheat | [Wheat Plant Diseases](https://www.kaggle.com/datasets/kushagra3204/wheat-plant-diseases) | Kaggle | ~14,155 | Not stated | CC0 (declared by uploader) |
| Wheat | [YELLOW-RUST-19](https://www.kaggle.com/datasets/tolgahayit/yellowrust19-yellow-rust-disease-in-wheat) | Kaggle | 5,421 raw (6 severity levels) | Ankara, Türkiye | See Kaggle page |
| Soybean | [MH-SoyaHealthVision](https://data.mendeley.com/datasets/hkbgh5s3b7/1) | Mendeley Data | 2,782 leaf images | Maharashtra, India | CC BY-NC 4.0 |
| Soybean | [SoyNet](https://data.mendeley.com/datasets/w2r855hpx8/2) | Mendeley Data | 1,363 raw | Jabalpur, Madhya Pradesh | CC BY 4.0 |
| Pea | [Pisum sativum Image Dataset](https://data.mendeley.com/datasets/nnv3k3m94k/1) | Mendeley Data | 12,066 | India | CC BY 4.0 |
| Chickpea | [FUSARIUM-22: Fusarium Wilt Disease in Chickpea](https://www.kaggle.com/datasets/tolgahayit/fusarium-wilt-disease-in-chickpea-dataset) | Kaggle | 4,339 raw (5 severity levels) | Türkiye | See Kaggle page |

Counts are the original images actually found in the downloads. Augmented and resized copies shipped with some datasets are excluded. See [data/manifests/summary_public_v1.md](data/manifests/summary_public_v1.md).

Class mappings, usage rules (for example, which folders are excluded as duplicates) and licence status for each dataset are recorded in [data/datasets.yaml](data/datasets.yaml).

> **Licence note:** MH-SoyaHealthVision is licensed for **non-commercial** use only. It is used here for research. Any commercial version of the model must be retrained without it.

### Citations

If you use this work, please also cite the original datasets:

- kushagra3204. *Wheat Plant Diseases* [Data set]. Kaggle. https://www.kaggle.com/datasets/kushagra3204/wheat-plant-diseases
- Hayıt, T., Erbay, H., Varçın, F., Hayıt, F., & Akci, N. (2023). The classification of wheat yellow rust disease based on a combination of textural and deep features. *Multimedia Tools and Applications*. https://doi.org/10.1007/s11042-023-15199-y
- Shinde, S., & Attar, V. (2025). *MH-SoyaHealthVision: An Indian UAV and leaf image dataset for integrated crop health assessment of soybean crop* (Version 1) [Data set]. Mendeley Data. https://doi.org/10.17632/hkbgh5s3b7.1
- Rajput, A. S., Shukla, S., & Thakur, S. S. (2023). *SoyNet: Indian Soybean Image dataset with quality images captured from the agriculture field* (Version 2) [Data set]. Mendeley Data. https://doi.org/10.17632/w2r855hpx8.2
- Thite, S., & Patil, K. (2025). *Pisum sativum Image Dataset: Healthy and Disease-Affected Cases* (Version 1) [Data set]. Mendeley Data. https://doi.org/10.17632/nnv3k3m94k.1
- Hayit, T., Endes, A., & Hayit, F. (2023). The severity level classification of Fusarium wilt of chickpea by pre-trained deep learning models. *Journal of Plant Pathology*. https://doi.org/10.1007/s42161-023-01520-z
- Hayit, T., Endes, A., & Hayit, F. (2023). KNN-based approach for the classification of fusarium wilt disease in chickpea based on color and texture features. *European Journal of Plant Pathology*. https://doi.org/10.1007/s10658-023-02791-z

## Tech stack

| Layer | Choice |
|---|---|
| ML | TensorFlow / Keras, MobileNetV3 / EfficientNet-Lite, LiteRT (TFLite) |
| Federated learning | [Flower](https://flower.ai) (simulation + Android clients), SecAgg+, differential privacy |
| Backend | FastAPI, PostgreSQL, Docker Compose |
| Mobile | Flutter (Dart), `camera`, `tflite_flutter`, Riverpod |
| Web | React + TypeScript + Vite + Tailwind CSS, calling the same backend API as mobile |
| Data & experiments | Label Studio, FiftyOne, cleanlab, MLflow |

## Repository structure

```
kisanshield-fl/
├── taxonomy/     # Single source of truth for disease class IDs
├── data/         # Data scripts and manifests (images are never committed)
├── ml/           # Preprocessing, training, calibration, mobile export
├── fl/           # Federated learning simulation, server app, privacy attack tests
├── backend/      # FastAPI service: prediction API, model registry, advice packs, admin
├── advisory/     # Expert-approved advice records and pack builder
├── mobile/       # Flutter app (Android first)
├── web/          # Browser demo of the prediction model
├── deploy/       # Docker Compose and environment templates
└── docs/         # Roadmap, architecture, threat model, runbooks
```

Each folder has its own README explaining what goes in it. Engineering decisions are logged in
[docs/BUILD_LOG.md](docs/BUILD_LOG.md); data-labelling decisions in
[data/review/DECISIONS.md](data/review/DECISIONS.md).

## Data and privacy principles

1. Raw farmer photos are never uploaded to the server or committed to this repository.
2. Field data is collected only with informed consent and follows India's DPDP Act 2023.
3. No faces, names, phone numbers or exact GPS locations are stored.
4. Public datasets are used only in line with their licences, and their sources are cited in `data/manifests/`.

## Project status

| Step | Status | Where |
|---|---|---|
| Dataset registry and manifest (duplicates, quality) | Done | [data/README.md](data/README.md) |
| Exploratory data analysis | Done | [docs/eda/EDA_FINDINGS.md](docs/eda/EDA_FINDINGS.md) |
| Cleaning decisions | Automatic rules applied; several awaiting expert sign-off | [data/review/DECISIONS.md](data/review/DECISIONS.md) |
| Expert label audit and SoyNet relabelling | Review pack ready | [data/review/README.md](data/review/README.md) |
| Train/val/test split | Done (public data only) | `data/scripts/build_splits.py` |
| Baseline model | First pass trained and evaluated, real numbers | [ml/training/RESULTS.md](ml/training/RESULTS.md) |
| Prediction API | v0 working, tested (fake + real model) | [backend/README.md](backend/README.md) |
| Web demo | v0 working, tested, built | [web/README.md](web/README.md) |
| Mobile app | v0 skeleton, calls the API; on-device inference not started | [mobile/README.md](mobile/README.md) |

**Key EDA finding:** in the public data, class is strongly tied to the source dataset (image shape, background,
camera). Accuracy on public data will overstate real-field accuracy. Madhya Pradesh field photos are needed for a
trustworthy test set — confirmed on real predictions, not just in theory: see the per-source table in
[ml/training/RESULTS.md](ml/training/RESULTS.md).

## Getting started

Requirements: Python 3.11+ (tested on 3.13), Node 20+, Flutter (stable channel). Docker comes later, for `deploy/`.

```bash
python -m venv .venv
.venv\Scripts\activate                 # Linux/macOS: source .venv/bin/activate
pip install -r ml/requirements.txt
python -m pytest data/scripts/tests -q
```

Then follow the data pipeline in [data/README.md](data/README.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). To report a security issue, see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
