# Mobile App

Flutter (Dart). Android first (matches farmer phones in MP), iOS free later since Flutter targets both.

## v0 (current): server-side inference
The app takes a photo, uploads it to `backend`'s `/predict` endpoint, and shows the result. This
gets a real working app in front of people fast, while the on-device pipeline below is still
being built. It needs a network connection, which the production plan removes.

## Planned (production): offline-first, on-device
Matches the architecture in the root README (predict first, train later, in the background):

```
lib/
├── screens/     Capture, result, advice, history, settings
├── services/    ApiService (v0), InferenceService (TFLite, on-device), AdvisoryService
├── ml/          Preprocessing (parity with ml/preprocessing), LiteRT inference
├── camera/      Camera capture + live photo quality check
├── data/        Local DB (sqflite/drift), encrypted photo storage
├── fl/          Federated learning client, head-only local trainer
└── widgets/     Shared UI components
```

- **On-device model:** `tflite_flutter`, loading the int8 model from `ml/export/`.
- **Camera:** the `camera` package.
- **Local storage:** `sqflite` or `drift`; photos encrypted at rest.
- **State:** Riverpod (simple, testable, no boilerplate-heavy alternative needed).

## Getting started
```bash
flutter create --org com.kisanshield mobile   # once, when this folder is first built out
cd mobile && flutter pub get && flutter run
```

Set the backend URL in `lib/config.dart` (never hard-code secrets or production URLs in source).
