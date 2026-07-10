# PocketMind Reference Snapshot

Snapshot of `C:\Users\Admin\Documents\PocketMind` for MedAlarm design and
engineering reference.

- Captured: 2026-07-06
- Branch: `stage`
- Commit: `ad9d25c` (`Start voice recording on a single tap with auto-stop on silence`)
- Working tree: clean at capture time
- Evidence: current CodeGraph index, active source, root agent/context docs,
  package scripts, Docker Compose, and GitHub Actions

This is a reference, not a requirement to turn MedAlarm into PocketMind.
Re-check PocketMind before relying on details that may have changed.

## Product Shape

PocketMind is a Telegram task-management product with three cooperating runtime
surfaces:

1. A React/Vite Telegram Mini App that owns the interactive task experience.
2. A FastAPI service for Telegram authentication, cross-device synchronization,
   voice transcription, and reminder-oriented persistence.
3. An aiogram bot plus APScheduler worker for reminder delivery and snoozing.

The frontend is a static GitHub Pages application. The backend, bot, and
scheduler share a database and run as separate supervised processes inside one
backend container. Cloudflare Tunnel is the only public backend ingress.

## Repository And Runtime Map

```text
frontend/
  src/main.tsx                 Telegram WebApp bootstrap and React entry
  src/App.tsx                  auth/load gates and route tree
  src/components/Layout.tsx    app shell, header, bottom nav, floating actions
  src/components/TaskForm.tsx  adaptive task form, validation, drafts, voice
  src/pages/                   dashboard, task CRUD, settings, feedback
  src/features/tasks/          local model, repository, sync/cache, selectors
  src/features/settings/       local-only settings
  src/api/                     auth, sync, voice, bearer-token client
  tests/                       compiled TypeScript regression entrypoints

backend/
  app/main.py                  FastAPI app, CORS, health, active API router
  app/api/v1/                  Telegram auth, sync, voice, feedback
  app/services/                sync, reminders, cleanup, task actions
  app/models/                  user, task, reminder log, feedback
  app/bot/main.py              aiogram long polling
  app/bot/handlers/            start/help and reminder callbacks
  app/scheduler/worker.py      interval worker and immediate startup cycle
  alembic/                     production schema migrations
  tests/                       API, sync, cleanup, and reminder tests
```

Primary frontend routes:

- `/`: scheduled dashboard with Today, Tomorrow, Soon, and Overdue views.
- `/tasks`: filtered task inventory.
- `/tasks/new`: create flow with draft persistence.
- `/tasks/:taskId`: task detail reached from the app or bot deep link.
- `/tasks/:taskId/edit`: edit flow.
- `/settings`: local app and reminder defaults.
- `/settings/feedback` and `/settings/bug-report`: feedback surfaces.

Active API surface:

- `POST /api/v1/auth/telegram`
- `GET /api/v1/sync/bootstrap`
- `GET /api/v1/sync/changes?since=...`
- `PUT /api/v1/sync/tasks/{client_task_id}`
- `DELETE /api/v1/sync/tasks/{client_task_id}`
- `POST /api/v1/sync/batch`
- Voice and feedback routes registered under `/api/v1`
- `GET /health`

The backend does not serve the SPA. Legacy backend task CRUD, settings APIs,
internal reminder cron routes, and the former Vercel shape are intentionally
absent.

## End-To-End Workflows

### Startup And Authentication

1. The frontend initializes Telegram WebApp behavior and renders `App`.
2. `useTelegramAuth` reads Telegram `initData`, including URL launch-data
   fallbacks, and exchanges it at `/auth/telegram`.
3. The JWT stays in the API client's in-memory auth state.
4. A dedicated local-preview Vite mode supplies a stub user and skips Telegram
   and backend auth for UI work.
5. The app blocks its route tree behind auth and initial task bootstrap, with
   localized loading, retry, and open-in-Telegram states.

### Local-First Task Mutation

1. Create/edit/complete/cancel/delete operations update browser state first.
2. Full task records are stored under `pocketmind.tasks.v2`.
3. A stable string UUID is both `LocalTask.id` and backend `client_task_id`.
4. Deletion is a tombstone (`deleted_at`) rather than immediate local removal.
5. The repository pushes reminder-relevant task fields to sync endpoints.
6. If the backend is unavailable, the local edit remains usable.

Task types are `quick`, `deadline`, `no_deadline`, `recurring`, and `waiting`.
Quick tasks derive a near-term reminder from settings. Deadline/waiting tasks
support none, once, daily, or interval modes. Recurring completion advances the
next occurrence instead of finalizing the record.

### Synchronization

1. Startup bootstrap retrieves server records and server time.
2. Incremental changes can be requested with a `since` timestamp.
3. Local and remote records meet on `(user_id, client_task_id)`.
4. Newer `updated_at` wins; datetime comparisons are normalized to UTC.
5. Remote bot/scheduler changes merge only when newer.
6. Soft-delete tombstones cross the sync boundary.

This is intentionally simple last-write-wins synchronization. It is not a CRDT
and does not offer field-level conflict resolution.

### Settings Ownership

Settings live only in frontend `localStorage` under
`pocketmind.settings.v1`. The backend has no user-settings API or settings
columns.

Each synced task carries a snapshot of the backend-relevant settings:

- reminder timezone
- reminder language
- snooze minutes

Changing settings is an immediate local write, followed by task re-sync so
existing backend rows receive the new snapshot. Other defaults remain purely
client-side form behavior.

### Reminder Delivery

1. The scheduler worker runs an immediate cycle, then polls at the configured
   interval.
2. Due-task selection reads persisted `remind_at` and task snapshot fields.
3. The bot sends a localized reminder and records chat/message identifiers in
   `ReminderLog`.
