/// Mirrors backend/app/schemas.py — keep both in sync when the API contract changes.
class Prediction {
  final String classId;
  final String nameEn;
  final String nameHi;
  final String crop;
  final double confidence;

  Prediction({
    required this.classId,
    required this.nameEn,
    required this.nameHi,
    required this.crop,
    required this.confidence,
  });

  factory Prediction.fromJson(Map<String, dynamic> json) => Prediction(
        classId: json['class_id'] as String,
        nameEn: json['name_en'] as String,
        nameHi: json['name_hi'] as String,
        crop: json['crop'] as String,
        confidence: (json['confidence'] as num).toDouble(),
      );
}

class PredictResponse {
  final String status; // "ok" | "not_sure"
  final Prediction? top;
  final List<Prediction> alternatives;
  final String? message;

  PredictResponse({required this.status, this.top, required this.alternatives, this.message});

  factory PredictResponse.fromJson(Map<String, dynamic> json) => PredictResponse(
        status: json['status'] as String,
        top: json['top'] == null ? null : Prediction.fromJson(json['top'] as Map<String, dynamic>),
        alternatives: (json['alternatives'] as List)
            .map((e) => Prediction.fromJson(e as Map<String, dynamic>))
            .toList(),
        message: json['message'] as String?,
      );

  bool get isConfident => status == 'ok' && top != null;
}
