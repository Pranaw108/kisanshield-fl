import type { PredictResponse } from "../types";
import { ConfidenceBar } from "./ConfidenceBar";

interface Props {
  result: PredictResponse;
}

export function ResultCard({ result }: Props) {
  if (result.status === "not_sure") {
    return (
      <div className="animate-rise rounded-xl2 border border-amber/35 bg-amber-soft dark:bg-amber-darksoft p-5" role="status">
        <p className="font-semibold text-amber dark:text-amber-dark">Not sure</p>
        <p className="mt-1">{result.message ?? "The model could not confidently name a disease."}</p>
      </div>
    );
  }

  const top = result.top!;
  return (
    <div className="animate-rise rounded-xl2 border border-brand/35 bg-brand/[0.07] dark:bg-brand-dark/10 p-5" role="status">
      <p className="text-xs uppercase tracking-wide text-muted dark:text-muted-dark">{top.crop}</p>
      <h3 className="font-display text-xl font-semibold">{top.name_en}</h3>
      <p className="text-sm text-ink-soft dark:text-ink-darksoft">{top.name_hi}</p>

      <div className="mt-3">
        <ConfidenceBar confidence={top.confidence} />
      </div>

      {result.alternatives.length > 0 && (
        <ul className="mt-3.5 flex flex-col gap-1.5">
          {result.alternatives.map((alt) => (
            <li key={alt.class_id} className="flex justify-between text-sm text-ink-soft dark:text-ink-darksoft">
              <span>{alt.name_en}</span>
              <span>{Math.round(alt.confidence * 100)}%</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function ErrorCard({ message }: { message: string }) {
  return (
    <div className="animate-rise rounded-xl2 border border-danger/35 bg-danger-soft dark:bg-danger-darksoft p-5" role="alert">
      <p className="font-semibold text-danger dark:text-danger-dark">Could not analyze that photo</p>
      <p className="mt-1">{message}</p>
    </div>
  );
}
