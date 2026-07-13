# Changelog

## Unreleased — full-stack Mini App production candidate

This section documents the current `feat-fullstack-mini-app` working tree. The
changes are not a production release until they are committed, reviewed,
merged, tagged, and deployed through the checklist in `deploy/README.md`.

### Telegram bot and reminders

- Preserved the existing aiogram bot and APScheduler reminder surface while
  adding the Mini App alongside it.
- Kept bot and scheduler in one production process so in-memory snooze jobs
  remain available to callback handlers.
- Added stable public reminder event IDs and shared idempotent Taken/Skipped
  resolution for both Telegram callbacks and the Mini App.
- Restored pending snoozes on scheduler startup and reconciled schedule changes
  with `ReminderScheduler.reload_jobs()`.

### Backend and persistence

- Added the FastAPI application with Telegram `initData` authentication,
  signed bearer tokens, CORS, health, and database readiness endpoints.
- Added local-first medicine synchronization with client UUIDs, timestamps,
  soft-delete tombstones, and last-write-wins conflict handling.
- Added server-authoritative settings, today's dashboard, adherence, history,
  and reminder-action endpoints under `/api/v1`.
- Extended the additive SQLite compatibility migration for existing bot
  databases; no destructive migration or Alembic dependency was introduced.
- Added production startup validation: non-development environments require a
  bot token, a strong JWT secret, an HTTPS Mini App URL, and restricted HTTPS
  CORS origins.

### Feedback and bug reports

- Added localized in-app rating and bug-report forms under Settings.
- Added authenticated multipart `POST /api/v1/feedback` submissions persisted
  in the `feedback` table.
- Relayed ratings to Telegram forum topic 3 and bug reports to topic 5 in the
  configured feedback chat. Telegram relay failures do not discard persisted
  submissions.
- Added optional JPEG, PNG, or WebP bug screenshots with an 8 MB limit and
  storage under the persistent `/app/data` volume.
- Added rating validation, required bug descriptions, screenshot previews,
  accessible controls, loading/error feedback, haptics, and RU/UK/EN copy.
- Removed browser/device diagnostic collection from the frontend; reports send
  only the user's rating/comment/description and optional screenshot.

### Mini App frontend

- Added the React 18, TypeScript, Vite, React Router, React Query, React Hook
  Form, and Zod application in `frontend/`.
- Added dashboard, medicine list/create/detail/edit, history, settings,
  feedback, and bug-report routes with the MedAlarm design system.
- Added local-first medicine storage and synchronization while keeping real
  adherence/history tied to server reminder dispatches.
- Added dashboard Taken/Skipped actions for unresolved dispatched doses.
- Added history period/status filtering, grouping, summaries, timezone-aware
  formatting, form-draft persistence, optional speech input, haptics, and
  Russian/Ukrainian/English localization.
- Restricted demo fixtures to Vite development builds. Production clears stale
  demo state and refuses to enable it.
- Polished feedback typography: larger labels/helper copy, lighter and smaller
  placeholders, concise punctuation, and no diagnostics notice.
- Kept the app viewport stable when the mobile keyboard opens so fixed
  navigation and floating actions remain behind the keyboard instead of
  jumping upward over form fields, including a measured viewport fallback for
  Telegram Android WebViews that ignore the standard keyboard-overlay APIs.
- Added development-only URLs for reviewing the full-screen loading, retry,
  and open-in-Telegram states without manufacturing authentication failures.

### Deployment and operations

- Added a non-root Python 3.12 Docker image and the `app.runtime` supervisor for
  API plus combined bot/scheduler startup.
- Added the single-replica Compose stack with persistent SQLite storage,
  bounded JSON logs, health checks, and an optional pinned Cloudflare Tunnel
  service.
- Added GitHub Actions for backend tests, image/Compose validation, frontend
  logic tests, production build validation, and GitHub Pages deployment.
- Added tagged VPS release, SQLite backup, restore, rollback, and operational
  verification scripts under `deploy/`.

### Verification completed locally

- Backend suite: 49 tests passed.
- Frontend plain-TypeScript logic suite passed.
- Production TypeScript/Vite build passed.
- Documentation and changed-file whitespace checks passed.
- Rendered browser QA is still required because the in-app browser was not
  available during the final feedback-form polish.
