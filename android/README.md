# Android App

Kotlin + Jetpack Compose. minSdk 26 (Android 8). Offline-first.

## Planned modules
```
ui/        Compose screens + ViewModels
camera/    CameraX capture + live photo quality check
ml/        Preprocessing (parity with Python), LiteRT inference, calibration
advisory/  Signed advice pack loader, severity -> actions, TTS/audio
data/      Room DB, encrypted photo storage, repositories
fl/        Flower client, head-only local trainer, feature cache
sync/      WorkManager jobs: model update, advice pack update, FL round
security/  Keystore, signature verification, certificate pinning, Play Integrity
core/      Config, logging (no personal data), i18n
```

The Android Studio project will be created here at the app build stage.
