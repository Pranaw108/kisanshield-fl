"""Tests for review_pack.py. Run: pytest data/scripts/tests -q"""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import build_manifest as bm  # noqa: E402
import review_pack as rp  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
BY_CROP = {"soybean": {"SOY_RUST", "SOY_HEALTHY", "UNKNOWN"}, "pulses": {"PUL_CHICKPEA_WILT", "UNKNOWN"},
           "all": {"UNKNOWN"}}
KNOWN = {"img_soy": "soybean", "img_chick": "chickpea"}


def row(**kw):
    base = {"manifest_version": bm.MANIFEST_VERSION, "image_id": "img_soy", "crop": "soybean",
            "current_class": "SOY_RUST", "verdict": "", "correct_class": "", "notes": ""}
    return {**base, **kw}


def check(**kw):
    return rp.check_row(2, row(**kw), KNOWN, BY_CROP)


# ---------------------------------------------------------------------------
# the validation matrix
# ---------------------------------------------------------------------------

def test_blank_row_is_skipped():
    assert check() == ([], None)


def test_correct_changes_nothing():
    assert check(verdict="correct") == ([], None)


def test_correct_with_a_class_is_rejected():
    errors, override = check(verdict="correct", correct_class="SOY_HEALTHY")
    assert override is None and "must leave correct_class empty" in errors[0]


def test_correct_needs_an_existing_class():
    errors, _ = check(verdict="correct", current_class=rp.NO_CLASS)
    assert "use 'label'" in errors[0]


def test_wrong_requires_a_class():
    errors, override = check(verdict="wrong")
    assert override is None and "needs correct_class" in errors[0]


def test_wrong_with_class_relabels():
    assert check(verdict="wrong", correct_class="SOY_HEALTHY") == ([], ("img_soy", "use", "SOY_HEALTHY", "expert_wrong"))


def test_label_assigns_a_class_to_an_unlabelled_image():
    errors, override = check(verdict="label", correct_class="SOY_RUST", current_class=rp.NO_CLASS)
    assert errors == [] and override == ("img_soy", "use", "SOY_RUST", "expert_label")


@pytest.mark.parametrize("verdict", ["wrong_unknown", "not_a_leaf", "unusable"])
def test_rejections_exclude_the_image(verdict):
    assert check(verdict=verdict) == ([], ("img_soy", "exclude", "", f"expert_{verdict}"))


def test_unsure_holds_instead_of_excluding():
    """An expert who cannot decide should not silently delete the image."""
    assert check(verdict="unsure") == ([], ("img_soy", "hold", "", "expert_unsure"))


def test_unknown_verdict_is_rejected():
    errors, _ = check(verdict="maybe")
    assert "unknown verdict" in errors[0]


# ---------------------------------------------------------------------------
# integrity checks
# ---------------------------------------------------------------------------

def test_class_must_match_the_crop():
    errors, _ = check(verdict="wrong", correct_class="PUL_CHICKPEA_WILT")   # wheat/pulse class on a soybean photo
    assert "not valid for crop" in errors[0]
    assert check(verdict="wrong", correct_class="PUL_CHICKPEA_WILT", image_id="img_chick")[0] == []


def test_unknown_image_id_is_rejected():
    errors, _ = check(verdict="correct", image_id="does_not_exist")
    assert "not in manifest" in errors[0]


def test_form_from_another_manifest_version_is_rejected():
    errors, _ = check(verdict="correct", manifest_version="public_v1")
    assert "rebuild the review pack" in errors[0]


def test_crop_aliases_map_to_taxonomy_crops():
    assert rp.allowed_classes(BY_CROP, "chickpea") == BY_CROP["pulses"]
    assert rp.allowed_classes(BY_CROP, "unknown_crop") == BY_CROP["all"]


