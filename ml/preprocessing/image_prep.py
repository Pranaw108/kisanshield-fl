"""Image preprocessing shared by training and inference (backend, and later on-device).

Using the same function in both places matters: a model trained on one kind of resize and
served with another silently loses accuracy. See ml/README.md.

Letterbox (pad to a square, keep aspect ratio) instead of squashing to a square, because some
source images are extreme aspect ratios (see docs/eda/EDA_FINDINGS.md, F2) and stretching them
would distort real disease features.
"""

from __future__ import annotations

import io

import numpy as np
from PIL import Image, ImageOps

IMAGE_SIZE = 224
PAD_COLOR = (114, 114, 114)  # mid-grey; not black or white, so it cannot look like a real background


def letterbox(img: Image.Image, size: int = IMAGE_SIZE) -> Image.Image:
    """Resize to fit in a size x size box, keeping aspect ratio, padded to fill the box."""
    img = img.convert("RGB")
    img.thumbnail((size, size), Image.LANCZOS)
    canvas = Image.new("RGB", (size, size), PAD_COLOR)
    canvas.paste(img, ((size - img.width) // 2, (size - img.height) // 2))
    return canvas


def load_and_letterbox(data: bytes, size: int = IMAGE_SIZE) -> Image.Image:
    """Decode image bytes (any source: upload, zip member, camera) with EXIF rotation applied."""
    with Image.open(io.BytesIO(data)) as img:
        return letterbox(ImageOps.exif_transpose(img), size)


def to_array(img: Image.Image) -> np.ndarray:
    """A letterboxed image as a batch-ready float32 array, scaled the way EfficientNet expects."""
    from tensorflow.keras.applications.efficientnet import preprocess_input
    arr = np.asarray(img, dtype=np.float32)
    return preprocess_input(arr)[np.newaxis, ...]
