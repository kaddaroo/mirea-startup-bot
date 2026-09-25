import asyncio

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import (
    COINS_FIRST_ATTENDANCE_BONUS,
    COINS_PER_ATTENDANCE,
    WORKER_INTERVAL_SECONDS,
)
from placeholders import runtime_repository as repository
from handlers.engagement_handler import rating_keyboard


async def _safe_send(bot: Bot, chat_id: int, text: str, reply_markup=None) -> bool:
    try:
        await bot.send_message(chat_id, text, reply_markup=reply_markup)
        return True
    except (TelegramBadRequest, TelegramForbiddenError) as error:
        print(f"Send to {chat_id} failed: {error!r}")
        return False


async def process_attendance_coins():
    awarded = await repository.sync_attendance_coins(
        COINS_PER_ATTENDANCE,
        COINS_FIRST_ATTENDANCE_BONUS,
    )
    if awarded:
        print(f"Coin rewards issued: {awarded}")


async def process_24h_reminders(bot: Bot):
    for item in await repository.get_due_reminders(100):
        start = item["start_date"].strftime("%d.%m.%Y в %H:%M")
        lines = [
            f"🎫 {item['name']}", "",
            "Привет! 👋",
            f"Напоминаем, что мероприятие состоится уже скоро: {start}.", "",
            f"📍 Адрес: {item.get('address') or 'уточняется'}",
            f"🏢 Аудитория: {item.get('auditorium') or 'уточняется'}",
        ]
        if item.get("route_url"):
            lines.extend(["", f"🗺 Как добраться: {item['route_url']}"])
        lines.extend(["", "🛂 Обязательно не забудь взять с собой паспорт!", "", "До встречи ❤️"])
        if await _safe_send(bot, item["telegram_id"], "\n".join(lines)):
            await repository.mark_reminder_sent(item["reg_id"])


async def process_feedback(bot: Bot):
    for item in await repository.get_due_feedback(100):
        text = (
            f"Спасибо, что были с нами на «{item['name']}»! ❤️\n\n"
            "📝 Проработка формы займёт около 10 минут.\n\n"
            "1. Оценка по шкале от 1 до 5\n\n"
            "Оцените по шкале от 1 до 5:\n"
            "🏠 Локация"
        )
        if await _safe_send(
            bot,
            item["telegram_id"],
            text,
            rating_keyboard(item["event_id"], "location"),
        ):
            await repository.mark_feedback_sent(item["reg_id"])


async def process_incomplete_registration(bot: Bot):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Продолжить регистрацию", callback_data="continue_registration")]
    ])
    for lead in await repository.get_incomplete_leads(50):
        name = lead.get("first_name") or ""
        hello = f"Привет, {name}!" if name else "Привет!"
        text = (
            f"{hello} Ты тут? 👋\n\n"
            "Ты запускал бота, но не закончил регистрацию. Чтобы зарегистрироваться на мероприятие, "
            "нужно заполнить небольшую анкету — это займёт пару минут."
        )
        if await _safe_send(bot, lead["telegram_id"], text, keyboard):
            await repository.mark_lead_reminder_sent(lead["telegram_id"])


async def background_worker(bot: Bot):
    while True:
        for job in (
            process_attendance_coins,
            lambda: process_24h_reminders(bot),
            lambda: process_feedback(bot),
            lambda: process_incomplete_registration(bot),
        ):
            try:
                await job()
            except Exception as error:
                print("Background job error:", repr(error))
        await asyncio.sleep(WORKER_INTERVAL_SECONDS)
