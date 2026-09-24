import { BackgroundShapes } from "./components/BackgroundShapes";
import { Dropzone } from "./components/Dropzone";
import { ErrorCard, ResultCard } from "./components/ResultCard";
import { usePrediction } from "./hooks/usePrediction";

export default function App() {
  const { status, previewUrl, result, error, selectFile, reset, analyze } = usePrediction();

  const handleSelect = (file: File) => {
    const rejection = selectFile(file);
    if (rejection) window.alert(rejection); // simple, accessible enough for a validation-only message
  };

  const busy = status === "loading";
  const hasPhoto = status !== "idle";

  return (
    <div className="min-h-screen text-ink dark:text-ink-dark font-body">
      <BackgroundShapes />

      <header className="py-5">
        <div className="mx-auto flex max-w-[720px] flex-wrap items-center justify-between gap-3 px-5">
          <a href="/" className="flex items-center gap-2.5 no-underline text-ink dark:text-ink-dark">
            <span className="text-2xl" aria-hidden>
              🌾
            </span>
            <span className="font-display text-xl font-semibold tracking-tight">
              KisanShield<span className="text-brand dark:text-brand-dark">-FL</span>
            </span>
          </a>
          <span className="rounded-full bg-amber-soft dark:bg-amber-darksoft px-2.5 py-1.5 text-xs font-medium text-amber dark:text-amber-dark">
            Research demo — not for field use
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-[720px] px-5">
        <section className="py-6">
          <h1 className="font-display text-[clamp(28px,5vw,40px)] font-semibold leading-tight tracking-tight">
            See what the model sees
          </h1>
          <p className="mt-3 max-w-[56ch] text-ink-soft dark:text-ink-darksoft">
            Upload a photo of a soybean, wheat or chickpea leaf. The model predicts the disease from a
            public-data baseline — see{" "}
            <a
              className="text-brand dark:text-brand-dark"
              href="../docs/eda/EDA_FINDINGS.md"
              target="_blank"
              rel="noopener noreferrer"
            >
              known limitations
            </a>
            . No treatment advice yet; that needs expert sign-off first.
          </p>
        </section>

        <section className="mb-5 rounded-xl2 border border-line dark:border-line-dark bg-card dark:bg-card-dark p-6 shadow-[0_1px_2px_rgba(28,35,24,.06),0_12px_32px_-8px_rgba(28,35,24,.18)]">
          <Dropzone previewUrl={previewUrl} onSelect={handleSelect} />

          <div className="mt-5 flex flex-wrap gap-2.5">
            <button
              type="button"
              onClick={analyze}
              disabled={!hasPhoto || busy}
              className="inline-flex items-center gap-2.5 rounded-full bg-brand dark:bg-brand-dark px-5 py-3 font-semibold text-brand-ink dark:text-brand-darkink
                shadow-sm transition-transform enabled:hover:-translate-y-px disabled:cursor-not-allowed disabled:opacity-45
                focus-visible:outline focus-visible:outline-[3px] focus-visible:outline-brand focus-visible:outline-offset-2"
            >
              {busy && (
                <span
                  className="h-4 w-4 animate-spin rounded-full border-2 border-brand-ink/35 border-t-brand-ink"
                  aria-hidden
                />
              )}
              {busy ? "Analyzing…" : "Analyze photo"}
            </button>
            {hasPhoto && (
              <button
                type="button"
                onClick={reset}
                className="rounded-full border border-line dark:border-line-dark px-5 py-3 text-ink-soft dark:text-ink-darksoft
                  hover:border-brand hover:text-brand dark:hover:border-brand-dark dark:hover:text-brand-dark"
              >
                Choose another
              </button>
            )}
          </div>

          <div className="mt-5" aria-live="polite">
            {status === "error" && error && <ErrorCard message={error} />}
            {status === "success" && result && <ResultCard result={result} />}
          </div>
        </section>

        <p className="mb-6 text-center text-sm text-muted dark:text-muted-dark">
          Images are sent to a demo server for prediction and are not stored. This page calls the same API the
          mobile app uses. See the{" "}
          <a
            className="text-muted dark:text-muted-dark underline decoration-line"
            href="https://github.com/Pranaw108/kisanshield-fl"
            target="_blank"
            rel="noopener noreferrer"
          >
            project on GitHub
          </a>
          .
        </p>
      </main>

      <footer className="border-t border-line dark:border-line-dark py-5">
        <p className="text-center text-sm text-muted dark:text-muted-dark">
          KisanShield-FL · federated learning crop disease research, Madhya Pradesh
        </p>
      </footer>
    </div>
  );
}
