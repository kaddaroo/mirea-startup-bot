from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from placeholders import runtime_repository as repository

from main_menu.keyboard import profile_keyboard

router = Router()


def _field(user, name: str, default=""):
    if isinstance(user, dict):
        return user.get(name, default)
    return getattr(user, name, default)


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user = await repository.find_user(callback.from_user.id)

    if user is None:
        await callback.answer("Профиль не найден", show_alert=True)
        return

    text = (
        "👤 <b>Ваш профиль</b>\n\n"
        f"{_field(user, 'surname')} "
        f"{_field(user, 'name')} "
        f"{_field(user, 'patronymic')}\n\n"
        f"🎓 ID вуза: {_field(user, 'id_university', '—') or '—'}\n"
        f"🏫 {_field(user, 'institute', '—') or '—'}\n"
        f"💻 {_field(user, 'direction_code', '—') or '—'}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=profile_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()