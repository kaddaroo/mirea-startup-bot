from io import BytesIO

import qrcode
from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from handlers.admin_panel_handler import admin_menu_keyboard, is_admin
from placeholders import runtime_repository as repository

router = Router()


def _event_admin_keyboard(event_id: int, checkin_open: bool) -> InlineKeyboardMarkup:
    toggle = (
        InlineKeyboardButton(text="🔴 Закрыть check-in", callback_data=f"admin_checkin_close:{event_id}")
        if checkin_open
        else InlineKeyboardButton(text="🟢 Открыть check-in", callback_data=f"admin_checkin_open:{event_id}")
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 QR для отметки", callback_data=f"admin_event_qr:{event_id}")],
        [toggle],
        [InlineKeyboardButton(text="⬅️ Админ-панель", callback_data="admin_menu")],
    ])


@router.callback_query(F.data.startswith("admin_event_manage:"))
async def manage_event(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    event_id = int(callback.data.split(":", 1)[1])
    event = await repository.get_event(event_id)
    if not event:
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    await callback.message.edit_text(
        f"🛠 #{event['id']} — {event['name']}\n\n"
        f"Check-in: {'открыт' if event.get('checkin_open') else 'закрыт'}",
        reply_markup=_event_admin_keyboard(event_id, bool(event.get("checkin_open"))),
    )


@router.callback_query(F.data.startswith("admin_checkin_open:"))
async def open_checkin(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    event_id = int(callback.data.split(":", 1)[1])
    await repository.set_checkin_open(event_id, True)
    await callback.message.edit_text(
        "🟢 Check-in открыт. Теперь QR отмечает присутствие и сразу начисляет коины.",
        reply_markup=_event_admin_keyboard(event_id, True),
    )


@router.callback_query(F.data.startswith("admin_checkin_close:"))
async def close_checkin(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    event_id = int(callback.data.split(":", 1)[1])
    await repository.set_checkin_open(event_id, False)
    await callback.message.edit_text(
        "🔴 Check-in закрыт. QR больше не отмечает присутствие.",
        reply_markup=_event_admin_keyboard(event_id, False),
    )


@router.callback_query(F.data.startswith("admin_event_qr:"))
async def event_qr(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    event_id = int(callback.data.split(":", 1)[1])
    event = await repository.get_event(event_id)
    if not event:
        await callback.answer("Мероприятие не найдено", show_alert=True)
        return
    token = event.get("checkin_token") or await repository.ensure_event_checkin_token(event_id)
    if not token:
        await callback.answer("Не удалось создать check-in token", show_alert=True)
        return

    me = await callback.bot.get_me()
    deep_link = f"https://t.me/{me.username}?start=checkin_{token}"
    image = qrcode.make(deep_link)
    buf = BytesIO()
    image.save(buf, format="PNG")

    await callback.bot.send_photo(
        callback.from_user.id,
        BufferedInputFile(buf.getvalue(), filename=f"event_{event_id}_checkin.png"),
        caption=(
            f"📱 QR для отметки посещения\n\n"
            f"🎫 {event['name']}\n"
            f"Ссылка: {deep_link}\n\n"
            "Перед началом мероприятия откройте check-in в админ-панели."
        ),
    )
