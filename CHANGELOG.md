# Changelog

All notable changes to MedAlarm are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Changed

- Removed the legacy Telegram text/inline menu; `/start` and `/app` now expose
  only the Mini App entry point while reminder actions remain in chat.

### Fixed

- Medicine creation now restores the last-used manual or catalogue entry mode
  together with all autosaved manual draft values after navigating back.

## [1.1.0] - 2026-07-16

### Added

- Added a CC BY catalogue importer for the Ukrainian Ministry of Health State
  Register of Medicinal Products, with local normalized search across Ukrainian,
  Russian, INN, ingredient, manufacturer, ATC, and registration fields.
- Added public catalogue status/search API endpoints and an optional
  startup freshness check for the production Compose service.
- Added manual/catalogue entry choices to medicine creation. Catalogue selections
  retain an official metadata snapshot through local-first synchronization and
  expose form/package, ingredients, manufacturer, registration, dispensing,
  ATC, attribution, and official instruction links on medicine details.
- Kept intake amount and schedule explicitly user-entered; catalogue information
  is read-only reference material and never generates treatment recommendations.
- Added Small, Regular, and Large text-size presets in Settings. The preference
  is persisted and synchronized, and scales typography throughout the Mini App;
  Regular is now slightly larger than the previous default.

## [1.0.1] - 2026-07-13

### Fixed

- Opening the mobile keyboard in Telegram no longer resizes the app and pushes
  the bottom navigation and floating actions above it. Supporting Chromium
  WebViews use keyboard overlay mode, while older Telegram Android WebViews
  retain the pre-keyboard viewport height and compensate for viewport resizing.

### Changed

- Full-screen loading, retry, and open-in-Telegram states now use the same
  circular MedAlarm emblem as the app header.
- Added development-only `/dev/loading`, `/dev/error`, and
  `/dev/open-in-telegram` routes for stable visual review of transient states.

## [1.0.0] - 2026-07-13

Initial tracked release. This tag is the baseline MedAlarm starts versioning
from; earlier bot-only history exists as untagged commits on `main`.

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

[Unreleased]: https://github.com/Miha21222/MedAlarm/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/Miha21222/MedAlarm/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/Miha21222/MedAlarm/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/Miha21222/MedAlarm/releases/tag/v1.0.0
