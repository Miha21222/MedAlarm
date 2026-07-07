# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

MedAlarm — a Telegram bot (Russian-language UI) that reminds users to take medicines on a schedule, now extended into a full-stack Telegram Mini App. Built with `aiogram 3`, `SQLite`/`aiosqlite`, `SQLAlchemy 2.0` (async), and `APScheduler` for the bot/scheduler surface, plus a `FastAPI` backend (`app/api/`) and a React/Vite frontend (`frontend/`) for the Mini App. MVP scope only: the app never gives medical advice, dosage suggestions, or treatment changes — it only reminds based on data the user entered.

## Commands

```bash
# Setup
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Run the bot locally (requires .env with BOT_TOKEN)
python main.py

# Run in Docker (bot + scheduler + API together via app/runtime.py)
docker compose up --build -d

# Backend tests
python -m pytest                              # full suite
python -m pytest tests/test_services.py        # one file
python -m pytest tests/test_services.py::test_history_filters_by_period  # single test

# Frontend (Mini App)
cd frontend
npm install
npm run dev          # real Telegram/backend flow
npm run dev:local    # local preview, stubs Telegram auth (Vite mode=preview)
npm run build
npm run test:local
```

CI: `.github/workflows/backend-tests.yml` runs `pytest` on changes to `app/**`/`tests/**`/`requirements.txt`. `.github/workflows/github-pages.yml` builds and deploys `frontend/` to GitHub Pages on push to `main`. There is no linter/formatter configured for either side — don't invent verification commands for tools this repo doesn't use.

Config is read from environment variables via `.env` (see `app/config.py`): `BOT_TOKEN`, `DATABASE_URL` (or `DB_PATH`, default `./data/medalarm.db`), `DEFAULT_TIMEZONE`, `LOG_LEVEL`, `APP_ENV`, plus the Mini App additions `JWT_SECRET`, `JWT_EXPIRE_MINUTES`, `MINI_APP_URL`, `CORS_ALLOWED_ORIGINS`. **`JWT_SECRET` must be a real secret whenever `APP_ENV` is not `dev`** — `load_settings()` raises at startup otherwise rather than silently running with the insecure default.

## Architecture

### Bot & scheduler (original surface, unchanged in shape)

**Entry point**: `main.py` loads settings, calls `init_db()` to create tables if missing (and run the additive SQLite migration, see below), builds the bot/dispatcher (`app/bot.py`), starts the `ReminderScheduler`, then runs `dp.start_polling`. `app/bot_main.py` is a slimmed alternative entrypoint (bot only, no scheduler) for split-process local dev; it is **not** used by Docker — see `app/runtime.py` below for why.

**Handlers — only one router chain is actually wired up.** `app/handlers/__init__.py` registers just two routers: `inline_ui_router` and `callbacks_router`. All live user-facing flows (`/start`, `/menu`, `/app`, adding/editing medicines, history, settings) are implemented directly in `app/handlers/inline_ui.py`, a single large module driving a menu-and-inline-keyboard UI plus FSM wizards (states in `app/states/`). `app/handlers/callbacks.py` handles the reminder action buttons (confirm / snooze / skip), delegating resolution to `app/services/reminder_action_service.py::ReminderActionService` — the same service the Mini App's `POST /reminder-events/{event_id}/actions` endpoint uses, so the bot and Mini App share one action-resolution implementation and one dispatch-log invariant (an intake can only be logged against an event that was actually dispatched).

**Scheduling**: `app/scheduler/jobs.py::ReminderScheduler` wraps an `AsyncIOScheduler` (UTC-based). `reload_jobs()` wipes and rebuilds all jobs from `ScheduleService.get_active_schedule_rows()` — call it whenever schedules change so cron jobs stay in sync with the DB. Each `MedicineSchedule` becomes either one daily `CronTrigger` (`days_of_week == "*"`) or one `CronTrigger` per weekday, evaluated in the user's own timezone. `schedule_snooze()` adds a one-off `DateTrigger` job instead of touching the DB schedule. `_send_reminder` re-fetches the schedule/medicine/user (guards against rows deleted since the job was scheduled), sends the message, then logs the dispatch via `IntakeService.log_dispatch` — this dispatch log is what `IntakeLog` responses (✅/⏰/⏭, and the Mini App's reminder-action endpoint) are later matched against, via the dispatch's `event_id`. `app/scheduler/__main__.py` is a standalone scheduler-only entrypoint for split-process local dev; also not used by Docker.

