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
| Pulses | Urd/moong YMV, Cercospora leaf spot, powdery mildew, chickpea Ascochyta blight |

The full draft class list is in [taxonomy/classes_v1.csv](taxonomy/classes_v1.csv).

## Tech stack

| Layer | Choice |
|---|---|
| ML | TensorFlow / Keras, MobileNetV3 / EfficientNet-Lite, LiteRT (TFLite) |
| Federated learning | [Flower](https://flower.ai) (simulation + Android clients), SecAgg+, differential privacy |
| Backend | FastAPI, PostgreSQL, Docker Compose |
| Mobile | Kotlin, Jetpack Compose, CameraX, LiteRT, Room, WorkManager |
| Data & experiments | Label Studio, FiftyOne, cleanlab, MLflow |

## Repository structure

```
kisanshield-fl/
├── taxonomy/     # Single source of truth for disease class IDs
├── data/         # Data scripts and manifests (images are never committed)
├── ml/           # Preprocessing, training, calibration, mobile export
├── fl/           # Federated learning simulation, server app, privacy attack tests
├── backend/      # FastAPI service: devices, model registry, advice packs, admin
├── advisory/     # Expert-approved advice records and pack builder
├── android/      # Kotlin Android app
├── deploy/       # Docker Compose and environment templates
└── docs/         # Roadmap, architecture, threat model, runbooks
```

Each folder has its own README explaining what goes in it.

## Data and privacy principles

1. Raw farmer photos are never uploaded to the server or committed to this repository.
2. Field data is collected only with informed consent and follows India's DPDP Act 2023.
3. No faces, names, phone numbers or exact GPS locations are stored.
4. Public datasets are used only in line with their licences, and their sources are cited in `data/manifests/`.

## Getting started

Setup instructions will be added as each component lands. Planned prerequisites:

- Python 3.11+
- Android Studio (latest stable), JDK 17
- Docker and Docker Compose

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). To report a security issue, see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
