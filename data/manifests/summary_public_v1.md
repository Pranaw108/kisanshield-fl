# Public data manifest — public_v1

Generated 2026-09-18 by `data/scripts/build_manifest.py`.

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
| chickpea_fusarium_22 | 3,378 | 959 | 15,002 | 19,339 |
| kaggle_wheat_plant_diseases | 4,781 | 1,231 | 8,142 | 14,154 |
| mh_soyahealthvision | 1,916 | 284 | 582 | 2,782 |
| pea_pisum_sativum | 0 | 5,048 | 7,018 | 12,066 |
| soynet | 124 | 1,163 | 8,051 | 9,338 |
| yellow_rust_19 | 5,375 | 2 | 15,044 | 20,421 |
| **Total** | **15,574** | **8,687** | **53,839** | **78,100** |

## Usable images per taxonomy class

| class_id | images | from datasets |
|---|---:|---|
| PUL_CHICKPEA_WILT | 3,378 | chickpea_fusarium_22 (3,378) |
| SOY_FROGEYE | 168 | mh_soyahealthvision (168) |
| SOY_HEALTHY | 328 | mh_soyahealthvision (204), soynet (124) |
| SOY_RUST | 845 | mh_soyahealthvision (845) |
| SOY_YMV | 699 | mh_soyahealthvision (699) |
| WHT_BLACK_RUST | 296 | kaggle_wheat_plant_diseases (296) |
| WHT_BROWN_RUST | 1,143 | kaggle_wheat_plant_diseases (1,143) |
| WHT_HEALTHY | 1,188 | kaggle_wheat_plant_diseases (986), yellow_rust_19 (202) |
| WHT_POWDERY_MILDEW | 817 | kaggle_wheat_plant_diseases (817) |
| WHT_SPOT_BLOTCH | 643 | kaggle_wheat_plant_diseases (643) |
| WHT_YELLOW_RUST | 6,069 | yellow_rust_19 (5,173), kaggle_wheat_plant_diseases (896) |

## Held images (need a decision)

| Dataset | Source label | Reason | Images |
|---|---|---|---:|
| chickpea_fusarium_22 | 1_hr | needs_expert_review | 959 |
| kaggle_wheat_plant_diseases | black_rust | duplicate_label_conflict | 162 |
| kaggle_wheat_plant_diseases | brown_rust | duplicate_label_conflict | 123 |
| kaggle_wheat_plant_diseases | leaf_blight | duplicate_label_conflict | 23 |
| kaggle_wheat_plant_diseases | mildew | duplicate_label_conflict | 4 |
| kaggle_wheat_plant_diseases | septoria | pending_taxonomy | 348 |
| kaggle_wheat_plant_diseases | tan_spot | duplicate_label_conflict | 2 |
| kaggle_wheat_plant_diseases | tan_spot | pending_taxonomy | 569 |
| mh_soyahealthvision | soyabean_frog_leaf_eye | duplicate_label_conflict | 1 |
| mh_soyahealthvision | soyabean_mosaic | duplicate_label_conflict | 8 |
| mh_soyahealthvision | soyabean_rust | duplicate_label_conflict | 7 |
| mh_soyahealthvision | soyabean_spectoria_brown_spot | pending_taxonomy | 268 |
| pea_pisum_sativum | anthracnose | pending_taxonomy | 371 |
| pea_pisum_sativum | ascochyta_blight | pending_taxonomy | 2,483 |
| pea_pisum_sativum | botrytis_blight | pending_taxonomy | 1,034 |
| pea_pisum_sativum | downey_mildew | pending_taxonomy | 236 |
| pea_pisum_sativum | fusarium_wilt | pending_taxonomy | 463 |
| pea_pisum_sativum | healthy_pea | pending_taxonomy | 201 |
| pea_pisum_sativum | powdery_mildew | pending_taxonomy | 260 |
| soynet | disease_pic | pending_taxonomy | 999 |
| soynet | mobile_disease | pending_taxonomy | 164 |
| yellow_rust_19 | 0 | duplicate_label_conflict | 1 |
| yellow_rust_19 | r | duplicate_label_conflict | 1 |

## Exclusion reasons

| Reason | Images |
|---|---:|
| augmented_copy_of_raw | 30,000 |
| derived_copy_resized_or_grayscale | 7,975 |
| near_duplicate | 7,186 |
| class_dropped | 7,163 |
| exact_duplicate | 1,515 |

## Duplicates (exact SHA-256 + near-duplicate pHash, Hamming distance ≤ 4)

- Duplicate groups: **3,517** covering **12,419** images
- Images removed as exact duplicates: **1,515**; as near duplicates: **7,186**
- Groups spanning two datasets: **513** (kaggle_wheat_plant_diseases ↔ yellow_rust_19: 513)
- Groups spanning a dataset's own train/valid/test split (leakage in the source split): **333**
- Groups with conflicting labels (all members held for review): **131**

## Image quality flags (use + hold images)

- Smaller than 224 px on the short side: **6,733**
- Grayscale: **0**
- Sharpness (Laplacian variance at 256 px): median 504, lowest 5% below 16. Review the blurriest images before training.

## Warnings

- Yellow Rust Disease in Wheat (Raw).zip: ignored non-image files: .txt ×1
- Yellow Rust Disease in Wheat(YELLOW-RUST-19).zip: ignored non-image files: .txt ×1
- FUSARIUM-22.zip: ignored non-image files: .txt ×1
