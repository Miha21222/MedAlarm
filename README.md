# MedAlarm

Telegram-бот для напоминаний о приёме лекарств (MVP на `aiogram 3`, `SQLite`, `SQLAlchemy`, `APScheduler`).

## Возможности MVP
- `/start` регистрация пользователя.
- `/add_medicine` пошаговое добавление лекарства и расписания.
- `/my_medicines` просмотр и управление активностью лекарства.
- `/today` план на сегодня.
- `/history [today|week|month] [medicine_id]` история приёмов.
- `/settings` настройка timezone, snooze и повторов до подтверждения.
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

