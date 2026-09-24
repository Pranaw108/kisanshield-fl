# Web

A browser demo of the prediction model: upload a leaf photo, see the predicted disease and
confidence. Built to prove the model works end-to-end and to let the team (PI, TL, reviewers)
try it without installing anything.

**Stack:** React + TypeScript + Vite + Tailwind CSS. Chosen over Next.js (the stack used on the
[SVS EduTech](../docs/BUILD_LOG.md) project, our UI/engineering quality bar) because this page is
a client-only API caller with no server-rendering need — Vite gives the same component-based,
typed, tested quality without App Router machinery this page doesn't use. The palette is
KisanShield's own deep green + warm paper (agri-tech), not SVS's blue branding — see
`tailwind.config.js`.

## Structure
```
src/
├── api/client.ts           fetch wrapper for POST /v1/predict (backend/app/routers/predict.py)
├── hooks/usePrediction.ts  upload -> analyze -> result state machine
├── components/             Dropzone, ConfidenceBar, ResultCard, BackgroundShapes
├── types.ts                mirrors backend/app/schemas.py — keep both in sync
└── App.tsx
```

## Run it
```bash
npm install
cp .env.example .env.local   # set VITE_API_BASE_URL if the backend isn't on localhost:8000
npm run dev
```

## Test, lint, build
```bash
npm test    # vitest — 9 tests: API client, ConfidenceBar, ResultCard (incl. "never shows advice")
npm run lint
npm run build
```

## Known issue
`npm audit` flags 5 vulnerabilities, all in `vite`/`vitest`/`esbuild` (dev-only build tooling,
never shipped to users). The advisory is a dev-server request-forgery risk that needs a malicious
site open in the same browser while `npm run dev` is running. Fixing it means a breaking major
version bump (`vite@8`, `vitest@5`) — do that as a deliberate, tested upgrade, not blind
`npm audit fix --force`.
