# Data decisions log

Every cleaning and labelling decision is recorded here with its evidence. Decisions take effect through
`data/datasets.yaml` (class mapping and quality rules), `data/review/image_overrides.csv` (single images), or the
build scripts. Evidence references point to [`docs/eda/EDA_FINDINGS.md`](../../docs/eda/EDA_FINDINGS.md).

**Status:**
- **Applied:** in effect and not agronomic, so no sign-off needed
- **Provisional:** in effect, awaiting agronomist or PI sign-off
- **Pending:** needs an expert before anything changes
- **Planned:** applied at the split and preprocessing step

**Owner:** who must confirm (AGR = agronomist / plant pathologist, PI = principal investigator, ENG = engineering).

| ID | Decision | Evidence | Where applied | Owner | Status |
|---|---|---|---|---|---|
| D-01 | Chickpea `1 (HR)` (0–10% wilted) is used as **healthy** (`PUL_HEALTHY`, severity 0) | The FUSARIUM-22 readme describes its categories as "healthy and fusarium wilt diseased". Without it, chickpea has only one class and cannot be trained. F9: overlaps with mild wilt | datasets.yaml `class_map` | AGR | Provisional |
| D-02 | Chickpea wilt moves **into the model** (`in_model=true`) | You chose FUSARIUM-22, and its readme says these are leaf images | taxonomy/classes_v1.csv | AGR, PI | Provisional |
| D-03 | **Pea not used in v1.** All pea images stay on hold | F8: pods on paper, heavy blur, 48% duplicates, background shortcut | datasets.yaml (`null`) | PI | Provisional |
| D-04 | Wheat **Septoria and tan spot not in v1** (held) | Single source, uncommon in central India, not in taxonomy v1 | datasets.yaml (`null`) | AGR | Provisional |
| D-05 | Soybean **Septoria brown spot** stays held until the agronomist decides whether to add the class | Present in Indian data (268 images), but overlaps rust and frog-eye (F10) | datasets.yaml (`null`) | AGR | Pending |
| D-06 | When duplicate photos carry **different labels**, exclude all of them. Labels are compared by class, or by source label for held images. An expert label on one copy wins; copies of an expert-rejected image are excluded too | F6: 350 groups (black vs brown rust, spot blotch vs septoria or tan spot, SoyNet diseased vs healthy); neither label can be trusted | build_manifest.py | ENG | Applied (1,010 images) |
| D-07 | Quality rules: Kaggle wheat images must be ≥ 96 px on the short side; pea sharpness ≥ 8 | F7: tiny crops and motion blur, checked visually | datasets.yaml `quality` | ENG | Applied (165 images) |
| D-08 | SoyNet's 1,163 diseased photos (Madhya Pradesh) get **expert per-disease labels** | Only Madhya Pradesh data, but labelled just "diseased" | review pack `soynet_relabel` | AGR | Pending |
| D-09 | Kaggle `leaf_blight` → `WHT_SPOT_BLOTCH` | The Helminthosporium leaf blight / spot blotch complex is common in India | datasets.yaml | AGR | Provisional |
| D-10 | MH-SoyaHealthVision `mosaic` → `SOY_YMV` | Yellow mosaic is the dominant soybean mosaic in India | datasets.yaml | AGR | Provisional |
| D-11 | Ignore the Kaggle wheat set's own train/valid/test split | F5: 333 duplicate groups cross its splits | split step | ENG | Applied |
| D-12 | Preprocessing: **tile YELLOW-RUST-19 strips into near-square crops**; letterbox (pad) other images; use background-robust augmentation (random crops, colour jitter) | F2, F3: shape and background shortcuts | split / preprocessing | ENG | Planned |
| D-13 | Evaluation: report **per-source** accuracy and leave-one-source-out results where a class has 2+ sources. Never present public-data accuracy as field accuracy | F1: sources are fully separable | evaluation | ENG, PI | Planned |
| D-14 | Balance: cap the YELLOW-RUST-19 yellow-rust contribution (~1,500 images) and use class-weighted loss | F4: 20.6× imbalance in wheat | split step | ENG | Planned |
| D-15 | Audit Kaggle black and brown rust with **100** images each (others 50) | F6: black and brown rust labels conflict | review pack | ENG | Applied |
| D-16 | During the label audit, check Kaggle mildew images with dark backgrounds | F3 | review pack | AGR | Pending |
| D-17 | Severity maps (YELLOW-RUST-19 Cobb scale, FUSARIUM-22 wilt %) → app severity 0–4 | Needed for advice by severity | datasets.yaml `severity_map` | AGR | Provisional |

## Sign-off

| Role | Name | Decisions confirmed | Date |
|---|---|---|---|
| Agronomist / plant pathologist | | | |
| Principal investigator | | | |
