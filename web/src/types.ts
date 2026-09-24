// Mirrors backend/app/schemas.py — keep both in sync when the API contract changes.

export interface Prediction {
  class_id: string;
  name_en: string;
  name_hi: string;
  crop: string;
  confidence: number;
}

export type PredictStatus = "ok" | "not_sure";

export interface PredictResponse {
  status: PredictStatus;
  top: Prediction | null;
  alternatives: Prediction[];
  message: string | null;
}
