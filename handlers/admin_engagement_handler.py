from io import BytesIO

import qrcode
from aiogram import F, Router
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from handlers.admin_panel_handler import admin_menu_keyboard, is_admin
from placeholders import runtime_repository as repository

from ui_helpers import safe_callback_answer, safe_edit_callback_text

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
        await safe_callback_answer(callback, "Нет доступа", show_alert=True)
        return
    await safe_callback_answer(callback)
    event_id = int(callback.data.split(":", 1)[1])
    event = await repository.get_event(event_id)
    if not event:
        await safe_edit_callback_text(
            callback,
            "⚠️ Мероприятие не найдено.",
            reply_markup=admin_menu_keyboard(),
        )
        return
    await safe_edit_callback_text(callback, 
        f"🛠 #{event['id']} — {event['name']}\n\n"
        f"Check-in: {'открыт' if event.get('checkin_open') else 'закрыт'}",
        reply_markup=_event_admin_keyboard(event_id, bool(event.get("checkin_open"))),
    )


@router.callback_query(F.data.startswith("admin_checkin_open:"))
async def open_checkin(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await safe_callback_answer(callback, "Нет доступа", show_alert=True)
        return
    await safe_callback_answer(callback)
    event_id = int(callback.data.split(":", 1)[1])
    await repository.set_checkin_open(event_id, True)
    await safe_edit_callback_text(callback, 
        "🟢 Check-in открыт. Теперь QR отмечает присутствие и сразу начисляет коины.",
        reply_markup=_event_admin_keyboard(event_id, True),
    )


@router.callback_query(F.data.startswith("admin_checkin_close:"))
async def close_checkin(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await safe_callback_answer(callback, "Нет доступа", show_alert=True)
        return
    await safe_callback_answer(callback)
    event_id = int(callback.data.split(":", 1)[1])
    await repository.set_checkin_open(event_id, False)
    await safe_edit_callback_text(callback, 
        "🔴 Check-in закрыт. QR больше не отмечает присутствие.",
        reply_markup=_event_admin_keyboard(event_id, False),
    )


@router.callback_query(F.data.startswith("admin_event_qr:"))
async def event_qr(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await safe_callback_answer(callback, "Нет доступа", show_alert=True)
        return
    await safe_callback_answer(callback)

    event_id = int(callback.data.split(":", 1)[1])
    event = await repository.get_event(event_id)
    if not event:
        await safe_edit_callback_text(
            callback,
            "⚠️ Мероприятие не найдено.",
            reply_markup=admin_menu_keyboard(),
        )
        return
    token = event.get("checkin_token") or await repository.ensure_event_checkin_token(event_id)
    if not token:
        await safe_edit_callback_text(
            callback,
            "⚠️ Не удалось создать check-in token.",
            reply_markup=_event_admin_keyboard(event_id, bool(event.get("checkin_open"))),
        )
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
