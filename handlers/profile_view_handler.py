from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from placeholders import repository

from main_menu.keyboard import profile_keyboard

router = Router()

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = repository.find_user(callback.from_user.id)

    if user is None:
        await callback.answer("Профиль не найден", show_alert=True)
        return

    text = (
        "👤 <b>Ваш профиль</b>\n\n"
        f"{user.get('surname', '')} "
        f"{user.get('name', '')} "
        f"{user.get('patronymic', '')}\n\n"
        f"🎂 {user.get('birth_date', '—')}\n"
        f"🎓 {user.get('university', '—')}\n"
        f"📚 {user.get('course', '—')} курс\n"
        f"💻 {user.get('direction', '—')}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=profile_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()