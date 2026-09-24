# Baseline model results

Trained 2026-09-25 on frozen EfficientNetB0 features (13618 images across train/val/test), 48s training time.

**This is a public-data baseline, not a field-tested model.** Per [EDA finding F1](../../docs/eda/EDA_FINDINGS.md), class is correlated with source dataset within this data, so the per-source breakdown below matters more than the headline number.

## Headline

| Split | macro-F1 |
|---|---:|
| Validation | 0.7987 |
| Test | 0.7833 |

## Per class (test)

| class | precision | recall | f1 | support |
|---|---:|---:|---:|---:|
| PUL_CHICKPEA_WILT | 0.95 | 0.74 | 0.83 | 338 |
| PUL_HEALTHY | 0.48 | 0.85 | 0.62 | 96 |
| SOY_FROGEYE | 0.29 | 0.76 | 0.42 | 17 |
| SOY_HEALTHY | 1.00 | 1.00 | 1.00 | 32 |
| SOY_RUST | 0.88 | 0.52 | 0.66 | 84 |
| SOY_YMV | 0.81 | 0.90 | 0.85 | 70 |
| WHT_BLACK_RUST | 0.62 | 0.72 | 0.67 | 29 |
| WHT_BROWN_RUST | 0.84 | 0.95 | 0.89 | 103 |
| WHT_HEALTHY | 0.90 | 0.80 | 0.85 | 119 |
| WHT_POWDERY_MILDEW | 0.93 | 0.82 | 0.87 | 82 |
| WHT_SPOT_BLOTCH | 0.79 | 0.76 | 0.77 | 49 |
| WHT_YELLOW_RUST | 0.97 | 0.98 | 0.98 | 607 |

## Per source, where a class has 2+ sources (test) — decision D-13

A class scoring very differently between its sources means the model is partly reading *which dataset the photo came from*, not the disease.

| class | source | n | accuracy |
|---|---|---:|---:|
| SOY_HEALTHY | mh_soyahealthvision | 20 | 1.0 |
| SOY_HEALTHY | soynet | 12 | 1.0 |
| WHT_HEALTHY | kaggle_wheat_plant_diseases | 99 | 0.889 |
| WHT_HEALTHY | yellow_rust_19 | 20 | 0.35 |
| WHT_YELLOW_RUST | kaggle_wheat_plant_diseases | 90 | 0.956 |
| WHT_YELLOW_RUST | yellow_rust_19 | 517 | 0.986 |

## Confusion matrix (test)

Rows = true class, columns = predicted class.

| | PUL_CHICKPEA_WILT | PUL_HEALTHY | SOY_FROGEYE | SOY_HEALTHY | SOY_RUST | SOY_YMV | WHT_BLACK_RUST | WHT_BROWN_RUST | WHT_HEALTHY | WHT_POWDERY_MILDEW | WHT_SPOT_BLOTCH | WHT_YELLOW_RUST |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **PUL_CHICKPEA_WILT** | 250 | 88 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **PUL_HEALTHY** | 14 | 82 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **SOY_FROGEYE** | 0 | 0 | 13 | 0 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| **SOY_HEALTHY** | 0 | 0 | 0 | 32 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **SOY_RUST** | 0 | 0 | 28 | 0 | 44 | 12 | 0 | 0 | 0 | 0 | 0 | 0 |
| **SOY_YMV** | 0 | 0 | 4 | 0 | 3 | 63 | 0 | 0 | 0 | 0 | 0 | 0 |
| **WHT_BLACK_RUST** | 0 | 0 | 0 | 0 | 0 | 0 | 21 | 4 | 0 | 0 | 4 | 0 |
| **WHT_BROWN_RUST** | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 98 | 2 | 0 | 0 | 0 |
| **WHT_HEALTHY** | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 5 | 95 | 2 | 1 | 13 |
| **WHT_POWDERY_MILDEW** | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 4 | 1 | 67 | 5 | 2 |
| **WHT_SPOT_BLOTCH** | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 4 | 0 | 3 | 37 | 1 |
| **WHT_YELLOW_RUST** | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 7 | 0 | 0 | 596 |