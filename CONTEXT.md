# MedAlarm Repository Context

Last verified from the working tree: **2026-07-16**.

This is the current-state handoff for contributors and coding agents. Read it
with `AGENTS.md`, which contains the binding repository rules. Do not treat
`PLAN.md` as proof of what is implemented; prefer current source and tests.

The complete production-candidate change inventory is in `CHANGELOG.md`; the
remaining release and infrastructure work is tracked in `deploy/README.md`.

## Repository status

- Current branch: `feat-fullstack-mini-app`.
- `HEAD`: `28f4760` (`chore: fix backend deps for Docker, add CI, JWT fail-fast, refresh docs`).
- Branch base visible locally: `main`/`origin/main` at `c124aa7`.
- The working tree is intentionally **not clean**: this snapshot has 45
  tracked changes and 29 untracked paths spanning backend, frontend,
  deployment, CI, and tests. Preserve them; do not reset or assume every
  current feature is committed.
- If Windows ownership blocks Git, use a one-shot command such as
  `git -c safe.directory=C:/Users/Admin/Documents/MedAlarm status`.

## Product boundary

MedAlarm is a Russian-first Telegram medicine-reminder bot plus a Telegram
Mini App. It records schedules and responses supplied by the user. It must not
give medical advice, select dosages, or recommend treatment changes.

The system has three surfaces: an aiogram bot, an APScheduler reminder worker,
and a React/Vite Mini App backed by FastAPI.

## Runtime topology

`Dockerfile` runs `python -m app.runtime`. The supervisor starts:

- `uvicorn app.api.main:app` for the API on port 8000;
- `python main.py` for the combined bot and scheduler.

The bot and scheduler remain together because scheduled snoozes are held in
the in-memory scheduler. Production is limited to one backend replica while it
uses SQLite and Telegram long polling. Compose persists `/app/data` in the
`medalarm_data` volume and optionally starts the pinned `cloudflared` service
through the `production` profile. `/ready` checks database readiness; `/health`
checks the API process.

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
  failures.
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

- `GET /catalog/status`
- `GET /catalog/medicines?q=...`
- `POST /auth/telegram`
- `GET /sync/bootstrap`
- `PUT /sync/medicines/{client_medicine_id}`
- `POST /sync/batch`
- `GET` and `PATCH /settings/me`
- `GET /dashboard/today`
- `GET /dashboard/adherence`
- `GET /history`
- `POST /reminder-events/{event_id}/actions`
- `POST /feedback` (rating or bug report, optional bug screenshot)

Authentication validates Telegram `initData` and issues a signed bearer token.
`JWT_SECRET` must be a real secret outside `APP_ENV=dev`; startup fails fast
otherwise. Never copy `.env` values into documentation or commits.

Medicine synchronization is local-first and last-write-wins by `updated_at`.
The server replaces the synced schedule collection and catalogue snapshot when
a newer medicine payload wins. Real history and adherence remain
server-authoritative.

`python -m app.catalog_update` resolves the latest hosted CSV through the
`data.gov.ua` CKAN API, decodes its Windows-1251 semicolon format, validates it,
and atomically replaces the local catalogue. Compose sets
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

The dashboard exposes Taken/Skipped buttons when a server dose has an
unresolved dispatch `event_id`. Real actionable doses use the API; local/demo
fallback actions are recorded idempotently in isolated local storage. History
can filter by period/status, group by day or medicine, and show a summary.
Medicine form drafts are autosaved per create/edit context. New medicines can
be entered manually or selected from the MOH catalogue. A catalogue selection
prefills only read-only product identity/reference fields; intake amount,
units, times, and schedule remain user-entered. Official instruction links are
shown as attributed external references and must never be converted into
personalized dosage or treatment advice.

Settings includes synchronized Small/Regular/Large typography presets that
apply a font scale across the Mini App; the local preview preserves the same
preference in localStorage. Settings also links to rating and bug-report forms.
Authenticated submissions are
stored in the backend and relayed best-effort to the configured Telegram forum
chat (rating topic 3, bug topic 5). Bug reports accept an optional JPEG, PNG,
or WebP screenshot up to 8 MB. The frontend does not attach browser/device diagnostics.

Keep the source-of-truth split explicit:

- Medicines: local-first, synchronized by client UUID and timestamp.
- Real history/adherence: server-authoritative and tied to dispatch events.
- Demo/fallback history: isolated local data, never sent as a real dispatch
  response.

## Configuration, tests, and operations

Use `.env.example` only as a key inventory. Required production values include
`BOT_TOKEN`, a strong `JWT_SECRET`, `MINI_APP_URL`, `CORS_ALLOWED_ORIGINS`, and
`TUNNEL_TOKEN`. Compose points the database at `/app/data/medalarm.db` and
enables `CATALOG_AUTO_UPDATE`; local developers can refresh explicitly with
`python -m app.catalog_update`.

The backend CI workflow runs pytest, builds the Docker image, and validates the
production Compose configuration. The Pages workflow runs all frontend logic
tests before building. No linter or formatter is configured.

Verification commands:

```powershell
python -m pytest

cd frontend
npm run test:local
npm run build
```

Backend tests cover services, API/auth/schema behavior, models/migrations,
scheduling, reminder delivery, and Mini App keyboard integration. Frontend
tests are plain TypeScript/Node checks for local medicine sync, demo/preview
medicines, local intake history, daily completion, auth gating, Telegram
helpers, haptics, persistent enum state, and history analysis. There is no
browser/component-level automated frontend suite yet.

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
