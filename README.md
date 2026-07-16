# MedAlarm

The current production-candidate changes are recorded in
[`CHANGELOG.md`](CHANGELOG.md). The remaining release and infrastructure work
is tracked in the checklist in [`deploy/README.md`](deploy/README.md).

## Telegram Mini App

MedAlarm now includes a full-stack Telegram Mini App:

- `frontend/` is the React + TypeScript + Vite interface.
- `app/api/` is the FastAPI authentication, sync, dashboard, history, and
  settings API.
- `python -m app.bot_main` runs Telegram long polling.
- `python -m app.scheduler` runs reminder scheduling.
- `python -m app.runtime` supervises the API plus the existing bot/scheduler
  runtime for Docker. Bot and scheduler intentionally remain together until
  snoozes are persisted rather than held in process memory.

### Frontend development

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
npm.cmd run test:local
npm.cmd run build
```

Vite development mode uses a local Telegram identity stub and browser
`localStorage`. Production builds require Telegram `initData`.

When the local preview is running, development-only full-screen state previews
are available at `/dev/loading`, `/dev/error`, and
`/dev/open-in-telegram`. These paths are disabled in production builds.

### Backend development

Import or refresh the openly licensed Ukrainian MOH State Register catalogue,
then start the API:

```powershell
python -m app.catalog_update
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
python -m app.bot_main
python -m app.scheduler
```

Add these values to the existing root `.env`:

```dotenv
JWT_SECRET=replace-with-a-long-random-secret
JWT_EXPIRE_MINUTES=1440
MINI_APP_URL=https://your-pages-host/MedAlarm/
CORS_ALLOWED_ORIGINS=https://your-pages-host
```

The legacy SQLite schema is upgraded in place on startup. Medicines receive
stable client IDs for local-first synchronization; reminder dispatch and intake
records remain server-authoritative.

The create-medicine screen supports manual entry and MOH catalogue search. The
catalogue is imported from the official `data.gov.ua` State Register CSV under
CC BY. It supplies product identity, form/package, ingredients, manufacturer,
registration, ATC and official instruction links; the user always enters their
own prescribed intake amount and schedule. Compose enables a source freshness
check on backend startup with `CATALOG_AUTO_UPDATE=true`.

### Production deployment

Production uses GitHub Pages for the frontend and a single Hostinger VPS
Compose stack behind Cloudflare Tunnel for the API, bot, and scheduler. Start
from `.env.example`; never reuse development secrets. The complete first
deployment, tagged-release, backup, restore, and rollback procedure is in
[`deploy/README.md`](deploy/README.md).

The production stack intentionally supports one backend replica while it uses
SQLite and Telegram long polling. Mini App schedule changes are reconciled by
the scheduler, and pending snoozes are restored after container restarts.

Settings now includes authenticated rating and bug-report forms. Submissions
are stored in SQLite and relayed best-effort to configured Telegram forum
topics; bug reports may include a JPEG, PNG, or WebP screenshot up to 8 MB.
Demo data is development-only and cannot be enabled by a production build.

Telegram-бот для напоминаний о приёме лекарств (MVP на `aiogram 3`, `SQLite`, `SQLAlchemy`, `APScheduler`).

## Возможности MVP
- `/start` регистрирует пользователя и предлагает открыть Mini App.
- Лекарства, расписание, история и настройки доступны в Mini App.
- Напоминания с inline-кнопками: `✅ Принял`, `⏰ Напомнить через 10 минут`, `⏭ Пропустить`.

## Быстрый запуск локально
1. Создайте окружение и установите зависимости:
   - `python -m venv .venv`
   - `.venv\Scripts\activate`
   - `pip install -r requirements.txt`
2. Создайте `.env` на основе `.env.example` и заполните `BOT_TOKEN`.
3. Запустите бота:
   - `python main.py`

## Запуск в Docker
1. Подготовьте `.env`.
2. Выполните:
   - `docker compose up --build -d`

## Структура
- `app/config.py` - конфиг приложения.
- `app/database` - модели и подключение к БД.
- `app/handlers` - команды и callback-обработчики.
- `app/services` - бизнес-логика.
- `app/scheduler` - APScheduler и задачи напоминаний.
- `tests` - unit/integration тесты.

## Важное ограничение
Бот не даёт медицинские рекомендации, не подбирает дозировки и не меняет схему лечения. Он только напоминает по данным, которые ввёл пользователь.
