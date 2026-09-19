# Expert review

Some cleaning needs a plant pathologist: checking labels, and labelling photos that only say "diseased".
This folder holds the decisions. The images stay outside git.

| File | Purpose |
|---|---|
| `DECISIONS.md` | Log of every data decision, with evidence, owner and status |
| `image_overrides.csv` | Per-image decisions (exclude or relabel), applied automatically by `build_manifest.py` |

## Workflow

```bash
# 1. Build the review pack (HTML image sheets + blank CSV forms) in <data-root>/review/
python data/scripts/review_pack.py build --data-root E:/Datasets
```

2. The expert opens each HTML page in a browser and fills in the matching CSV (Excel works):

   | Form | Images | Task |
   |---|---:|---|
   | `label_audit.csv` | 1,200 | Is the label right? (50 per group; 100 for Kaggle black and brown rust) |
   | `soynet_relabel.csv` | 1,163 | Which disease is this Madhya Pradesh soybean photo? |

   - **verdict:** `correct`, `wrong`, `unsure`, `not_a_leaf` or `unusable`
   - **correct_class:** the right taxonomy class id, when known

3. Import the answers, then rebuild the manifest:

```bash
python data/scripts/review_pack.py import E:/Datasets/review/label_audit.csv --decided-by "Dr. Name"
python data/scripts/build_manifest.py --data-root E:/Datasets
```

The import writes approved rows into `image_overrides.csv`. Commit that file so decisions are versioned.

## Label error rate
The audit also measures label quality. If more than **5%** of a group's audited images are wrong, review that whole
group before training. Record the result in `DECISIONS.md`.
