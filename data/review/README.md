# Expert review

Some cleaning needs a plant pathologist: checking labels, and labelling photos that only say "diseased".
This folder holds the decisions. The images stay outside git.

| File | Purpose |
|---|---|
| `DECISIONS.md` | Log of every data decision, with evidence, owner and status |
| `image_overrides.csv` | Current per-image decisions, applied automatically by `build_manifest.py` |
| `review_history.csv` | Append-only record of every imported decision (who, when, what) |

## Workflow

```bash
# 1. Build the review pack into <data-root>/review/<manifest version>/
python data/scripts/review_pack.py build --data-root E:/Datasets
```

2. The expert opens each HTML page in a browser and fills in the matching CSV (Excel works):

   | Form | Images | Task |
   |---|---:|---|
   | `label_audit.csv` | 1,200 | Is the label right? (50 per group; 100 for Kaggle black and brown rust) |
   | `soynet_relabel.csv` | 1,163 | Which disease is this Madhya Pradesh soybean photo? |

   **Verdicts** (one per row):

   | verdict | correct_class | What happens |
   |---|---|---|
   | `correct` | empty | Nothing changes |
   | `wrong` | **required** | The image is used with that class instead |
   | `label` | **required** | For photos with no class yet (SoyNet) |
   | `wrong_unknown` | empty | Class is wrong, right one unknown → excluded |
   | `not_a_leaf` | empty | Not a crop leaf → excluded |
   | `unusable` | empty | Too blurry or dark to judge → excluded |
   | `unsure` | empty | Cannot decide → held out of training, not deleted |

   Every other combination is rejected on import, so a forgotten class can't silently delete an image.

3. Import the answers, then rebuild the manifest:

```bash
python data/scripts/review_pack.py import E:/Datasets/review/public_v2/label_audit.csv --decided-by "Dr. Name"
python data/scripts/build_manifest.py --data-root E:/Datasets
```

The import checks every row before writing anything: known image id, matching manifest version, a class that
exists for that crop, and a verdict/class combination from the table above. If any row fails, nothing is imported.
Approved rows go to `image_overrides.csv` (current state) and `review_history.csv` (append-only), both committed to git.

## Label error rate
The audit also measures label quality. If more than **5%** of a group's audited images are wrong, review that whole
group before training. Record the result in `DECISIONS.md`.

## Sampling
How many images each group gets is configured in `data/datasets.yaml` under `review:`, not in code.
