# Roadmap

## Stage A · Foundations
- [ ] S-00 Project setup, partners and ethics

## Stage B · Data
- [x] S-01 Data assessment (registry, manifest, EDA)
- [ ] S-02 Disease scope and label taxonomy (v1 draft in use; several decisions still provisional
      pending agronomist sign-off — see `data/review/DECISIONS.md`; pea/urd/moong not covered)
- [x] S-03 Public dataset acquisition and mapping
- [ ] S-04 Field data collection and farmer survey (kharif + rabi) — biggest open gap, see EDA F1
- [ ] S-05 Annotation and quality control (automatic cleaning done; expert audit pack ready, awaiting agronomist)
- [x] S-06 Preprocessing, augmentation and splits (`data/scripts/build_splits.py`; public data only)

## Stage C · Model
- [x] S-07 Centralised baseline model — first pass done, real numbers in `ml/training/RESULTS.md`
      (test macro-F1 0.78; per-source breakdown confirms the EDA F1 shortcut risk on real
      predictions, e.g. the minority source for WHT_YELLOW_RUST scores 95.6% vs 98.6%).
      **Not yet done:** hyperparameter tuning, D-12 (tile wheat strips instead of letterbox),
      Grad-CAM sanity check, confidence calibration.
- [ ] S-08 Mobile model export and on-device benchmark — v0 backend serves the Keras model
      directly (`backend/`); TFLite export and on-device benchmarking not started

## Stage D · Federated learning
- [ ] S-09 Federated learning simulation
- [ ] S-10 Privacy and security layer
- [ ] S-11 Backend and FL server — v0 prediction API only (`backend/`), not the FL/device-registry
      backend this item describes

## Stage E · Advisory and app
- [ ] S-12 Advisory knowledge base — blocks showing any treatment advice in the app or web demo
- [ ] S-13 Mobile app — v0 skeleton built (`mobile/`, Flutter, calls the backend API, camera/gallery
      capture, result screen); on-device inference, FL client, offline storage not started
- [ ] S-14 System integration and testing

## Stage F · Prove it
- [ ] S-15 Field pilot and evaluation
- [ ] S-16 Release, documentation and publications
