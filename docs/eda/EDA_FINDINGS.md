# EDA findings: public datasets

**Scope:** 6 public datasets, 78,100 files. The analysis ran on manifest `public_v1` (24,261 usable or held images).
**Notebook:** [`ml/notebooks/01_eda.ipynb`](../../ml/notebooks/01_eda.ipynb) · **Charts:** [`figures/`](figures/) · **Decisions:** [`data/review/DECISIONS.md`](../../data/review/DECISIONS.md)

## Summary

The public data is usable for a **first baseline**, but it has one serious problem: **the model can tell classes apart by
*which dataset a photo came from* instead of by the disease.** In wheat, a model that never looks at the disease
(it sees only image size, shape, brightness and file size) scores **0.85 macro-F1**, higher than one that looks at
the image content (**0.82**). Public-data accuracy will therefore overstate real-field accuracy. Madhya Pradesh field
photos (roadmap S-04) are the only reliable test.

## Findings

| # | Finding | Evidence | Impact | Action |
|---|---|---|---|---|
| F1 | **Class and source are mixed up** | 8 of 11 usable classes come from a single dataset. A simple model identifies the source dataset with **1.00** macro-F1 for every class that has two sources. t-SNE maps split wheat and soybean by *source*, not by disease. | The model learns camera, background and framing style. Accuracy on public data ≠ accuracy in the field | D-13, D-14, S-04 field data |
| F2 | **Shape shortcut in wheat** | YELLOW-RUST-19 images are long strips (median aspect ratio ~7, about 1000×120 px). Every other dataset is near 1. Metadata-only model: **0.85** macro-F1 vs **0.60** majority-class baseline. | "Long thin image = yellow rust" | D-12 (tile strips into square crops) |
| F3 | **Background shortcuts** | YELLOW-RUST-19 was shot on a dark, grey background (border brightness ~90, saturation ~35) while Kaggle wheat has bright, green field backgrounds (~130 / ~110). Kaggle *mildew* images have very dark backgrounds. Pea *healthy* has the whitest background. | Background predicts class | D-12, D-16, D-03 |
| F4 | **Class imbalance** | Wheat 20.6× (yellow rust 6,069 vs black rust 295). Soybean 5× (rust 845 vs frog-eye 168). Chickpea 3.5× (wilt 3,378 vs healthy 959). | Rare classes get ignored | D-14 |
| F5 | **Heavy duplication** | 8,694 duplicate images removed (burst photos of the same leaf or pod). Pea loses 48%. 513 groups are shared between the Kaggle wheat set and YELLOW-RUST-19. 333 groups leak across Kaggle's own train/test split. | Inflated accuracy if not removed | Done (manifest dedupe), D-11 |
| F6 | **Label noise in Kaggle wheat** | 131 duplicate groups carry conflicting labels, 107 of them *black rust vs brown rust*: the same photo labelled both ways. | Kaggle rust labels are unreliable | D-06 (excluded 1,010 images, see below), D-15 (bigger audit) |
| F7 | **Quality** | 111 Kaggle images under 96 px (tiny crops). 54 pea images heavily motion-blurred. Soybean images score low on sharpness because leaves are smooth, not because they are blurry. | Minor | D-07 |
| F8 | **Pea is a weak dataset for this app** | Mostly pods photographed on white paper, not leaves in the field. Heavy blur, 48% duplicates, background differs by class. | Would teach the wrong things | D-03 (not in v1) |
| F9 | **Chickpea healthy vs wilt overlap** | In the t-SNE map, "1 (HR)" (0–10% wilted) images mix with wilted ones. All images come from one field in Türkiye. | Expect lower accuracy; no Indian chickpea data | D-01, S-04 |
| F10 | **Soybean lesion diseases overlap** | Rust, frog-eye and Septoria brown spot overlap in embedding space. Linear probe on soybean scores 0.76 macro-F1 (yellow mosaic separates well). | Hardest classes; need more and better data | S-04, D-05 |
| F11 | **Coverage gaps** | No Indian wheat images. No per-disease labels for Madhya Pradesh soybean (SoyNet). No urd or moong data. | Field collection is essential | D-08, S-04 |

## Charts

| Chart | What it shows |
|---|---|
| [01_class_balance](figures/01_class_balance.png) | Usable images per class, coloured by source dataset |
| [02_image_size_shape](figures/02_image_size_shape.png) | Image sizes and aspect ratios per dataset (the strip shortcut) |
| [03_background](figures/03_background.png) | Background brightness and colour per dataset and label (background shortcuts) |
| [04_quality](figures/04_quality.png) | Sharpness and brightness per dataset |
| [05_tsne_wheat](figures/05_tsne_wheat.png), [soybean](figures/05_tsne_soybean.png), [chickpea](figures/05_tsne_chickpea.png), [pea](figures/05_tsne_pea.png) | Image embeddings coloured by class and by source |
| [shortcut_tests.csv](shortcut_tests.csv) | Results of the three shortcut tests |

Image grids per class (for visual review) are in `<data-root>/eda/grids/`. They are not committed because dataset licences restrict republishing images.

## Shortcut test results

| Test | Scope | Macro-F1 | Reading |
|---|---|---:|---|
| Class from metadata only | wheat | **0.851** | Shortcut: beats the pixel-based probe |
| Class from embedding (linear probe) | wheat | 0.821 | |
| Class from metadata only | soybean | 0.520 | Weak shortcut (majority share 0.41) |
| Class from embedding (linear probe) | soybean | 0.762 | |
| Source from embedding | WHT_HEALTHY | 1.000 | Sources fully separable |
| Source from embedding | WHT_YELLOW_RUST | 1.000 | Sources fully separable |
| Source from embedding | SOY_HEALTHY | 1.000 | Sources fully separable |

**Update after code review:** the conflict check first compared only taxonomy classes, so a held copy (for example Kaggle
*septoria*) of a photo kept as *leaf blight* was silently dropped as a plain duplicate. Comparing labels too found
**350** conflicting groups (1,010 images), including 149 spot-blotch photos that are also labelled septoria or tan spot,
and 8 SoyNet photos labelled both *diseased* and *healthy*.

## After cleaning (manifest `public_v2`)

| Class | Usable images | Sources |
|---|---:|---|
| WHT_YELLOW_RUST | 6,069 | YELLOW-RUST-19 5,173 · Kaggle 896 |
| WHT_HEALTHY | 1,188 | Kaggle 986 · YELLOW-RUST-19 202 |
| WHT_BROWN_RUST | 1,030 | Kaggle |
| WHT_POWDERY_MILDEW | 815 | Kaggle |
| WHT_SPOT_BLOTCH | 494 | Kaggle |
| WHT_BLACK_RUST | 292 | Kaggle |
| SOY_RUST | 845 | MH-SoyaHealthVision |
| SOY_YMV | 699 | MH-SoyaHealthVision |
| SOY_HEALTHY | 320 | MH-SoyaHealthVision 204 · SoyNet 116 |
| SOY_FROGEYE | 168 | MH-SoyaHealthVision |
| PUL_CHICKPEA_WILT | 3,378 | FUSARIUM-22 |
| PUL_HEALTHY (chickpea) | 959 | FUSARIUM-22 |
| **Total** | **16,257** | |

A further 7,295 images are held for decisions (pea, Septoria, tan spot, SoyNet relabelling). See the [v2 summary](../../data/manifests/summary_public_v2.md).
