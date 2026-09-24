import type { PredictResponse } from "../types";

// Override at build time: VITE_API_BASE_URL=https://api.example.com npm run build
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {}

export async function predict(file: File, signal?: AbortSignal): Promise<PredictResponse> {
  const body = new FormData();
  body.append("file", file);

  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}/v1/predict`, { method: "POST", body, signal });
  } catch {
    throw new ApiError("Could not reach the prediction server. Check your connection and try again.");
  }

  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new ApiError(detail?.detail ?? `Server error (${res.status}). Please try again.`);
  }
  return res.json() as Promise<PredictResponse>;
}
