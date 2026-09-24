"""KisanShield-FL backend — FastAPI app.

Run: uvicorn app.main:app --reload --app-dir backend
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import config
from app.routers import predict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("kisanshield.startup")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Warm the model so the first real request isn't slow. A missing model does not crash the
    # process — /health reports it and /predict 503s per request — so the server stays up and
    # inspectable instead of crash-looping.
    from app.inference import get_predictor
    try:
        get_predictor()
    except FileNotFoundError:
        log.error("no trained model found at startup; /predict will 503 until one is added", exc_info=True)
    yield


app = FastAPI(title="KisanShield-FL API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.include_router(predict.router, prefix="/v1", tags=["prediction"])


@app.exception_handler(FileNotFoundError)
async def model_unavailable(_request: Request, _exc: FileNotFoundError) -> JSONResponse:
    # single place this translation happens, so it applies no matter where get_predictor() is called
    return JSONResponse(status_code=503, content={"detail": "prediction model is not available"})


@app.get("/health")
def health() -> dict:
    from app.inference import get_predictor
    try:
        get_predictor()
        return {"status": "ok", "model_loaded": True}
    except FileNotFoundError:
        return {"status": "degraded", "model_loaded": False}
