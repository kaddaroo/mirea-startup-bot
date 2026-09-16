from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
# сразу вопрос - прописываем ли эти библиотеки или все библиотеки в один файл запихнем и просто в каждом файле импорт библиотечного сделаем?
# еще вопрос где это протестить? именно вид в тг, типа прост своего тестового бота зарегать?

import repository

router = Router()


def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать профиль",
                    callback_data="edit_profile"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="main_menu"
                )
            ]
        ]
    )


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