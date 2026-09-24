# Backend

FastAPI service. **v0 (current):** one endpoint, `POST /v1/predict`, serving the baseline model
trained in `ml/training/`. **Planned (production):** device registration, model registry,
signed advice-pack distribution, admin panel — see the architecture in the root README.

## Why a prediction API exists before the rest of the backend
The mobile app and web demo both need *something* to call to show a working prediction end to
end. Building the full device/model-registry/advisory backend first, with no way to see a
prediction, would mean flying blind on the one thing that has to work: the model. `/predict`
gets that proven, then the rest of the backend is built around it.

## Run it

```bash
pip install -r backend/requirements.txt
set KISANSHIELD_DATA_ROOT=E:/Datasets   # PowerShell: $env:KISANSHIELD_DATA_ROOT="E:/Datasets"
uvicorn app.main:app --reload --app-dir backend
```

Needs a trained model first: `ml/training/extract_features.py` then `ml/training/train_baseline.py`
(see `ml/README.md`). `/health` reports `model_loaded: false` and `/predict` returns 503 until
one exists — the server still starts and stays inspectable rather than crashing.

## API

| Endpoint | Purpose |
|---|---|
| `GET /health` | `{"status": "ok"\|"degraded", "model_loaded": bool}` |
| `POST /v1/predict` | multipart `file` (JPEG/PNG/WebP, ≤10 MB) → prediction |

`/predict` response:
```json
{
  "status": "ok",
  "top": {"class_id": "SOY_RUST", "name_en": "Rust", "name_hi": "गेरुआ रोग", "crop": "soybean", "confidence": 0.91},
  "alternatives": [{"...": "..."}],
  "message": null
}
```
Below the confidence threshold, `status` is `"not_sure"`, `top` is `null`, and `message` explains why.

**No treatment advice is returned.** That needs an expert-approved knowledge base (roadmap
S-12), which does not exist yet. Returning it before then would be unreviewed agronomic advice
reaching a farmer — never do that.

## Test

```bash
pytest backend/tests -q
```
Tests use a fake predictor (`backend/tests/conftest.py`) — no model file or TensorFlow model
load is needed to run them; they check the API contract, not the model's accuracy.

## Config
All via environment variables (`app/config.py`), never hard-coded: `KISANSHIELD_DATA_ROOT`,
`KISANSHIELD_MODEL_DIR`, `KISANSHIELD_TAXONOMY`, `KISANSHIELD_MANIFEST_VERSION`,
`KISANSHIELD_CORS_ORIGINS`.
