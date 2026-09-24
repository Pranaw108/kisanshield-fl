# Build log

Engineering and architecture decisions for this project, one entry per decision. Data-labelling
decisions (which dataset, which class) live in [`data/review/DECISIONS.md`](../data/review/DECISIONS.md)
instead — this file is for how the pipeline itself is built.

## 2026-09-18 — Manifest pipeline order: rules → overrides → duplicates
`build_manifest.py` applies automatic rules, then expert overrides, then resolves duplicates —
never the other order. Resolving duplicates first would let a later expert override on one copy
leave its near-duplicate copies unreviewed and still in the training set.

## 2026-09-19 — Leader clustering, not union-find, for near-duplicates
`group_near_duplicates()` uses greedy leader clustering: the kept image claims every duplicate
within the pHash threshold of itself. Union-find would chain A~B~C into one group even when A and
C are unrelated, so the kept image would not represent the images it replaces.

## 2026-09-19 — Duplicate conflicts compare labels, not just taxonomy classes
A `hold` image (no class yet) and a `use` image can still be the same photo under two different
source labels. Comparing only `class_id` missed this and let the mismatch through as a plain
duplicate. `label_identity()` falls back to `dataset:source_label` when there is no class yet.

## 2026-09-19 — Hash cache is versioned
`HASH_VERSION` is embedded in every cache row. Bump it when `hash_image()` changes, so a cache
built by old code is never silently reused with new logic.

## 2026-09-20 — Thumbnail builder reads the manifest, not `datasets.yaml`
`build_thumbnails.py` gets each image's archive and path from the manifest row, not by re-running
the current archive rules. A manifest is a snapshot; the current config can move on after it was
generated. It also verifies every thumbnail exists on disk before reporting success, rather than
trusting its own counters.

## 2026-09-21 — Review forms are versioned and re-validated on import
Forms live under `review/<manifest version>/` and carry `manifest_version` in every row, so a form
built against an old manifest is rejected on import instead of silently applied to a new one.

## 2026-09-21 — An expert's "unsure" holds an image; only a named rejection excludes it
`unsure` moves an image to `hold`, not `exclude`. Not being able to judge a photo is different
from rejecting it, and a verdict must never silently delete data the expert didn't reject.

## 2026-09-25 — Web demo: React + TypeScript + Vite + Tailwind, not plain HTML/JS
User asked for a UI quality bar matching SVS EduTech (component architecture, typed, tested),
with permission to use React. Superseded the first version (plain HTML/CSS/JS). Vite instead of
Next.js: this page is a client-only API caller with no server-rendering need, so Next's App
Router would be unused weight — a right-sized choice, not a lesser one. Kept KisanShield's own
green/amber palette; SVS's blue branding belongs to a different product. Real checks run and
passing: `tsc -b`, `vite build`, `eslint`, 9 vitest tests (including one asserting the result
card never renders treatment-advice-shaped text, since S-12 doesn't exist yet).

Known issue, not fixed: `npm audit` flags 5 vulnerabilities, all in `vite`/`vitest`/`esbuild`
(dev-tooling only, never shipped). Fixing needs a breaking major-version bump — left as a
deliberate future upgrade, not forced blind.

## 2026-09-24 — Mobile: Flutter, not Kotlin native; add a web demo
User decision, supersedes the original data/datasets.yaml-era plan (native Android). Reasons:
Flutter reaches Android and iOS from one codebase, and a web demo (`web/`) lets the model be
shown to the PI/TL/reviewers without an app install. `android/` renamed to `mobile/`; nothing
had been built there yet, so the rename was free. v0 of both mobile and web call `backend`'s
`/predict` API rather than running on-device — gets a working demo fast. On-device TFLite
inference (the production target, so the app works offline) is unchanged in the roadmap and
follows once the model and mobile app structure are proven.
