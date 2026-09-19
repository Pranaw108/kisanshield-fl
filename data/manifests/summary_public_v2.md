# Public data manifest — public_v2

Generated 2026-09-19 by `data/scripts/build_manifest.py`.

**Status meaning:** `use` = ready for training · `hold` = waiting on a taxonomy or expert decision · `exclude` = never used (reason recorded).

## Archives

| Archive | Dataset | Size (GB) | Downloaded | Images listed | Skipped members |
|---|---|---:|---|---:|---|
| wheat data.zip | kaggle_wheat_plant_diseases | 6.09 | 2026-09-15 | 14,154 | — |
| Yellow Rust Disease in Wheat (Raw).zip | yellow_rust_19 | 0.65 | 2026-09-18 | 5,421 | — |
| Yellow Rust Disease in Wheat(YELLOW-RUST-19).zip | yellow_rust_19 | 0.8 | 2026-09-18 | 15,000 | — |
| MH-SoyaHealthVision An Indian UAV and Leaf Image Dataset for Integrated Crop Health Assessment.zip | mh_soyahealthvision | 9.75 | 2026-09-18 | 2,782 | uav_images_not_used: 4 |
| SoyNet Indian Soybean Image dataset with quality images captured from the agriculture field ( healthy and disease Images).zip | soynet | 8.48 | 2026-09-17 | 9,338 | duplicate_archive_copy: 1 |
| Pisum sativum Image Dataset Healthy and Disease-Af.zip | pea_pisum_sativum | 0.49 | 2026-09-15 | 12,066 | — |
| FUSARIUM-22.zip | chickpea_fusarium_22 | 6.57 | 2026-09-18 | 19,339 | — |

## Status by dataset

| Dataset | use | hold | exclude | total |
|---|---:|---:|---:|---:|
| chickpea_fusarium_22 | 4,337 | 0 | 15,002 | 19,339 |
| kaggle_wheat_plant_diseases | 4,513 | 917 | 8,724 | 14,154 |
| mh_soyahealthvision | 1,916 | 268 | 598 | 2,782 |
| pea_pisum_sativum | 0 | 4,947 | 7,119 | 12,066 |
| soynet | 116 | 1,163 | 8,059 | 9,338 |
| yellow_rust_19 | 5,375 | 0 | 15,046 | 20,421 |
| **Total** | **16,257** | **7,295** | **54,548** | **78,100** |

## Usable images per taxonomy class

| class_id | images | from datasets |
|---|---:|---|
| PUL_CHICKPEA_WILT | 3,378 | chickpea_fusarium_22 (3,378) |
| PUL_HEALTHY | 959 | chickpea_fusarium_22 (959) |
| SOY_FROGEYE | 168 | mh_soyahealthvision (168) |
| SOY_HEALTHY | 320 | mh_soyahealthvision (204), soynet (116) |
| SOY_RUST | 845 | mh_soyahealthvision (845) |
| SOY_YMV | 699 | mh_soyahealthvision (699) |
| WHT_BLACK_RUST | 292 | kaggle_wheat_plant_diseases (292) |
| WHT_BROWN_RUST | 1,030 | kaggle_wheat_plant_diseases (1,030) |
| WHT_HEALTHY | 1,188 | kaggle_wheat_plant_diseases (986), yellow_rust_19 (202) |
| WHT_POWDERY_MILDEW | 815 | kaggle_wheat_plant_diseases (815) |
| WHT_SPOT_BLOTCH | 494 | kaggle_wheat_plant_diseases (494) |
| WHT_YELLOW_RUST | 6,069 | yellow_rust_19 (5,173), kaggle_wheat_plant_diseases (896) |

## Held images (need a decision)

| Dataset | Source label | Reason | Images |
|---|---|---|---:|
| kaggle_wheat_plant_diseases | septoria | pending_taxonomy | 348 |
| kaggle_wheat_plant_diseases | tan_spot | pending_taxonomy | 569 |
| mh_soyahealthvision | soyabean_spectoria_brown_spot | pending_taxonomy | 268 |
| pea_pisum_sativum | anthracnose | pending_taxonomy | 344 |
| pea_pisum_sativum | ascochyta_blight | pending_taxonomy | 2,425 |
| pea_pisum_sativum | botrytis_blight | pending_taxonomy | 1,025 |
| pea_pisum_sativum | downey_mildew | pending_taxonomy | 233 |
| pea_pisum_sativum | fusarium_wilt | pending_taxonomy | 463 |
| pea_pisum_sativum | healthy_pea | pending_taxonomy | 201 |
| pea_pisum_sativum | powdery_mildew | pending_taxonomy | 256 |
| soynet | disease_pic | pending_taxonomy | 999 |
| soynet | mobile_disease | pending_taxonomy | 164 |

## Exclusion reasons

| Reason | Images |
|---|---:|
| augmented_copy_of_raw | 30,000 |
| derived_copy_resized_or_grayscale | 7,975 |
| class_dropped | 7,163 |
| near_duplicate | 6,865 |
| exact_duplicate | 1,370 |
| duplicate_label_conflict | 1,010 |
| too_small | 111 |
| too_blurry | 54 |

## Duplicates (exact SHA-256 + near-duplicate pHash, Hamming distance ≤ 4)

- Duplicate groups: **3,512** covering **12,407** images
- Images removed as exact duplicates: **1,370**; as near duplicates: **6,865**
- Groups spanning two datasets: **513** (kaggle_wheat_plant_diseases ↔ yellow_rust_19: 513)
- Groups spanning a dataset's own train/valid/test split (leakage in the source split): **333**
- Groups with conflicting labels, including held images (all members excluded): **350**
- Groups that copy an expert-rejected image (copies excluded): **0**

## Review decisions applied (data/review/image_overrides.csv)

- None

## Image quality flags (use + hold images)

- Smaller than 224 px on the short side: **6,537**
- Grayscale: **0**
- Sharpness (Laplacian variance at 256 px): median 529, lowest 5% below 16. Review the blurriest images before training.

## Warnings

- Yellow Rust Disease in Wheat (Raw).zip: ignored non-image files: .txt ×1
- Yellow Rust Disease in Wheat(YELLOW-RUST-19).zip: ignored non-image files: .txt ×1
- FUSARIUM-22.zip: ignored non-image files: .txt ×1
