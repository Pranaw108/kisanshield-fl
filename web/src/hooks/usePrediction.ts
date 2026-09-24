import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, predict } from "../api/client";
import type { PredictResponse } from "../types";

export const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const MAX_BYTES = 10 * 1024 * 1024;

type Status = "idle" | "ready" | "loading" | "success" | "error";

interface State {
  status: Status;
  file: File | null;
  previewUrl: string | null;
  result: PredictResponse | null;
  error: string | null;
}

const initialState: State = { status: "idle", file: null, previewUrl: null, result: null, error: null };

/** Owns the upload -> analyze -> result lifecycle so components stay presentational. */
export function usePrediction() {
  const [state, setState] = useState<State>(initialState);
  const abortRef = useRef<AbortController | null>(null);

  // Revoke the object URL whenever it changes or the component unmounts, so previews
  // don't leak memory across repeated uploads.
  useEffect(() => {
    const url = state.previewUrl;
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [state.previewUrl]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const selectFile = useCallback((file: File): string | null => {
    if (!ACCEPTED_TYPES.includes(file.type)) return "Please choose a JPEG, PNG or WebP photo.";
    if (file.size > MAX_BYTES) return "That photo is too large (max 10 MB).";

    setState((prev) => {
      if (prev.previewUrl) URL.revokeObjectURL(prev.previewUrl);
      return { status: "ready", file, previewUrl: URL.createObjectURL(file), result: null, error: null };
    });
    return null;
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState((prev) => {
      if (prev.previewUrl) URL.revokeObjectURL(prev.previewUrl);
      return initialState;
    });
  }, []);

  const analyze = useCallback(async () => {
    const file = state.file;
    if (!file) return;

    const controller = new AbortController();
    abortRef.current = controller;
    setState((prev) => ({ ...prev, status: "loading", error: null }));

    try {
      const result = await predict(file, controller.signal);
      if (controller.signal.aborted) return;
      setState((prev) => ({ ...prev, status: "success", result }));
    } catch (err) {
      if (controller.signal.aborted) return;
      const message = err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
      setState((prev) => ({ ...prev, status: "error", error: message }));
    }
  }, [state.file]);

  return { ...state, selectFile, reset, analyze };
}
