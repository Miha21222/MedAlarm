# MedAlarm Repository Context

Last verified from the working tree: **2026-07-18**.

This is the current-state handoff for contributors and coding agents. Read it
with `AGENTS.md`, which contains the binding repository rules. Do not treat
`PLAN.md` as proof of what is implemented; prefer current source and tests.

The complete production-candidate change inventory is in `CHANGELOG.md`; the
remaining release and infrastructure work is tracked in `deploy/README.md`.

## Repository status

- Current integration branch: `stage`; pull requests target `main`.
- The current history/dashboard/catalogue UX pass is developed and validated
  on `stage`. Inspect `git status` before editing and preserve any unrelated
  local runtime files.
- If Windows ownership blocks Git, use a one-shot command such as
  `git -c safe.directory=C:/Users/Admin/Documents/MedAlarm status`.

## Product boundary

MedAlarm is a Russian-first Telegram medicine-reminder bot plus a Telegram
Mini App. It records schedules and responses supplied by the user. It must not
give medical advice, select dosages, or recommend treatment changes.

The system has three surfaces: an aiogram bot, an APScheduler reminder worker,
and a React/Vite Mini App backed by FastAPI.

## Runtime topology

`Dockerfile` runs `python -m app.runtime`. The supervisor initializes the shared database once to prevent first-start
migration races, then starts:

- `uvicorn app.api.main:app` for the API on port 8000;
- `python main.py` for the combined bot and scheduler.

The bot and scheduler remain together because scheduled snoozes are held in
the in-memory scheduler. Production is limited to one backend replica while it
uses SQLite and Telegram long polling. Compose persists `/app/data` in the
`medalarm_data` volume and optionally starts the pinned `cloudflared` service
through the `production` profile. `/ready` checks database readiness; `/health`
checks the API process. Public `/api/v1/version` reports the version baked into
that backend image and disables caching so deployment checks stay current.

The frontend is deployed separately by `.github/workflows/github-pages.yml` on
pushes to `main`. The workflow tests and builds `frontend/`, requires an HTTPS
API URL ending in `/api/v1`, and publishes to GitHub Pages. Production deploy,
backup, restore, and rollback steps are in `deploy/README.md`.

Local entrypoints:

- `python main.py`: combined bot and scheduler.
- `uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000`: API.
- `python -m app.bot_main`: bot-only local development.
- `python -m app.scheduler`: scheduler-only local development.
- `npm run dev:local` in `frontend/`: UI preview with Telegram auth stubbed.
- `npm run dev` in `frontend/`: real Telegram/backend flow.

## Backend architecture

- `main.py` loads settings, initializes the database, creates the bot and
  dispatcher, starts `ReminderScheduler`, and begins long polling.
- `app/handlers/__init__.py` registers `inline_ui_router` and
  `callbacks_router`. `inline_ui.py` handles `/start` and `/app` and opens the
  Mini App; the legacy text menu and FSM flows have been removed. Reminder
  buttons live in `callbacks.py`.
- `app/services/` owns persistence and domain rules. Keep database queries out
  of handlers and API routes.
- `app/database/session.py::session_scope()` commits on success and rolls back
  failures. SQLite uses foreign-key enforcement, a 30-second busy timeout, and
  WAL mode so the API and bot/scheduler processes can safely share the file.
- `ensure_sqlite_compatibility()` is the additive, idempotent SQLite migration
  mechanism; the project does not use Alembic.
- Every schedule mutation must be followed by
  `ReminderScheduler.reload_jobs()` so the database and in-memory cron jobs do
  not diverge.

The central relationships are `User -> Medicine -> MedicineSchedule`, with
`IntakeLog` and `ReminderDispatchLog` attached to medicines. `Medicine` carries
`client_medicine_id`, `updated_at`, and `deleted_at` for synchronization.
Catalogue-linked medicines also carry a JSON metadata snapshot so reminders
remain stable if the external register changes. `CatalogMedicine` and
`CatalogMetadata` hold the locally imported, openly licensed Ukrainian MOH
State Register and its source freshness metadata.

Every real reminder response must resolve an existing
`ReminderDispatchLog.event_id`. `ReminderActionService` is shared by Telegram
callbacks and the Mini App. It accepts `taken` or `skipped`, verifies event
ownership, creates at most one intake, and returns the existing result on
repeated requests. Preserve this idempotency; never create server-authoritative
adherence history without a dispatch.

## FastAPI surface

`app/api/main.py` initializes the database during lifespan, configures CORS,
and mounts these routes under `/api/v1`:

