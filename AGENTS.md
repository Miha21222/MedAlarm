# AGENTS.md

## CodeGraph

This repository is indexed by CodeGraph (`.codegraph/` exists). Before using
grep, find, or direct source reads to understand or locate code:

1. Use `codegraph_explore` when the MCP tool is available.
2. Otherwise run `codegraph explore "<question or symbols>"`.
3. Treat CodeGraph output as the current read surface unless it reports stale
   files or disabled synchronization.
4. Fall back to `rg` or direct reads only for unindexed content such as docs,
   config, logs, lockfiles, or an exact literal CodeGraph did not surface.

For flow questions, name both endpoints in one query. Before editing code, query
the exact symbols or files and review their callers, dependencies, and tests.

## Project

MedAlarm is a Russian-language Telegram medicine-reminder bot, now extended
into a full-stack Telegram Mini App. The bot/scheduler surface is built with
aiogram 3, async SQLAlchemy 2.0, SQLite/aiosqlite, and APScheduler. The Mini
App adds a FastAPI backend (`app/api/`) and a React/Vite frontend
(`frontend/`). It only reminds users from data they entered. Never add
medical advice, dosage recommendations, or treatment changes.

## Architecture Map

### Current checkout snapshot (verified 2026-07-10)

- Active branch: `feat-fullstack-mini-app`; `HEAD` is `28f4760`, with the
  visible `main`/`origin/main` base at `c124aa7`.
- This is an intentionally dirty feature checkout. At this snapshot it has 45
  tracked changes and 29 untracked paths across backend, frontend, deployment,
  CI, and tests. Inspect overlapping diffs, preserve unrelated work, and never
  reset the tree merely to make it clean.
- Windows sandbox ownership can make Git report a dubious repository. Use a
  one-shot command such as
  `git -c safe.directory=C:/Users/Admin/Documents/MedAlarm status`; do not
  change global Git configuration for this checkout.
- `CONTEXT.md` is the shared dated handoff. This file remains the complete
  Codex/agent instruction surface and must stay aligned with current code.
- `CHANGELOG.md` records the full production-candidate scope;
  `deploy/README.md` contains the production-readiness checklist.
- `README.md` has a legacy Russian section that can appear as mojibake in some
  read surfaces. Do not reproduce the broken encoding.
- `POCKETMIND_REFERENCE.md` is design background, not a source of truth for
  MedAlarm behavior.

- `main.py`: load settings, initialize the database, create bot/dispatcher,
  start `ReminderScheduler`, and begin long polling. This is the combined
  bot+scheduler process Docker actually runs (via `app/runtime.py`).
- `app/bot.py`: construct the aiogram bot and dispatcher.
- `app/bot_main.py`: bot-only entrypoint (no scheduler), for split-process
  local dev; not used by Docker.
- `app/handlers/inline_ui.py`: `/start` and `/app` registration/welcome flow;
  it opens the Mini App and has no legacy text-menu or FSM flows.
- `app/handlers/callbacks.py`: live reminder actions for taken, snooze, and
  skip, delegating to `app/services/reminder_action_service.py` — the same
  service the Mini App's reminder-action endpoint uses.
- `app/handlers/__init__.py`: live router registration (only
  `inline_ui_router` and `callbacks_router`).
- `app/services/`: database-backed business logic. Keep queries here rather
  than in handlers or API routes. Includes `medicine_sync_service.py`
  (Mini App last-write-wins sync), `medicine_catalog_service.py` (CC BY
  Ukrainian MOH State Register import/search), and `reminder_action_service.py`
  (shared bot/Mini App reminder resolution).
- `app/database/models.py`: `User -> Medicine -> MedicineSchedule`, with
  intake and reminder-dispatch logs and cascade deletion. `Medicine` carries
  `client_medicine_id`/`updated_at`/`deleted_at` plus an optional catalogue
  snapshot for Mini App sync; `CatalogMedicine`/`CatalogMetadata` store the
  imported MOH catalogue. `ReminderDispatchLog` carries a public `event_id`
  used by both the bot
  callback and the Mini App action endpoint.
- `app/database/session.py`: async engine/session setup. Use `session_scope()`
  so successful operations commit and failures roll back.
- `app/database/migrations.py`: `ensure_sqlite_compatibility()`, an additive,
  idempotent, SQLite-only migration run on every `init_db()` (no Alembic).
- `app/scheduler/jobs.py`: APScheduler job creation, reminder delivery,
  dispatch logging, and one-off snoozes.
- `app/scheduler/setup.py`: module-level scheduler getter/setter used by
  handlers.
- `app/scheduler/__main__.py`: scheduler-only entrypoint for split-process
  local dev; not used by Docker.