4. Current Telegram actions are snooze and, when HTTPS configuration permits,
   open-task deep linking.
5. Snooze validates task ownership and the exact sent reminder log, updates the
   task, reconciles reminder logs, and deletes stale reminder messages.
6. Completion happens in the Mini App, not from the reminder keyboard.

Internal numeric task IDs remain in callback data. Mini App routes use the
string `client_task_id`; these identifiers are deliberately not interchangeable.

## UI And Interaction Model

PocketMind uses a compact mobile app shell designed around Telegram widths:

- fixed visual hierarchy: logo and localized page title in the header
- icon-only three-destination bottom navigation
- floating create/draft action and contextual floating back action
- green/emerald active states, white rounded cards, soft shadows, and pills
- Lucide icons paired with accessible labels and titles
- haptic feedback for selection, navigation, success, and warnings
- EN/RU/UK localization with an always-available header language cycle

The dashboard is an agenda rather than a generic card grid. It persists its
selected period, groups multi-day views by localized day, shows time chips, and
has a compact empty state. Task-list filters and views are also persisted.

Forms use React Hook Form plus Zod, localized validation keys, task-type-aware
fields, settings-derived defaults, draft persistence, an auto-sizing
description, and voice input for title/description. A same-day deadline is
forced into a one-time reminder mode to keep the UI and timing semantics
coherent.

Deep-link navigation is handled explicitly: if a Telegram-opened task is the
first browser history entry, Back resets task-list filters to reveal that task
and routes to the list instead of calling a useless `navigate(-1)`.

The UI has dedicated loading, retry, auth failure, Telegram gate, empty, toast,
and form-submission states. Most domain logic has focused TypeScript regression
tests, but CodeGraph reports limited direct component coverage for the main
pages and layout.

## Build, Deployment, And Release Workflow

Frontend:

- React 18, TypeScript, Vite, React Router, TanStack Query
- React Hook Form and Zod
- Tailwind plus project CSS and Lucide icons
- `npm.cmd --prefix frontend run test:local`
- `npm.cmd --prefix frontend run build`
- GitHub Pages deploys `frontend/dist` from `main`
- Pages base path is `/PocketMind/`

Backend:

- FastAPI, async SQLAlchemy, Alembic, aiogram, APScheduler
- `python -m unittest backend.tests.test_sync_api backend.tests.test_cleanup_surface -v`
- Docker image runs migrations, API, bot, and scheduler under supervision
- SQLite persists in the `pocketmind_data` volume
- Cloudflare Tunnel points to `http://backend:8000`; no host port is exposed

Release flow:

1. Day-to-day changes go to `stage`.
2. Local preview is a readiness gate for UI work.
3. One reusable `stage -> main` PR carries integration work.
4. The user reviews and merges it.
5. Only merged `main` is production-ready and triggers Pages deployment.
6. Backend Python changes also pass the Skylos SAST/dead-code workflow.

## Patterns Worth Reusing In MedAlarm

### Strong Candidates

- A real Mini App shell for richer medication management while retaining the
  bot as the timely notification surface.
- Telegram auth gating with a backend-issued short-lived token.
- Separate API, bot, and scheduler processes sharing one data model.
- Stable client-facing IDs for deep links instead of exposing database IDs.
- Explicit reminder dispatch logs so callbacks are valid only for messages
  actually sent to that user.
- Reminder message cleanup after a terminal or snooze action.
- Local-preview mode for rapid UI work without Telegram credentials.
- Localized loading/error/empty states and narrow-width regression checks.
- A `stage -> main` release gate with preview before promotion.
- Alembic migrations instead of production `create_all`.

### Reuse Carefully

- Local-first medication data would raise higher correctness and multi-device
  consistency risks than local-first task notes. MedAlarm should not adopt
  last-write-wins blindly for medication schedules or adherence history.
- Per-record settings snapshots are excellent for deterministic reminders, but
  they make global settings changes an explicit re-sync/migration problem.
- One container supervising API, bot, and scheduler is operationally simple,
  but separate processes or services may be safer as load and reliability
  requirements grow.
- SQLite is appropriate at small scale; concurrent full-stack usage may justify
  PostgreSQL earlier than PocketMind's pet-project scope.

### Do Not Copy

- Do not remove MedAlarm's server ownership of medicine schedules merely to
  imitate PocketMind's frontend-first architecture.
- Do not use browser local storage as the authoritative adherence log.
- Do not mix internal numeric callback IDs with public route IDs without an
  explicit mapping contract.
- Do not trust stale architecture prose over live router registration, tests,
  and CodeGraph call paths.

## Current Drift And Risks

- PocketMind `AGENTS.md` and `CONTEXT.md` still mention done actions in reminder
  callbacks. Current `reminder_keyboard`, callback handler, and cleanup-surface
  test show snooze plus open-task only. Source and tests are authoritative.
- Main page/layout components have little direct component-test coverage.
- Last-write-wins synchronization depends heavily on trustworthy, normalized
  timestamps and can lose concurrent edits.
- Local-only settings do not naturally roam across devices.
- Static Pages and separately deployed API require correct CORS, base-path,
  HTTPS, and repository-variable configuration.
- SQLite is shared by API, bot, and scheduler processes; lock/contention and
  backup behavior deserve attention as usage grows.

## Reference Rule

When using this snapshot for MedAlarm:

1. Borrow product and engineering patterns, not PocketMind domain assumptions.
2. Re-query PocketMind CodeGraph before copying an implementation detail.
3. Prefer MedAlarm's safety and adherence invariants over architectural parity.
4. Record explicitly whether a borrowed behavior is local-only, synchronized,
   or server-authoritative.
