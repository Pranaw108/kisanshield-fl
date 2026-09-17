# Taxonomy

`classes_v1.csv` is the **single source of truth** for disease class IDs. The ML pipeline, the advice records and the Android app all read these IDs.

## Rules
- Class IDs (e.g., `SOY_YMV`) never change once frozen. Changes create a new file version (`classes_v2.csv`).
- `in_model = true` means the model predicts the class from leaf photos.
- `in_model = false` means the disease appears in the advice library only, because it can't be diagnosed from a leaf photo (roots, grain).
- **Status: DRAFT.** The class list must be reviewed and signed off by the project agronomist before v1 is frozen.
