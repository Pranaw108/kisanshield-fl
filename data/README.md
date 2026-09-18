# Data

**Images are never committed to git.** Downloaded archives stay on local or private storage. This folder holds only configuration, scripts and small reports.

| Path | Purpose |
|---|---|
| `datasets.yaml` | Registry of every public dataset: URL, DOI, licence, citation, class mapping, and the rules for reading each archive |
| `scripts/build_manifest.py` | Scans the downloaded archives and writes the image manifest, with duplicate and quality checks |
| `scripts/tests/` | Tests for the manifest builder |
| `manifests/` | Summary reports (`summary_public_v1.md`). The full manifest CSVs live next to the data, not in git |

## Build the manifest

Setup (once):

```bash
pip install -r data/requirements.txt
```

Run from the repository root:

```bash
# 1. Quick check (~3 min): applies the folder rules and counts images. No hashing.
python data/scripts/build_manifest.py --data-root E:/Datasets --list-only

# 2. Full run: hashes every usable image, finds duplicates, writes the manifest.
python data/scripts/build_manifest.py --data-root E:/Datasets
```

Instead of passing `--data-root` every time, you can set the environment variable `KISANSHIELD_DATA_ROOT`.

- **Archives stay zipped.** Images are read straight from the downloaded zips (including nested zips), so no extra disk space is needed.
- **Re-runs are fast.** Hashes are cached in `<data-root>/manifests/hash_cache.csv`. After editing `datasets.yaml` (for example, a class mapping), only new or changed files are hashed.
- **Run one dataset:** `--only soynet`. Outputs get a `_partial` suffix.
- **Stricter or looser duplicate matching:** `--near-dup-threshold 4` is the default (0 = identical, 64 = everything matches).

### Outputs (in `<data-root>/manifests/`)

| File | Contents |
|---|---|
| `manifest_public_v1.csv` | One row per image: dataset, archive, path, source label, taxonomy `class_id`, severity, `status` (`use` / `hold` / `exclude`) with reason, SHA-256, perceptual hash, size, grayscale flag, sharpness, brightness |
| `duplicates_public_v1.csv` | Every duplicate group: members, the kept (canonical) image, and whether it spans datasets, source splits or labels |
| `summary_public_v1.md` | Readable report, also copied to `data/manifests/` in the repo |
| `hash_cache.csv` | Hash cache for fast re-runs |

### What each status means

| Status | Meaning | Examples |
|---|---|---|
| `use` | Ready for training | Mapped to a taxonomy class, not a duplicate |
| `hold` | Waiting on a decision | Class not in taxonomy yet (pea, Septoria), needs expert review, duplicates carrying conflicting labels |
| `exclude` | Never used | Augmented or resized copies, dropped classes (pests, grain diseases), exact or near duplicates, unreadable files |

### Duplicate checks
1. **Exact duplicates:** identical file bytes (SHA-256).
2. **Near duplicates:** a perceptual hash (pHash, a fingerprint of how the image looks) within the threshold. This catches resized or re-saved copies of the same photo, including copies across datasets.
3. **One image is kept per group:** preferring `use` over `hold`, then the higher resolution. The others are excluded with `duplicate_of` pointing to the kept image.
4. **Groups with conflicting classes** (the same photo labelled differently by two datasets) are held for expert review.

## Rules
- Downloaded archives are read-only. Never edit files inside them. Fix labels through `datasets.yaml`.
- Split by **source group** (farm, district, dataset), not by random image, so near-identical photos never land in both training and test data.
- Field data requires recorded consent. No faces, names or exact GPS.
