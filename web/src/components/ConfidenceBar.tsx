interface Props {
  confidence: number; // 0..1
  tone?: "brand" | "amber";
}

/** Animated confidence meter. Fills on mount via a CSS transition on width. */
export function ConfidenceBar({ confidence, tone = "brand" }: Props) {
  const pct = Math.round(confidence * 100);
  const fillClass = tone === "amber" ? "bg-amber dark:bg-amber-dark" : "bg-brand dark:bg-brand-dark";

  return (
    <div>
      <div className="h-2 rounded-full bg-ink/10 dark:bg-ink-dark/10 overflow-hidden">
        <div
          className={`h-full rounded-full transition-[width] duration-500 ease-out ${fillClass}`}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      <p className="mt-1.5 text-sm text-ink-soft dark:text-ink-darksoft">{pct}% confidence</p>
    </div>
  );
}
