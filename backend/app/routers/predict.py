"""POST /predict — upload a leaf photo, get the predicted disease.

No treatment advice is returned here. That needs an expert-approved knowledge base
(roadmap S-12), which does not exist yet — see backend/README.md.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app import config
from app.inference import Predictor, get_predictor
from app.schemas import PredictionOut, PredictResponse

log = logging.getLogger("kisanshield.predict")
router = APIRouter()

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def predictor_dependency() -> Predictor:
    """A thin wrapper around get_predictor() so tests can override it without a real model file.

    FileNotFoundError (no trained model) becomes a 503 via the app-wide handler in main.py, so
    that translation applies no matter what raises it, not just this one call site.
    """
    return get_predictor()


@router.post("/predict", response_model=PredictResponse)
async def predict(file: UploadFile, predictor: Predictor = Depends(predictor_dependency)) -> PredictResponse:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"unsupported file type {file.content_type!r}; use JPEG, PNG or WebP")

    data = await file.read()
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"file too large: {len(data)} bytes (max {config.MAX_UPLOAD_BYTES})")

    try:
        predictions = predictor.predict(data)
    except Exception as exc:
        log.error("prediction failed", exc_info=True)
        raise HTTPException(422, "could not read this image") from exc

    top = predictions[0]
    out = [PredictionOut(**p.__dict__) for p in predictions]
    if top.confidence < config.MIN_CONFIDENCE_FOR_RESULT:
        return PredictResponse(status="not_sure", top=None, alternatives=out,
                               message="Not confident enough to name a disease. Try a clearer, closer photo.")
    return PredictResponse(status="ok", top=out[0], alternatives=out[1:])