def test_project_taxonomy_loads_with_classes_per_crop():
    by_crop = rp.load_classes_by_crop(REPO / "taxonomy" / "classes_v1.csv")
    assert "SOY_RUST" in by_crop["soybean"] and "WHT_YELLOW_RUST" in by_crop["wheat"]
    assert "UNKNOWN" in by_crop["soybean"]                      # shared classes reach every crop
    assert "SOY_RUST" not in by_crop["wheat"]


def test_review_config_comes_from_datasets_yaml():
    per_group, overrides = rp.load_review_config(REPO / "data" / "datasets.yaml")
    assert per_group == 50
    assert overrides[("kaggle_wheat_plant_diseases", "black_rust")] == 100


# ---------------------------------------------------------------------------
# import
# ---------------------------------------------------------------------------

@pytest.fixture()
def import_world(tmp_path, monkeypatch):
    (tmp_path / "manifests").mkdir()
    manifest = tmp_path / "manifests" / f"manifest_{bm.MANIFEST_VERSION}.csv"
    with manifest.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["image_id", "crop"])
        w.writeheader()
        w.writerows([{"image_id": "img_soy", "crop": "soybean"}, {"image_id": "img2", "crop": "soybean"}])
    monkeypatch.setattr(bm, "DEFAULT_OVERRIDES", tmp_path / "image_overrides.csv")
    monkeypatch.setattr(rp, "HISTORY_PATH", tmp_path / "review_history.csv")
    return tmp_path


def write_form(path, rows):
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rp.FORM_FIELDS)
        w.writeheader()
        w.writerows(rows)
    return path


def read_csv(path):
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def run_import(root, form, who="Dr. A"):
    return rp.main(["import", str(form), "--data-root", str(root), "--decided-by", who])


def test_import_writes_overrides_and_history(import_world):
    form = write_form(import_world / "label_audit.csv",
                      [row(image_id="img_soy", verdict="wrong", correct_class="SOY_HEALTHY", crop="soybean"),
                       row(image_id="img2", verdict="unusable", crop="soybean")])
    assert run_import(import_world, form) == 0
    overrides = read_csv(bm.DEFAULT_OVERRIDES)
    assert {o["image_id"]: (o["action"], o["class_id"]) for o in overrides} == {
        "img_soy": ("use", "SOY_HEALTHY"), "img2": ("exclude", "")}
    assert all(o["decided_by"] == "Dr. A" and o["decided_at"] for o in overrides)
    assert len(read_csv(rp.HISTORY_PATH)) == 2


def test_later_decision_wins_but_history_keeps_both(import_world):
    first = write_form(import_world / "f1.csv", [row(image_id="img_soy", verdict="wrong", correct_class="SOY_HEALTHY")])
    assert run_import(import_world, first) == 0
    second = write_form(import_world / "f2.csv", [row(image_id="img_soy", verdict="not_a_leaf")])
    assert run_import(import_world, second, who="Dr. B") == 0

    current = read_csv(bm.DEFAULT_OVERRIDES)
    assert len(current) == 1 and current[0]["action"] == "exclude" and current[0]["decided_by"] == "Dr. B"
    assert [h["action"] for h in read_csv(rp.HISTORY_PATH)] == ["use", "exclude"]


def test_force_refuses_to_overwrite_answered_form(tmp_path):
    form = tmp_path / "label_audit.csv"
    with form.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=rp.FORM_FIELDS)
        w.writeheader()
        w.writerow(row(verdict="correct"))
    with pytest.raises(SystemExit, match="already has answered rows"):
        rp.write_form(form, __import__("pandas").DataFrame([{"image_id": "x"}]), force=True)


def test_nothing_is_imported_when_a_row_is_invalid(import_world, capsys):
    form = write_form(import_world / "bad.csv",
                      [row(image_id="img_soy", verdict="wrong", correct_class="SOY_HEALTHY"),
                       row(image_id="img2", verdict="wrong")])          # missing class
    assert run_import(import_world, form) == 1
    assert "nothing imported" in capsys.readouterr().out
    assert not bm.DEFAULT_OVERRIDES.exists()
