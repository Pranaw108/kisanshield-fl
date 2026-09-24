"""API request/response models. Pydantic validates every response shape automatically."""

from __future__ import annotations

from pydantic import BaseModel


class PredictionOut(BaseModel):
    class_id: str
    name_en: str
    name_hi: str
    crop: str
    confidence: float


class PredictResponse(BaseModel):
    status: str  # "ok" | "not_sure"
    top: PredictionOut | None
    alternatives: list[PredictionOut]
    message: str | None = None


class ErrorResponse(BaseModel):
    detail: str
