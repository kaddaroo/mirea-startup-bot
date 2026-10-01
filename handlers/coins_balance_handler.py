from aiogram import F, Router
from aiogram.types import CallbackQuery

from main_menu.keyboard import balance_keyboard
from placeholders import runtime_repository as repository
from ui_helpers import replace_callback_with_text, safe_callback_answer, safe_edit_callback_text

router = Router()


@router.callback_query(F.data == "balance")
async def balance_handler(callback: CallbackQuery):
    await safe_callback_answer(callback)
    user = await repository.find_user(callback.from_user.id)

    if user is None:
        await safe_edit_callback_text(callback, "Профиль не найден.")
        return

    await replace_callback_with_text(
        callback,
        "💰 <b>Ваш баланс</b>\n\n"
        f"🪙 {user.get('coins', 0)} коинов",
        reply_markup=balance_keyboard(),
        parse_mode="HTML",
    )
