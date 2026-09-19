"""Tests for build_manifest.py. Run: pytest data/scripts/tests -q"""

import csv
import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_manifest as bm  # noqa: E402

REPO = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def smooth_image(seed: int, size: int = 256) -> Image.Image:
    """A smooth random image: resized copies stay perceptually identical, different seeds do not."""
    rng = np.random.default_rng(seed)
    base = Image.fromarray(rng.integers(0, 255, (8, 8, 3), dtype=np.uint8))
    return base.resize((size, size), Image.BICUBIC)


def jpeg_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=92)
    return buf.getvalue()


def zip_bytes(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


@pytest.fixture()
def fake_world(tmp_path: Path):
    data = tmp_path / "data"
    data.mkdir()
    a1, a2, b1, c1 = (jpeg_bytes(smooth_image(s)) for s in (1, 2, 3, 4))
    a1_small = jpeg_bytes(smooth_image(1).resize((200, 200)))  # near duplicate of a1

    # Dataset A: plain zip with classes, an exact dup, a near dup, an excluded folder, a dropped class, a readme
    (data / "a.zip").write_bytes(zip_bytes({
        "A/train/Healthy/1.jpg": a1,
        "A/train/Healthy/1_copy.jpg": a1,          # exact duplicate
        "A/test/healthy_test/1_small.jpg": a1_small,  # near duplicate, across the source split
        "A/train/Rust/2.jpg": a2,
        "A/train/Aphid/3.jpg": b1,                 # dropped class
        "A/aug/Healthy/9.jpg": c1,                 # excluded folder
        "A/train/Mystery/4.jpg": c1,               # label missing from class_map -> hold
        "A/readme.txt": b"hello",
    }))
    # Dataset B: nested zips; one skipped, one read. Contains a near dup of A's Rust image under another label.
    inner_leaf = zip_bytes({"Leaf_Rust/x.jpg": jpeg_bytes(smooth_image(2).resize((220, 220))),
                            "Leaf_Rust/y.jpg": jpeg_bytes(smooth_image(5))})
    inner_uav = zip_bytes({"uav/z.jpg": jpeg_bytes(smooth_image(6))})
    (data / "b.zip").write_bytes(zip_bytes({"B/Leaf/Leaf_Rust.zip": inner_leaf, "B/UAV/uav.zip": inner_uav}))

    taxonomy = tmp_path / "classes.csv"
    taxonomy.write_text("class_id,crop\nX_HEALTHY,x\nX_RUST,x\nX_OTHER,x\n", encoding="utf-8")
    config = tmp_path / "datasets.yaml"
    config.write_text(r"""
datasets:
  - id: ds_a
    crop: x
    local:
      label_strip_suffixes: [_test]
      archives:
        - file: a.zip
          rules:
            - pattern: '^A/aug/'
              exclude: augmented_copy
            - pattern: '^A/(?P<split>train|test)/(?P<label>[^/]+)/[^/]+$'
    class_map:
      healthy: X_HEALTHY
      rust: X_RUST
      aphid: drop
  - id: ds_b
    crop: x
    local:
      archives:
        - file: b.zip
          rules:
            - pattern: 'B/UAV/'
              skip: uav_not_used
            - pattern: 'B/Leaf/(?P<label>[^/]+)\.zip!/'
    class_map:
      leaf_rust: X_OTHER
""", encoding="utf-8")
    return data, config, taxonomy, tmp_path / "out"


def read_manifest(out: Path) -> dict[str, dict]:
    with (out / f"manifest_{bm.MANIFEST_VERSION}.csv").open(encoding="utf-8") as fh:
        return {r["member_path"]: r for r in csv.DictReader(fh)}


# ---------------------------------------------------------------------------
# unit tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw, suffixes, expected", [
    ("Black Rust", [], "black_rust"),
    ("blast_test_valid", ["_valid", "_test"], "blast"),
    ("1(HR)", [], "1_hr"),
    ("Healthy Pic", [], "healthy_pic"),
    ("0", [], "0"),
    ("_test", ["_test"], "test"),  # never strips a label down to nothing
])
def test_normalise_label(raw, suffixes, expected):
    assert bm.normalise_label(raw, suffixes) == expected


