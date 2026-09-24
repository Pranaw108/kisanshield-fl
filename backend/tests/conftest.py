"""Shared fixtures. The real model is never loaded in tests — a fake predictor stands in."""

import io
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.inference import Prediction  # noqa: E402
from app.main import app  # noqa: E402
from app.routers.predict import predictor_dependency  # noqa: E402


class FakePredictor:
    """Returns fixed, ordered predictions without touching TensorFlow or a model file."""

    def __init__(self, predictions):
        self._predictions = predictions

    def predict(self, image_bytes, top_k=3):
        return self._predictions[:top_k]


CONFIDENT = [
    Prediction("SOY_RUST", "Rust", "गेरुआ रोग", "soybean", 0.91),
    Prediction("SOY_FROGEYE", "Frogeye leaf spot", "फ्रॉगआई पत्ती धब्बा", "soybean", 0.05),
    Prediction("SOY_HEALTHY", "Healthy", "स्वस्थ", "soybean", 0.02),
]
UNSURE = [
    Prediction("SOY_RUST", "Rust", "गेरुआ रोग", "soybean", 0.20),
    Prediction("SOY_HEALTHY", "Healthy", "स्वस्थ", "soybean", 0.18),
    Prediction("SOY_FROGEYE", "Frogeye leaf spot", "फ्रॉगआई पत्ती धब्बा", "soybean", 0.15),
]


@pytest.fixture()
def client_with(monkeypatch):
    """client_with(predictions) -> TestClient wired to a FakePredictor returning those predictions."""
    def _make(predictions):
        app.dependency_overrides[predictor_dependency] = lambda: FakePredictor(predictions)
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()
    return _make


def jpeg_bytes(color="green", size=(64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()