**Data model** (`app/database/models.py`): `User` → `Medicine` (cascade-deletes `schedules`, `intake_logs`, `reminder_dispatch_logs`) → `MedicineSchedule` → `ReminderDispatchLog`/`IntakeLog`. `MedicineSchedule` has a unique constraint on `(medicine_id, time, days_of_week)`. `Medicine` additionally carries `client_medicine_id`/`updated_at`/`deleted_at` for the Mini App's local-first sync (client-generated UUID, soft delete). `ReminderDispatchLog` carries a public `event_id` (UUID) plus `status`/`chat_id`/`message_id`/`resolved_at`, used by both the bot callback and the Mini App action endpoint. Intake status and "today due" logic live in `app/services/` (`schedule_service.py`, `intake_service.py`, `medicine_service.py`, `user_service.py`), which handlers, the scheduler, and the API all call into — keep DB queries in services, not handlers or routes.

**Sessions**: use `session_scope()` from `app/database/session.py` (async context manager, commits on success / rolls back on exception) rather than opening `SessionLocal()` directly. `app/database/migrations.py::ensure_sqlite_compatibility()` runs right after `create_all` on every `init_db()` call — an additive, idempotent, SQLite-only migration (no Alembic) that adds the Mini-App-era columns/indexes and backfills UUIDs for rows created before the Mini App existed. Safe to re-run on every startup; never drops or renames anything.

### Mini App backend (`app/api/`)

FastAPI app (`app/api/main.py`), single router in `app/api/routes.py` (prefix `/api/v1`): Telegram-initData auth (`POST /auth/telegram`, issuing a custom HMAC-signed bearer token — not a real JWT library, just JWT-shaped), medicine sync (`GET /sync/bootstrap`, `PUT /sync/medicines/{client_medicine_id}`, `POST /sync/batch`, handled by `app/services/medicine_sync_service.py::MedicineSyncService` — last-write-wins by `updated_at`), settings (`GET`/`PATCH /settings/me`), dashboard (`GET /dashboard/today`, `GET /dashboard/adherence`), history (`GET /history`), and reminder resolution (`POST /reminder-events/{event_id}/actions`, via `ReminderActionService`, idempotent). `app/runtime.py` is the actual Docker entrypoint (`CMD` in `Dockerfile`): it supervises two subprocesses, `uvicorn app.api.main:app` and `python main.py` (bot+scheduler combined) — bot and scheduler are kept in one process because snooze jobs live in the in-memory `AsyncIOScheduler` instance and aren't persisted, so splitting them (as `bot_main.py`/`scheduler/__main__.py` allow for local dev) isn't yet safe in production.

### Mini App frontend (`frontend/`)

React + TypeScript + Vite. Deliberately structured like the sibling PocketMind project's frontend (see `POCKETMIND_REFERENCE.md` for the full comparison this was based on), but keeping MedAlarm's own hand-written `src/styles.css` design system (navy/teal palette derived from the MedAlarm logo, real Manrope/Nunito Sans fonts) rather than adopting Tailwind: `src/api/` (resource-split HTTP client — `client.ts`, `auth.ts`, `sync.ts`, `dashboard.ts`, `history.ts`, `settings.ts`), `src/features/medicines/` (`localMedicines.ts` pure logic + localStorage I/O, `localMedicineRepository.ts` network-aware sync orchestration with a concurrency-safe re-read-before-merge, `cache.ts` React Query wiring), `src/contexts/` (`AppSettingsContext`, `ToastContext`), `src/hooks/` (`useTelegramAuth`, `usePersistentEnumState`), `src/components/` (`Layout` shell, `MedicineCard`, `OpenInTelegram` gate screen, etc.), `src/pages/` (one file per route). `npm run dev:local` (Vite `--mode preview`) stubs Telegram auth entirely for UI work without a bot token. Medicines are local-first + synced (localStorage, client-generated UUIDs, last-write-wins merge); history/adherence are always fetched live from the backend with no local cache — this split is deliberate, not an oversight (see `POCKETMIND_REFERENCE.md`'s caution against treating local storage as an authoritative adherence log).

**Known v1 gaps, not bugs**: the Mini App has no "mark taken/skipped" action of its own — that only works from the bot's reminder message today, because a dose can only be resolved once a `ReminderDispatchLog` exists for it, and the dashboard's "today" view doesn't yet expose the dispatch `event_id` needed to call the action endpoint from the Mini App. Schedules are daily-only in the Mini App's create/edit form even though the data model supports per-weekday lists.

**Tests** (`tests/`) use an in-memory SQLite DB per test via the `db_session` fixture in `conftest.py`. Async tests rely on `pytest-asyncio`. Frontend tests (`frontend/tests/`) use no framework — plain TypeScript compiled to CommonJS via `tsconfig.tests.json` and run with `node`, covering only pure-logic modules (`localMedicines`, `authGate`, `telegramWebApp`, `usePersistentEnumState`); there is no component/page-level frontend test coverage yet.
