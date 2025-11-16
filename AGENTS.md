# Repository Guidelines

## Project Structure & Module Organization
- `backend/` holds the Django REST API plus vendored `inventree-part-import` tooling; settings live under `backend/config/`, service logic in `backend/api/`, and entry scripts like `backend/manage.py`.
- `frontend/` is a Vite + React app (`src/` for components, `styles.css`, `vite.config.ts`).
- `inventree-part-import/` and `inventree_part_import_config/` contain the upstream importer library and configuration samples. Keep these in sync with their upstream repos when updating.
- Tests should mirror this layout: Django tests under `backend/api/tests/`, frontend tests under `frontend/src/`, and importer unit tests alongside their modules.

## Build, Test, and Development Commands
- `docker compose up --build` — rebuilds both services and runs the stack locally.
- `cd backend && poetry run python manage.py test` (or `pytest`) — executes Django unit tests.
- `cd backend && python manage.py collectstatic --noinput` — rebuilds admin/DRF static assets (required after dependency updates and before Docker builds).
- `cd frontend && npm install && npm run dev` — starts the Vite dev server; `npm run test` runs frontend unit tests.
- `cd inventree-part-import && poetry run pytest` — validates the vendored importer logic before syncing changes.

## Coding Style & Naming Conventions
- Python: Black-compatible formatting, 4-space indents, type hints where possible. Service modules follow `snake_case` filenames (`mouser.py`, `inventree.py`).
- TypeScript/React: Prettier defaults (2-space indents), functional components, hooks for state/side effects. Component files use `PascalCase` (e.g., `BarcodeScanner.tsx`).
- Keep environment/config files ASCII; document new settings in `README.md` or `AGENTS.md`.

## Testing Guidelines
- Backend tests should cover API views, serializer validation, and importer orchestration (mock external APIs). Name test modules `test_<feature>.py`.
- Frontend tests (Vitest/React Testing Library) should assert UI state for search/import flows; place specs next to components as `<Component>.test.tsx`.
- Run full test suites before PRs; aim for meaningful coverage on new code paths.

## Commit & Pull Request Guidelines
- Follow the existing concise present-tense style (e.g., `Add CSRF token fetch`). Group related changes per commit; include config/vendor updates when syncing importer sources.
- PRs should summarize scope, list test commands executed, reference issues, and include screenshots/GIFs for UI changes. Highlight any migrations, new env vars, or manual steps.

## Security & Configuration Tips
- Secrets live in `.env`/Docker env files; never commit real API keys. When adding importer configs, mask sensitive values and point contributors to `inventree_part_import_config/config.yaml` for examples.
- The runtime importer config directory lives in `.importer_config/` (gitignored). The backend copies the templates from `inventree_part_import_config/` and injects provider credentials from env vars when `/api/importer/*` is called. Update the templates first, then delete `.importer_config/` locally if you need a fresh copy.
- New Django endpoints `/api/importer/preview/` and `/api/importer/import/` wrap the vendored `inventree-part-import` library. Always surface dry-run data through `preview` and use the importer pipeline for real imports; the legacy `/api/search/*` + `/api/import/` flow should be treated as fallback only.
- Document any new importer settings (e.g., `MOUSER_SCRAPING`, `DIGIKEY_LANGUAGE`, `IMPORTER_CONFIG_DIR`) in both `README.md` and here when you add them so the ops team knows how to configure deployments.
- `backend/staticfiles/` is not checked in; always run `python backend/manage.py collectstatic --noinput` locally before packaging/pushing images so WhiteNoise can serve assets in every environment.
