"""Tests for image_prep.py. Run: pytest ml/preprocessing/tests -q"""

import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import preprocessing.image_prep as ip  # noqa: E402


def test_letterbox_keeps_aspect_ratio_no_distortion():
    wide = Image.new("RGB", (1000, 100), "green")
    out = ip.letterbox(wide, size=224)
    assert out.size == (224, 224)
    # the real content should be a thin band, not stretched to fill the square
    arr = np.asarray(out)
    content_rows = np.where(np.any(arr != ip.PAD_COLOR, axis=(1, 2)))[0]
    assert 0 < (content_rows.max() - content_rows.min() + 1) < 224 * 0.5


def test_letterbox_square_image_fills_the_box():
    square = Image.new("RGB", (300, 300), "blue")
    out = ip.letterbox(square, size=224)
    arr = np.asarray(out)
    assert not np.any(np.all(arr == ip.PAD_COLOR, axis=-1))   # no padding needed for a square


def test_load_and_letterbox_applies_exif_rotation():
    img = Image.new("RGB", (200, 100), "red")
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 CW
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    out = ip.load_and_letterbox(buf.getvalue())
    assert out.size == (ip.IMAGE_SIZE, ip.IMAGE_SIZE)


def test_to_array_shape_and_batch_dim():
    img = ip.letterbox(Image.new("RGB", (50, 50), "white"))
    arr = ip.to_array(img)
    assert arr.shape == (1, ip.IMAGE_SIZE, ip.IMAGE_SIZE, 3)
    assert arr.dtype == np.float32
