from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.database.session import session_scope
from app.services.intake_service import IntakeService
from app.services.user_service import UserService

router = Router()


@router.message(Command("history"))
async def cmd_history(message: Message) -> None:
    if message.from_user is None:
        return
    args = (message.text or "").split()[1:]
    period = "week"
    medicine_id = None
    if args:
        if args[0] in {"today", "week", "month"}:
            period = args[0]
        else:
            await message.answer("Период: today/week/month. Пример: /history week 3")
            return
    if len(args) > 1:
        if args[1].isdigit():
            medicine_id = int(args[1])
        else:
            await message.answer("ID лекарства должен быть числом.")
            return

    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, message.from_user.id)
        if user is None:
            await message.answer("Сначала запустите /start.")
            return
        records = await IntakeService.history(
            session=session,
            user_id=user.id,
            period=period,
            medicine_id=medicine_id,
            limit=50,
        )
    if not records:
        await message.answer("История пуста для выбранного фильтра.")
        return
    lines = [f"История ({period}):"]
    for row in records:
        lines.append(
            f"- {row.scheduled_at.strftime('%Y-%m-%d %H:%M')} | {row.medicine.name} | {IntakeService.status_to_emoji(row.status)}"
        )
    await message.answer("\n".join(lines))

