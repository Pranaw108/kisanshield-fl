"""Tests for build_thumbnails.py. Run: pytest data/scripts/tests -q"""

import csv
import io
import logging
import sys
import zipfile
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_thumbnails as bt  # noqa: E402

FIELDS = ["image_id", "archive", "member_path", "status", "sha256"]


def jpeg(color, size=(800, 400)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "JPEG")
    return buf.getvalue()


def write_zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)


def write_manifest(path: Path, rows: list[dict]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return path


@pytest.fixture()
def world(tmp_path):
    root = tmp_path / "data"
    root.mkdir()
    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w") as zf:
        zf.writestr("leaf/n1.jpg", jpeg("green"))
    write_zip(root / "a.zip", {"A/x.jpg": jpeg("red"), "A/y.jpg": jpeg("blue"), "A/inner.zip": inner.getvalue()})
    rows = [
        {"image_id": "x", "archive": "a.zip", "member_path": "A/x.jpg", "status": "use", "sha256": "s1"},
        {"image_id": "y", "archive": "a.zip", "member_path": "A/y.jpg", "status": "exclude", "sha256": "s2"},
        {"image_id": "n1", "archive": "a.zip", "member_path": "A/inner.zip!/leaf/n1.jpg", "status": "hold", "sha256": "s3"},
    ]
    return root, tmp_path, rows


def run(root, manifest, *extra):
    return bt.main(["--data-root", str(root), "--manifest", str(manifest), "--workers", "2", *extra])


def thumbs(root):
    return root / "cache" / f"thumbs_{bt.THUMB_SIZE}"


def test_builds_selected_images_including_nested(world):
    root, tmp, rows = world
    assert run(root, write_manifest(tmp / "m.csv", rows)) == 0
    assert sorted(p.stem for p in thumbs(root).glob("*.jpg")) == ["n1", "x"]
    with Image.open(thumbs(root) / "x.jpg") as img:
        assert img.size == (384, 192)                          # aspect ratio kept
    assert not list(thumbs(root).glob("*.tmp"))


def test_rebuilds_when_source_changes_and_skips_when_unchanged(world, caplog):
    root, tmp, rows = world
    manifest = write_manifest(tmp / "m.csv", rows)
    assert run(root, manifest) == 0
    with caplog.at_level(logging.INFO):
        assert run(root, manifest) == 0
    assert "0 to build" in caplog.text

    rows[0]["sha256"] = "s1-new"                               # same image_id, new content
    caplog.clear()
    with caplog.at_level(logging.INFO):
        assert run(root, write_manifest(manifest, rows)) == 0
    assert "1 to build" in caplog.text


def test_prune_is_opt_in(world):
    root, tmp, rows = world
    manifest = write_manifest(tmp / "m.csv", rows)
    assert run(root, manifest, "--statuses", "use", "hold", "exclude") == 0
    assert (thumbs(root) / "y.jpg").exists()

    assert run(root, manifest) == 0                            # y no longer selected: kept by default
    assert (thumbs(root) / "y.jpg").exists()
    assert run(root, manifest, "--prune") == 0
    assert not (thumbs(root) / "y.jpg").exists()
    assert "y" not in bt.load_index(thumbs(root) / "index.csv")


def test_failures_are_logged_with_image_id(world, caplog):
    root, tmp, rows = world
    rows.append({"image_id": "gone", "archive": "a.zip", "member_path": "A/missing.jpg", "status": "use", "sha256": "s4"})
    write_zip(root / "b.zip", {"B/bad.jpg": b"not an image"})
    rows.append({"image_id": "bad", "archive": "b.zip", "member_path": "B/bad.jpg", "status": "use", "sha256": "s5"})
    with caplog.at_level(logging.ERROR):
        assert run(root, write_manifest(tmp / "m.csv", rows)) == 1
    assert "gone" in caplog.text and "member not found" in caplog.text
    assert "bad" in caplog.text and "UnidentifiedImageError" in caplog.text


def test_cli_validation(world, tmp_path):
    root, _, _ = world
    with pytest.raises(SystemExit):
        bt.main(["--data-root", str(root), "--statuses", "banana"])
    with pytest.raises(SystemExit):
        bt.main(["--data-root", str(root), "--manifest", str(tmp_path / "nope.csv")])


def test_interrupted_write_leaves_no_partial_file(tmp_path, monkeypatch):
    out = tmp_path / "t.jpg"
    data = jpeg("red")

    def boom(*_a, **_k):
        raise OSError("disk full")
    monkeypatch.setattr(Image.Image, "save", boom)
    assert "disk full" in bt.save_thumbnail(data, str(out))
    assert not out.exists() and not Path(str(out) + ".tmp").exists()
