"""Configuration from environment variables. No secrets or paths are hard-coded."""

from __future__ import annotations

import os
from pathlib import Path

# Where trained models and taxonomy live. In production this is baked into the deploy image;
# for local dev it points at the shared data drive.
MODEL_DIR = Path(os.environ.get("KISANSHIELD_MODEL_DIR", os.environ.get("KISANSHIELD_DATA_ROOT", "") + "/models"))
TAXONOMY_PATH = Path(os.environ.get(
    "KISANSHIELD_TAXONOMY", Path(__file__).resolve().parents[2] / "taxonomy" / "classes_v1.csv"))
MANIFEST_VERSION = os.environ.get("KISANSHIELD_MANIFEST_VERSION", "public_v2")

# Comma-separated list of allowed origins for the web demo / Flutter app during development.
# Locked down to real domains before any public deploy.
CORS_ORIGINS = os.environ.get("KISANSHIELD_CORS_ORIGINS", "*").split(",")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB: generous for a phone photo, small enough to block abuse
MIN_CONFIDENCE_FOR_RESULT = 0.35  # below this, "not sure" beats a guessed disease name
