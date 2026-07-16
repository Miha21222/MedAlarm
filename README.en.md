<p align="center">
  <a href="README.md">Русский</a> · <a href="README.uk.md">Українська</a> · <strong>English</strong>
</p>

<div align="center">
  <img src="frontend/public/logo.png" alt="MedAlarm logo" width="128" />
  <h1>MedAlarm</h1>
  <p><strong>A simple Telegram assistant for medication reminders</strong></p>
  <p>
    <a href="https://t.me/med_alarm_bot?start=app">Open in Telegram</a>
    · <a href="https://github.com/Miha21222/MedAlarm/releases/latest">Latest release</a>
    · <a href="CHANGELOG.md">Changelog</a>
  </p>
</div>

> [!IMPORTANT]
> MedAlarm does not provide medical advice, recommend dosages, or change
> treatment plans. The app only reminds users about the medicines, amounts,
> and intake times they entered themselves according to their prescription.

## What MedAlarm can do

- ⏰ Sends reminders according to a schedule entered by the user.
- ✅ Lets users mark a dose as taken, skip it, or snooze the reminder directly in Telegram.
- 💊 Stores a medicine list, amount per intake, comments, and multiple daily times.
- 🔎 Supports manual entry and search in the official State Register of Medicinal Products of Ukraine.
- 📊 Shows today's plan and schedule-adherence statistics.
- 📜 Groups history by day and medicine, with period and status filters.
- 🌐 Works in Russian, Ukrainian, and English.
- 🔤 Supports three text sizes, haptic feedback, and voice input where available.
- 🔄 Saves medicines locally and synchronizes them with the server after Telegram authentication.
- 📨 Accepts ratings and bug reports, including an optional screenshot.

## Getting started

1. Open [@med_alarm_bot](https://t.me/med_alarm_bot?start=app) and press **Start** or send `/start`.
2. Press **“Open MedAlarm”** in the bot's message.
3. Open the **“Medicines”** tab and press `+`.
4. Choose how to add the medicine:
   - **from the MOH catalogue** — find a registered product, then enter the prescribed amount and time yourself;
   - **manually** — enter the name, amount, comment, and schedule yourself.
5. Save the medicine. It will appear in today's plan and synchronize with the server.
6. When a real reminder arrives, choose **“Taken”**, **“Skip”**, or **“Remind later”**.
7. Use the **“History”** tab to review completed and skipped intakes.

The form draft is saved automatically. You can leave the page, switch between manual entry and the catalogue, and return without losing entered values.

## Interface

The screenshots use demonstration data. They are interface examples, not medical prescriptions.

<table>
  <tr>
    <td align="center">
      <img src="docs/screenshots/dashboard.png" alt="Today's intake plan" width="250" /><br />
      <strong>Today's plan</strong><br />Upcoming intakes and quick actions
    </td>
    <td align="center">
      <img src="docs/screenshots/medicines.png" alt="Medicine list" width="250" /><br />
      <strong>Medicines</strong><br />Amounts, times, and synchronization status
    </td>
  </tr>
  <tr>
    <td align="center">
      <img src="docs/screenshots/add-medicine.png" alt="Adding a medicine from the MOH catalogue" width="250" /><br />
      <strong>Add medicine</strong><br />MOH catalogue or manual entry
    </td>
    <td align="center">
      <img src="docs/screenshots/history.png" alt="Intake history" width="250" /><br />
      <strong>History</strong><br />Statistics, periods, and filters
    </td>
  </tr>
</table>

## How it works

MedAlarm consists of four parts:

- The **Telegram bot**, built with `aiogram 3`, registers users and delivers reminders.
- The **scheduler**, built with APScheduler, creates jobs from saved schedules and restores snoozed reminders after a restart.
- The **Backend API**, built with FastAPI and async SQLAlchemy, validates Telegram `initData`, synchronizes medicines, and serves settings, the daily plan, history, and feedback.
- The **Telegram Mini App**, built with React, TypeScript, and Vite, provides the mobile interface.

Core data is stored in SQLite. Medicines follow a local-first synchronization model, with conflicts resolved by the latest update time. Real intake history remains server-authoritative and is always linked to a reminder event.

## Running locally

### Option 1: interface with test authentication

Requires Node.js 22+ and npm:

```powershell
cd frontend
npm install
npm run dev:local
```

Open `http://localhost:5173/`. The local preview uses a test Telegram identity and allows you to enable an isolated demo mode. Demo data is never uploaded as real intake history.

### Option 2: bot, API, and scheduler in Docker

1. Copy `.env.example` to `.env`.
2. Provide at least a valid `BOT_TOKEN`, a secure `JWT_SECRET`, the HTTPS Mini App URL, and allowed CORS origins.
3. Start the stack:

```powershell
docker compose up --build -d
```

Docker starts the API and the combined bot-and-scheduler process. Cloudflare Tunnel is also available through the production profile.

### Option 3: separate development processes

Requires Python 3.12+:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m app.catalog_update
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

In separate terminals:

```powershell
python -m app.bot_main
python -m app.scheduler
```

For a regular local run with the bot and scheduler together, use `python main.py`.

## Validating changes

```powershell
python -m pytest
cd frontend
npm run test:local
npm run build
```

CI also builds the Docker image, validates the production Compose configuration, and deploys the Mini App to GitHub Pages after frontend changes reach `main`.

## Medicine catalogue

Search uses open data from the State Register of Medicinal Products of Ukraine, published on [data.gov.ua](https://data.gov.ua/) under **CC BY**. The catalogue provides reference information only: product name, dosage form, composition, manufacturer, registration details, ATC codes, and a link to the official instruction. The user always enters the intake amount and schedule.

Refresh the local catalogue:

```powershell
python -m app.catalog_update
```

## Deployment and operations

Production uses one backend container on a VPS, a persistent SQLite volume, Telegram long polling, and Cloudflare Tunnel. Do not run multiple backend replicas while the application relies on SQLite and a single Telegram polling process.

Instructions for initial deployment, releases, backups, restoration, and rollback are available in [`deploy/README.md`](deploy/README.md).

## Project structure

```text
app/
├── api/          # FastAPI API and Telegram authentication
├── database/     # SQLAlchemy models, sessions, and SQLite migrations
├── handlers/     # /start, /app, and reminder actions
├── scheduler/    # APScheduler jobs and reminder delivery
└── services/     # Business logic and database queries
frontend/         # React/Vite Telegram Mini App
tests/            # Backend tests
frontend/tests/   # Pure frontend-logic tests
deploy/           # Releases, backup, restore, and production documentation
```

## Licences and responsibility

The project's source code is distributed according to the repository's licence file, if present. Data from the Ukrainian State Register is used with the attribution required by the CC BY licence.

MedAlarm is a reminder-organization tool, not a medical information system. Consult a qualified medical professional about prescribing, changing, or discontinuing treatment.
