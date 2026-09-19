# Data

**Images are never committed to git.** Downloaded archives stay on local or private storage. This folder holds only configuration, scripts and small reports.

| Path | Purpose |
|---|---|
| `datasets.yaml` | Registry of every public dataset: URL, DOI, licence, citation, class mapping, quality rules, and the rules for reading each archive |
| `scripts/build_manifest.py` | Scans the downloaded archives and writes the image manifest, with duplicate and quality checks |
| `scripts/build_thumbnails.py` | Caches a small copy (384 px) of every usable image for EDA and review |
| `scripts/review_pack.py` | Builds image sheets and forms for the agronomist, and imports their answers |
| `scripts/tests/` | Tests for the data scripts |
| `review/` | Decision log and per-image overrides (see [review/README.md](review/README.md)) |
| `manifests/` | Summary reports. The full manifest CSVs live next to the data, not in git |

## Setup (once)

From the repository root:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r ml/requirements.txt   # includes data/requirements.txt
```

Set where the downloaded archives live, or pass `--data-root` to every command:

```bash
set KISANSHIELD_DATA_ROOT=E:/Datasets     # Windows cmd  (PowerShell: $env:KISANSHIELD_DATA_ROOT="E:/Datasets")
```

## Pipeline

```bash
# 1. Quick check (~3 min): applies the folder rules and counts images. No hashing.
python data/scripts/build_manifest.py --list-only

# 2. Manifest (~10 min first time, ~3 min after): hashes images, removes duplicates, applies decisions
python data/scripts/build_manifest.py

# 3. Thumbnail cache (~7 min first time; afterwards only new or changed images)
#    Reads image locations from the manifest. Add --prune to delete thumbnails the manifest no longer
#    selects (the EDA notebook uses public_v1, so prune only after you stop re-running it).
python data/scripts/build_thumbnails.py

# 4. EDA: open ml/notebooks/01_eda.ipynb with the "KisanShield (.venv)" kernel

# 5. Expert review pack, then import answers (see review/README.md)
python data/scripts/review_pack.py build
```

- **Archives stay zipped.** Images are read straight from the downloaded zips (including nested zips), so no extra disk space is needed.
- **Re-runs are fast.** Hashes are cached in `<data-root>/manifests/hash_cache.csv`. After editing `datasets.yaml`, results are reused for unchanged archive members (same path, CRC and size). Changing the hashing code? Bump `HASH_VERSION` in `build_manifest.py` to invalidate the cache.
- **Run one dataset:** `--only soynet`. Outputs get a `_partial` suffix.
- **Stricter or looser duplicate matching:** `--near-dup-threshold 4` is the default (0 = identical, 64 = everything matches).

### Outputs (in `<data-root>/`)

| File | Contents |
|---|---|
| `manifests/manifest_public_v2.csv` | One row per image: dataset, archive, path, source label, taxonomy `class_id`, severity, `status` (`use` / `hold` / `exclude`) with reason, SHA-256, perceptual hash, size, grayscale flag, sharpness, brightness |
| `manifests/duplicates_public_v2.csv` | Every duplicate group: members, the kept image, and whether it spans datasets, source splits or labels |
| `manifests/summary_public_v2.md` | Readable report, also copied to `data/manifests/` in the repo |
| `cache/thumbs_384/` | Thumbnails, named `<image_id>.jpg` |
| `review/` | Review pack: HTML sheets and CSV forms |

Manifest versions: `public_v1` was the first scan (used for EDA). `public_v2` applies the EDA and review decisions.

### What each status means

| Status | Meaning | Examples |
|---|---|---|
| `use` | Ready for training | Mapped to a taxonomy class, passed quality checks, not a duplicate |
| `hold` | Waiting on a decision | Class not in taxonomy yet (pea, Septoria), SoyNet photos awaiting expert labels |
| `exclude` | Never used | Augmented or resized copies, dropped classes, duplicates, conflicting labels, too small or blurry, expert-rejected |

### Duplicate checks
1. **Exact duplicates:** identical file bytes (SHA-256).
2. **Near duplicates:** a perceptual hash (pHash, a fingerprint of how the image looks) within the threshold. This catches resized, re-saved or burst copies of the same photo, including across datasets.
3. **One image is kept per group:** preferring expert-reviewed images, then `use` over `hold`, then the higher resolution. Every removed image is within the threshold of the kept one (no chaining).
4. **Duplicates with conflicting labels** are all excluded, because neither label can be trusted (decision D-06). Labels are compared by class, or by source label for held images.
5. **Expert decisions win:** an expert label on one copy applies to the group, and copies of an expert-rejected image are excluded too.

**Order of steps:** automatic rules (archive rules, quality) → expert overrides → duplicate resolution. Duplicates are therefore always resolved on the final, reviewed state.

`is_grayscale` is a heuristic flag (near-identical colour channels), so read it as *likely* grayscale.

## Rules
- Downloaded archives are read-only. Never edit files inside them. Fix labels through `datasets.yaml` or `review/image_overrides.csv`.
- Every decision is logged in `review/DECISIONS.md`.
- Split by **source group** (farm, district, dataset), not by random image, so near-identical photos never land in both training and test data.
- Field data requires recorded consent. No faces, names or exact GPS.