- `app/api/`: FastAPI backend for the Mini App (`main.py` app + CORS,
  `routes.py` prefix `/api/v1` — public catalogue status/search, auth, sync,
  settings, dashboard, history, reminder actions, `auth.py` Telegram initData
  validation + bearer tokens,
  `schemas.py`, `dependencies.py`).
- `app/runtime.py`: Docker entrypoint supervising two subprocesses (the API
  and `main.py`'s combined bot+scheduler) with signal forwarding and
  fail-together shutdown.
- `frontend/`: React + TypeScript + Vite Mini App. `src/api/` (resource-split
  HTTP client), `src/features/medicines/` (local-first localStorage
  repository + React Query cache), `src/contexts/`, `src/hooks/`,
  `src/components/`, `src/pages/`. Uses its own hand-written `src/styles.css`
  design system, not Tailwind.
- Current frontend routes are dashboard, medicine list/create/detail/edit,
  history, settings, rating feedback, and bug reporting. Medicine creation
  supports manual entry or selection from the locally imported MOH catalogue;
  intake amount and schedule always remain user-entered. The dashboard exposes Taken/Skipped actions only for
  unresolved server dispatch events. `src/features/demo/` provides isolated
  preview state; demo actions use a separate history storage key and never
  alter real history. `src/features/history/` provides period/status filters,
  day/medicine grouping, and summaries. Medicine drafts are autosaved per form
  context.
- Demo mode is development-only: `main.tsx` configures it from
  `import.meta.env.DEV`, production clears any stale demo localStorage flag,
  and attempts to re-enable it are ignored.
- Feedback is persisted in the `feedback` table through `POST /api/v1/feedback`
  and relayed best-effort to Telegram. Ratings go to topic 3 and bug reports to
  topic 5 of the configured feedback forum chat. Bug screenshots accept only
  JPEG, PNG, or WebP up to 8 MB. Relay failures must not lose the database row.
  The frontend does not attach browser/device diagnostic metadata.
- `frontend/src/api/reminderActions.ts` sends real actionable doses to the
  server and supports idempotent local/demo fallback. Real adherence must stay
  tied to `ReminderDispatchLog.event_id`.
- `tests/`: pytest and pytest-asyncio tests using in-memory SQLite.
  `frontend/tests/`: plain-TypeScript tests (no framework) for pure-logic
  modules only.

Schedule changes must be followed by `ReminderScheduler.reload_jobs()` so the
in-memory cron jobs match the database. Reminder responses (bot or Mini App)
must remain tied to an existing dispatch record.

## Commands

```powershell
# Setup
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Import/refresh the Ukrainian MOH catalogue
python -m app.catalog_update

# Run locally; .env must contain BOT_TOKEN
python main.py

# Test
python -m pytest
python -m pytest tests/test_services.py
python -m pytest tests/test_services.py::test_history_filters_by_period

# Docker (bot + scheduler + API together via app/runtime.py)
docker compose up --build -d

# Frontend (Mini App)
cd frontend
npm install
npm run dev:local    # local preview, stubs Telegram auth
npm run build
npm run test:local
```

CI: `.github/workflows/backend-tests.yml` runs `pytest` on backend changes.
`.github/workflows/github-pages.yml` builds and deploys `frontend/` to GitHub
Pages on push to `main`. No linter or formatter is configured for either side.

Backend CI also builds the image and validates production Compose. Pages CI
runs `npm run test:local`, requires an HTTPS API URL ending in `/api/v1`, and
builds with the `/MedAlarm/` base path. Production uses one SQLite-backed
backend replica plus the optional pinned `cloudflared` service. Deployment,
backup, restore, and rollback instructions are in `deploy/README.md`.

`JWT_SECRET` (env var, see `app/config.py`) must be a real secret whenever
`APP_ENV` is not `dev` — `load_settings()` raises at startup otherwise rather
than silently running with the insecure default.

## Change Guidelines

- Preserve the Russian, beginner-friendly user interface. Mini App typography
  must respect the synchronized Small/Regular/Large text-size preference.
- Keep callback actions idempotent and avoid duplicate messages or side effects.
- Put persistence and domain rules in services, not handlers or API routes.
- Add or update focused tests for behavior changes (`tests/` for backend,
  `frontend/tests/` for pure-logic frontend modules).
- Never expose `.env` values or commit secrets.
- Mini App medicines are local-first + synced (last-write-wins by
  `updated_at`). Real Telegram/backend history is server-authoritative and
  tied to dispatch events. Demo/offline fallback history is isolated client
  data and must never be uploaded or represented as a real dispatch response.
- The Mini App schedule form remains daily-oriented even though the model can
  represent weekday selections.
- Frontend tests are plain TypeScript/Node logic tests; there is no automated
  browser or component suite. Coverage includes local medicine sync,
  preview/demo medicines, local intake history, daily completion, auth gating,
  Telegram helpers, haptics, persistent enum state, and history analysis.
