"""Tests for POST /v1/predict. Run: pytest backend/tests -q"""

from conftest import CONFIDENT, UNSURE, jpeg_bytes


def use(fixture_gen, predictions):
    return next(fixture_gen(predictions))


def test_confident_prediction_returns_top_and_alternatives(client_with):
    client = use(client_with, CONFIDENT)
    r = client.post("/v1/predict", files={"file": ("leaf.jpg", jpeg_bytes(), "image/jpeg")})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["top"]["class_id"] == "SOY_RUST"
    assert body["top"]["confidence"] == 0.91
    assert [a["class_id"] for a in body["alternatives"]] == ["SOY_FROGEYE", "SOY_HEALTHY"]
    assert "top" in body and "advice" not in body        # no agronomic advice — S-12 not built yet


def test_low_confidence_is_reported_as_not_sure(client_with):
    client = use(client_with, UNSURE)
    r = client.post("/v1/predict", files={"file": ("leaf.jpg", jpeg_bytes(), "image/jpeg")})
    body = r.json()
    assert body["status"] == "not_sure" and body["top"] is None
    assert "not confident" in body["message"].lower()


def test_rejects_non_image_content_type(client_with):
    client = use(client_with, CONFIDENT)
    r = client.post("/v1/predict", files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_rejects_oversized_upload(client_with, monkeypatch):
    import app.config as config
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 10)
    client = use(client_with, CONFIDENT)
    r = client.post("/v1/predict", files={"file": ("leaf.jpg", jpeg_bytes(), "image/jpeg")})
    assert r.status_code == 413


def test_unreadable_image_returns_422_not_500(client_with):
    class BrokenPredictor:
        def predict(self, data, top_k=3):
            raise ValueError("cannot identify image")
    from app.main import app
    from app.routers.predict import predictor_dependency
    app.dependency_overrides[predictor_dependency] = lambda: BrokenPredictor()
    from fastapi.testclient import TestClient
    client = TestClient(app)
    r = client.post("/v1/predict", files={"file": ("leaf.jpg", b"not an image", "image/jpeg")})
    app.dependency_overrides.clear()
    assert r.status_code == 422


def test_health_endpoint_reports_missing_model_without_crashing():
    from app.main import app
    from fastapi.testclient import TestClient
    body = TestClient(app).get("/health").json()
    assert body["status"] == "degraded" and body["model_loaded"] is False


def test_model_unavailable_returns_503():
    from app.main import app
    from app.routers.predict import predictor_dependency
    def boom():
        raise FileNotFoundError("no model")
    app.dependency_overrides[predictor_dependency] = boom
    from fastapi.testclient import TestClient
    r = TestClient(app).post("/v1/predict", files={"file": ("leaf.jpg", jpeg_bytes(), "image/jpeg")})
    app.dependency_overrides.clear()
    assert r.status_code == 503
