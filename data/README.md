# Data

**Images are never committed to git.** They live in a private, access-controlled bucket. This folder holds only scripts and manifests.

| Path | Purpose |
|---|---|
| `scripts/` | Download public datasets, map labels to taxonomy IDs, deduplicate (pHash), strip EXIF/GPS, build manifests |
| `manifests/` | Versioned `manifest_vX.csv` (one row per image: id, sha256, source, class_id, is_field, licence, split) and `dataset_card.md` |

## Rules
- `data/raw/<source>/` is read-only once downloaded. Keep each dataset's licence and citation next to it.
- Split by **farm and district**, not by random image, so the same farm never appears in both training and test data.
- Field data requires recorded consent. No faces, names or exact GPS.