def test_project_config_is_valid():
    """The real datasets.yaml parses and every mapped class exists in the taxonomy."""
    specs = bm.load_config(REPO / "data" / "datasets.yaml", bm.load_taxonomy(REPO / "taxonomy" / "classes_v1.csv"))
    assert {s.id for s in specs} >= {"kaggle_wheat_plant_diseases", "soynet", "chickpea_fusarium_22"}
    assert all(s.archives for s in specs)


def test_config_rejects_unknown_class(tmp_path):
    tax = tmp_path / "t.csv"
    tax.write_text("class_id\nA\n", encoding="utf-8")
    cfg = tmp_path / "c.yaml"
    cfg.write_text("datasets:\n - id: d\n   crop: x\n   local: {archives: [{file: f.zip, rules: []}]}\n"
                   "   class_map: {healthy: NOT_A_CLASS}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="NOT_A_CLASS"):
        bm.load_config(cfg, bm.load_taxonomy(tax))


def test_hash_image_handles_corrupt_bytes():
    out = bm.hash_image(b"not an image")
    assert out["sha256"] and out["error"]


def test_group_near_duplicates_basic():
    groups = bm.group_near_duplicates(["ffffffffffffffff", "fffffffffffffff0", "0000000000000000"], threshold=4)
    assert groups == [[0, 1]]


def test_group_near_duplicates_does_not_chain():
    # B is 4 bits from A, C is 4 bits from B but 8 from A: C must NOT join A's group.
    a, b, c = "0000000000000000", "000000000000000f", "00000000000000ff"
    assert bm.group_near_duplicates([a, b, c], threshold=4) == [[0, 1]]
    # leader order matters: the first (preferred) image is always the one kept
    assert bm.group_near_duplicates([b, a, c], threshold=4) == [[0, 1, 2]]


# ---------------------------------------------------------------------------
# end-to-end
# ---------------------------------------------------------------------------

def run(fake_world, *extra, overrides=None):
    data, config, taxonomy, out = fake_world
    return bm.main(["--data-root", str(data), "--out", str(out), "--config", str(config),
                    "--taxonomy", str(taxonomy), "--workers", "2",
                    "--overrides", str(overrides or out / "no_overrides.csv"), *extra])


def test_overrides_relabel_and_exclude(fake_world, monkeypatch, tmp_path):
    monkeypatch.setattr(bm, "REPO_SUMMARY_DIR", tmp_path / "repo_summary")
    assert run(fake_world) == 0
    ids = {p: r["image_id"] for p, r in read_manifest(fake_world[3]).items()}

    overrides = tmp_path / "overrides.csv"
    overrides.write_text(
        "image_id,action,class_id,reason,decided_by,status\n"
        f"{ids['A/train/Mystery/4.jpg']},use,X_RUST,expert_relabel,agronomist,approved\n"
        f"{ids['A/train/Healthy/1.jpg']},exclude,,blurry,engineer,provisional\n"
        "ffffffffffffffff,exclude,,blurry,engineer,provisional\n", encoding="utf-8")
    assert run(fake_world, overrides=overrides) == 0
    m = read_manifest(fake_world[3])
    assert m["A/train/Mystery/4.jpg"]["status"] == "use" and m["A/train/Mystery/4.jpg"]["class_id"] == "X_RUST"
    assert m["A/train/Healthy/1.jpg"]["reason"] == "review:blurry"
    # copies of the rejected image must not come back as the new "kept" image
    for copy in ("A/train/Healthy/1_copy.jpg", "A/test/healthy_test/1_small.jpg"):
        assert m[copy]["reason"] == "duplicate_of_rejected"
        assert m[copy]["duplicate_of"] == ids["A/train/Healthy/1.jpg"]
    summary = (tmp_path / "repo_summary" / f"summary_{bm.MANIFEST_VERSION}.md").read_text(encoding="utf-8")
    assert "review:blurry" in summary and "unknown image ids" in summary


def dup_row(image_id, status, class_id="", source_label="lbl", reason="", phash="0000000000000000", ds="d"):
    return {"image_id": image_id, "dataset_id": ds, "status": status, "class_id": class_id,
            "source_label": source_label, "reason": reason, "phash": phash, "sha256": image_id,
            "width": 100, "height": 100, "member_path": image_id, "split_source": "",
            "duplicate_of": "", "dup_group": ""}


def test_use_and_hold_copies_with_different_labels_conflict():
    # same photo: one copy mapped to a class, the other held under a different source label
    rows = [dup_row("a", "use", "X_RUST", "leaf_blight"), dup_row("b", "hold", "", "septoria")]
    bm.resolve_duplicates(rows, 4, {"d": 0})
    assert [r["reason"] for r in rows] == ["duplicate_label_conflict"] * 2


def test_same_class_from_two_sources_is_not_a_conflict():
    rows = [dup_row("a", "use", "X_RUST", "s", ds="d1"), dup_row("b", "use", "X_RUST", "yellow_rust", ds="d2")]
    bm.resolve_duplicates(rows, 4, {"d1": 0, "d2": 1})
    assert rows[0]["status"] == "use" and rows[1]["reason"] == "near_duplicate"


def test_expert_label_wins_over_conflicting_copy():
    rows = [dup_row("a", "use", "X_RUST", "leaf_blight"),
            dup_row("b", "use", "X_OTHER", "septoria", reason="review:expert_label")]
    bm.resolve_duplicates(rows, 4, {"d": 0})
    assert rows[1]["status"] == "use" and rows[1]["class_id"] == "X_OTHER"
    assert rows[0]["reason"] == "near_duplicate" and rows[0]["duplicate_of"] == "b"


def test_experts_disagreeing_on_copies_excludes_all():
    rows = [dup_row("a", "use", "X_RUST", reason="review:x"), dup_row("b", "use", "X_OTHER", reason="review:y")]
    bm.resolve_duplicates(rows, 4, {"d": 0})
    assert all(r["reason"] == "duplicate_label_conflict" for r in rows)


def test_use_override_on_unhashed_image_is_rejected(tmp_path):
    rows = [dict(dup_row("a", "exclude", reason="augmented_copy"), phash="")]
    csv_path = tmp_path / "o.csv"
    csv_path.write_text("image_id,action,class_id,reason\na,use,X_RUST,x\n", encoding="utf-8")
    with pytest.raises(ValueError, match="never hashed"):
        bm.apply_overrides(rows, csv_path, {"X_RUST"})


def test_legacy_cache_is_migrated_and_versioned(tmp_path, monkeypatch):
    cache = tmp_path / "hash_cache.csv"
    cache.write_text("key,sha256,phash,width,height,mode,is_grayscale,sharpness_256,brightness,error\n"
                     "k1,s,p,1,1,RGB,0,1,1,\n", encoding="utf-8")
    assert set(bm.load_cache(cache)) == {"k1"}                  # old rows count as version 1
    assert "hash_version" in cache.read_text(encoding="utf-8").splitlines()[0]
    monkeypatch.setattr(bm, "HASH_VERSION", "2")
    assert bm.load_cache(cache) == {}                            # new hashing code ignores them


def test_quality_rules():
    spec = bm.DatasetSpec("d", "x", {}, {}, [], [], min_short_side=100, min_sharpness=5.0)
    rows = [
        {"dataset_id": "d", "status": "use", "width": 80, "height": 300, "sharpness_256": 50, "reason": ""},
        {"dataset_id": "d", "status": "hold", "width": 300, "height": 300, "sharpness_256": 2, "reason": ""},
        {"dataset_id": "d", "status": "use", "width": 300, "height": 300, "sharpness_256": 50, "reason": ""},
        {"dataset_id": "d", "status": "exclude", "width": 10, "height": 10, "sharpness_256": 0, "reason": "x"},
    ]
    bm.apply_quality_rules(rows, {"d": spec})
    assert [r["reason"] for r in rows] == ["too_small", "too_blurry", "", "x"]


def test_overrides_reject_invalid_class(fake_world, monkeypatch, tmp_path):
    monkeypatch.setattr(bm, "REPO_SUMMARY_DIR", tmp_path / "repo_summary")
    bad = tmp_path / "bad.csv"
    bad.write_text("image_id,action,class_id,reason\nabc,use,NOT_A_CLASS,x\n", encoding="utf-8")
    with pytest.raises(ValueError, match="NOT_A_CLASS"):
        run(fake_world, overrides=bad)


def test_end_to_end(fake_world, monkeypatch, tmp_path):
    monkeypatch.setattr(bm, "REPO_SUMMARY_DIR", tmp_path / "repo_summary")
    assert run(fake_world) == 0
    m = read_manifest(fake_world[3])

    assert m["A/train/Healthy/1.jpg"]["status"] == "use"
    assert m["A/train/Healthy/1_copy.jpg"]["reason"] == "exact_duplicate"
    assert m["A/test/healthy_test/1_small.jpg"]["reason"] == "near_duplicate"
    assert m["A/test/healthy_test/1_small.jpg"]["duplicate_of"] == m["A/train/Healthy/1.jpg"]["image_id"]
    assert m["A/test/healthy_test/1_small.jpg"]["source_label"] == "healthy"   # suffix stripped
    assert m["A/train/Aphid/3.jpg"]["reason"] == "class_dropped"
    assert m["A/aug/Healthy/9.jpg"]["reason"] == "augmented_copy"
    assert m["A/aug/Healthy/9.jpg"]["sha256"] == ""                            # excluded files are not hashed
    assert m["A/train/Mystery/4.jpg"]["status"] == "hold"
    assert not any("readme" in p for p in m)

    nested = "B/Leaf/Leaf_Rust.zip!/Leaf_Rust/y.jpg"
    assert m[nested]["status"] == "use" and m[nested]["class_id"] == "X_OTHER"
    assert not any("UAV" in p for p in m)                                      # skipped nested zip never read

    # A's rust image and B's near copy carry different classes -> both held for review
    conflict = [m["A/train/Rust/2.jpg"], m["B/Leaf/Leaf_Rust.zip!/Leaf_Rust/x.jpg"]]
    assert all(r["reason"] == "duplicate_label_conflict" for r in conflict)
    assert conflict[0]["dup_group"] == conflict[1]["dup_group"]

    summary = (tmp_path / "repo_summary" / f"summary_{bm.MANIFEST_VERSION}.md").read_text(encoding="utf-8")
    assert "uav_not_used: 1" in summary
    assert "`mystery`" in summary


def test_rerun_uses_cache(fake_world, monkeypatch, tmp_path):
    monkeypatch.setattr(bm, "REPO_SUMMARY_DIR", tmp_path / "repo_summary")
    assert run(fake_world) == 0
    first = read_manifest(fake_world[3])

    def boom(*_a, **_k):
        raise AssertionError("hash_image should not be called when every file is cached")
    monkeypatch.setattr(bm, "hash_image", boom)
    assert run(fake_world) == 0
    assert read_manifest(fake_world[3]) == first


def test_list_only_does_not_hash(fake_world, monkeypatch, tmp_path):
    monkeypatch.setattr(bm, "REPO_SUMMARY_DIR", tmp_path / "repo_summary")
    assert run(fake_world, "--list-only") == 0
    assert not (fake_world[3] / f"manifest_{bm.MANIFEST_VERSION}.csv").exists()
    assert (tmp_path / "repo_summary" / f"summary_{bm.MANIFEST_VERSION}_list_only.md").exists()