- `GET /version` (public, no-cache backend runtime version)
- `GET /catalog/status`
- `GET /catalog/medicines?q=...`
- `POST /auth/telegram`
- `GET /sync/bootstrap`
- `PUT /sync/medicines/{client_medicine_id}`
- `POST /sync/batch`
- `PATCH /reminders/config` (local settings' reminder-only runtime projection)
- `GET /dashboard/today`
- `GET /dashboard/adherence`
- `GET /history`
- `POST /reminder-events/{event_id}/actions`
- `POST /feedback` (rating or bug report, optional bug screenshot)

Authentication validates Telegram `initData` and issues a signed bearer token.
`JWT_SECRET` must be a real secret outside `APP_ENV=dev`; startup fails fast
otherwise. Never copy `.env` values into documentation or commits.

Medicine synchronization is local-first and last-write-wins by `updated_at`.
When a newer medicine payload wins, the server reconciles schedule slots in
place (preserving unchanged IDs and historical dispatch links) and replaces the
catalogue snapshot. Out-of-order client responses cannot overwrite newer local
edits. App settings are local-authoritative; language, timezone, snooze, and
repeat mode are retried as a server reminder projection, while UI-only text
size never crosses the network. Real history and adherence remain
server-authoritative.

`python -m app.catalog_update` resolves the latest hosted CSV through the
`data.gov.ua` CKAN API, decodes its Windows-1251 semicolon format, validates it,
deduplicates equivalent registered forms, and atomically replaces the local
catalogue. Search also deduplicates existing data, and visually similar but
legitimately distinct results expose a compact registration/manufacturer
identifier. Compose sets
`CATALOG_AUTO_UPDATE=true` to check source freshness on startup. Catalogue
search is public because its source data is public CC BY; medicine sync remains
authenticated. The register is regulatory product metadata, not live retail
SKU, price, or availability data.

## Frontend architecture and behavior

`frontend/` uses React 18, TypeScript, Vite, React Router, React Query, React
Hook Form, Zod, Lucide icons, and a hand-written `src/styles.css`. It does not
use Tailwind or a component framework.

Routes are dashboard, medicine list/create/detail/edit, history, and settings.
The main divisions are:

- `src/api/`: auth, sync, settings, dashboard, history, and reminder actions.
- `src/features/medicines/`: local-first medicines, React Query cache, form
  drafts, preview medicines, and local intake history.
- `src/features/demo/`: development-only demo state and fixtures. Production
  clears stale demo state and refuses to enable it. Demo actions use a separate
  storage key and must not alter real local history.
- `src/features/history/`: filtering, grouping, and summary calculations.
- `src/contexts/`, `src/hooks/`, `src/components/`, and `src/pages/`: shared
  state, Telegram integration, reusable UI, and route pages.

The dashboard plan is built from local medicines; the server response overlays
only dispatch status and cannot add or overwrite local medicine content. It
exposes Taken/Skipped buttons when a matching server dose has an unresolved
dispatch `event_id`. Real actionable doses use the API; local/demo fallback
actions are recorded idempotently in isolated local storage. A newly
created medicine includes only schedule slots at or after its creation minute
on that first local day; earlier slots begin on the next applicable day.
History can filter by status and by the response's current calendar day,
Monday-to-Sunday week, or calendar month, group by response day or medicine,
and show a summary. Medicine form drafts are autosaved per create/edit context. New
medicines can be entered manually or selected from the MOH catalogue, with the
same schedule, dashboard, sync, and history rules. A catalogue selection
prefills only read-only product identity/reference fields; intake amount,
units, times, and schedule remain user-entered. Search and selected-medicine
cards show compact identity/form/strength/dispensing information while
retaining source attribution; catalogue data must never be converted into
personalized dosage or treatment advice.

Settings lives in localStorage and includes Small/Regular/Large typography
presets that apply a font scale across the Mini App. Only reminder-relevant
language/timezone/snooze/repeat values are projected to the backend. Settings
also links to rating and bug-report forms. Its version panel compares the
frontend version embedded by Vite with the backend runtime version from the
public API and highlights mismatches; both derive from `frontend/package.json`
in their independently deployed artifacts.
Authenticated submissions are
stored in the backend and relayed best-effort to the configured Telegram forum
chat (rating topic 3, bug topic 5). Bug reports accept an optional JPEG, PNG,
or WebP screenshot up to 8 MB. The frontend does not attach browser/device diagnostics.

Keep the source-of-truth split explicit:

- Medicines: local-authoritative, synchronized by client UUID and timestamp
  for reminders and optional cross-device recovery.
- Settings: local-authoritative; only the reminder runtime projection syncs.
- Real history/adherence: server-authoritative and tied to dispatch events.
- Demo/fallback history: isolated local data, never sent as a real dispatch
  response.

## Configuration, tests, and operations

Use `.env.example` only as a key inventory. Required production values include
`BOT_TOKEN`, a strong `JWT_SECRET`, `MINI_APP_URL`, `CORS_ALLOWED_ORIGINS`, and
`TUNNEL_TOKEN`. Compose points the database at `/app/data/medalarm.db` and
enables `CATALOG_AUTO_UPDATE`; local developers can refresh explicitly with
`python -m app.catalog_update`.

Backend CI runs Ruff and pytest, builds the Docker image, and validates the
production Compose configuration. Frontend CI runs ESLint, logic tests, Vitest
component tests, a production build, and a Playwright Chromium smoke test.
Ruff and Prettier provide backend/frontend formatting commands.

Verification commands:

```powershell
ruff check app tests main.py
python -m pytest

cd frontend
npm run lint
npm run test:local
npm run test:component
npm run build
npm run test:browser
```

Backend tests cover services, HTTP API/auth/schema behavior, models/migrations,
scheduling, reminder delivery, and Mini App keyboard integration. Frontend
coverage combines plain TypeScript/Node logic checks, Vitest/Testing Library
component tests, and a Playwright browser smoke test.

## Handoff cautions

- This checkout contains a broad uncommitted feature pass. Inspect diffs before
  editing overlapping files and keep unrelated work intact.
- `README.md` has a legacy Russian section that appears mojibake-encoded in
  some read surfaces. Do not propagate that encoding into new docs.
- Mini App schedule forms remain daily-oriented even though the model supports
  weekday selections.
- `POCKETMIND_REFERENCE.md` is design background, not MedAlarm's source of
  truth.
- If code and this snapshot diverge, update this file from code, tests,
  workflows, and deployment configuration in the same change.
