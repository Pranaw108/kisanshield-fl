/// Runtime configuration. Never hard-code a production URL or secret here.
///
/// Override at build/run time:
///   flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000
/// (10.0.2.2 is how the Android emulator reaches the host machine's localhost.)
class Config {
  static const apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  /// Below this confidence, the UI shows "not sure" instead of a disease name.
  /// Mirrors backend/app/config.py MIN_CONFIDENCE_FOR_RESULT — keep both in sync.
  static const minConfidence = 0.35;
}
