# Contributing

## Branches
- `main` is always stable and protected.
- Work on short-lived branches: `feat/<scope>-<short-name>`, `fix/...`, `data/...`, `docs/...`
  (e.g., `feat/ml-baseline-mobilenet`).

## Commits
Use [Conventional Commits](https://www.conventionalcommits.org): `feat(ml): add temperature scaling`.

## Pull requests
- One logical change per PR, with a short description of what changed and how it was tested.
- Changes to `taxonomy/` or `advisory/records/` need review from the project agronomist.
- Never commit images, model binaries, datasets or secrets (see `.gitignore`).

## Code style
- Python: `ruff` + `black`, type hints on public functions, `pytest` for tests.
- Dart/Flutter: official Dart style, `dart format` + `flutter analyze`.
- Web: plain HTML/CSS/JS, no build step, until the page needs one.
