from __future__ import annotations

from aiogram import Bot
from aiogram.fsm.context import FSMContext


async def remember_context_message(state: FSMContext, message_id: int) -> None:
    data = await state.get_data()
    ids = set(data.get("context_message_ids", []))
    ids.add(message_id)
    await state.update_data(context_message_ids=list(ids))


async def cleanup_context_messages(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    keep_message_ids: set[int] | None = None,
) -> None:
    data = await state.get_data()
    ids = data.get("context_message_ids", [])
    keep = keep_message_ids or set()
    for message_id in ids:
        if message_id in keep:
            continue
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception:
            pass
    await state.update_data(context_message_ids=[])

