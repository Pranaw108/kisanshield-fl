"""Tests for build_splits.py. Run: pytest data/scripts/tests -q"""

import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_manifest as bm  # noqa: E402
import build_splits as bs  # noqa: E402


def test_split_stratum_covers_val_and_test_when_possible():
    rng = random.Random(0)
    result = bs.split_stratum([f"i{n}" for n in range(20)], rng)
    counts = {v: list(result.values()).count(v) for v in ("train", "val", "test")}
    assert counts["val"] > 0 and counts["test"] > 0
    assert sum(counts.values()) == 20


def test_split_stratum_never_starves_a_tiny_group():
    rng = random.Random(0)
    result = bs.split_stratum(["a", "b", "c"], rng)
    assert set(result.values()) <= {"train", "val", "test"}
    assert len(result) == 3          # every image gets a split, none dropped


def test_split_stratum_is_deterministic():
    ids = [f"i{n}" for n in range(50)]
    a = bs.split_stratum(ids, random.Random(bs.SEED))
    b = bs.split_stratum(ids, random.Random(bs.SEED))
    assert a == b


def test_no_leakage_between_splits():
    """Every image appears in exactly one split across all strata."""
    rng = random.Random(bs.SEED)
    seen = {}
    for stratum in range(5):
        result = bs.split_stratum([f"s{stratum}_i{n}" for n in range(30)], rng)
        seen.update(result)
    assert len(seen) == 150 and len(set(seen)) == 150


def test_end_to_end(tmp_path, capsys):
    root = tmp_path
    (root / "manifests").mkdir()
    manifest = root / "manifests" / f"manifest_{bm.MANIFEST_VERSION}.csv"
    rows = [{"image_id": f"yr{i}", "dataset_id": "yellow_rust_19", "class_id": "WHT_YELLOW_RUST",
             "status": "use"} for i in range(2000)]
    rows += [{"image_id": f"h{i}", "dataset_id": "kaggle_wheat", "class_id": "WHT_HEALTHY",
             "status": "use"} for i in range(50)]
    rows.append({"image_id": "held", "dataset_id": "kaggle_wheat", "class_id": "", "status": "hold"})
    with manifest.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["image_id", "dataset_id", "class_id", "status"])
        w.writeheader()
        w.writerows(rows)

    assert bs.main(["--data-root", str(root)]) == 0
    out = list(csv.DictReader((root / "manifests" / f"splits_{bm.MANIFEST_VERSION}.csv").open(encoding="utf-8")))

    assert "held" not in {r["image_id"] for r in out}                       # only `use` rows are split
    yr_train = [r for r in out if r["dataset_id"] == "yellow_rust_19" and r["split"] == "train"]
    assert len(yr_train) == bs.YELLOW_RUST_CAP                              # D-14 cap applied
    assert sum(1 for r in out if r["split"] == "unused") == 2000 - len(yr_train) - \
        sum(1 for r in out if r["dataset_id"] == "yellow_rust_19" and r["split"] in ("val", "test"))
    small = [r for r in out if r["dataset_id"] == "kaggle_wheat"]
    assert {r["split"] for r in small} & {"val", "test"}                    # small class still covered
