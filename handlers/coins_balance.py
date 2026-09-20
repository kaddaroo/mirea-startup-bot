from aiogram import Router, F
from aiogram.types import CallbackQuery

from main_menu import coins_logic

from main_menu.keyboard import balance_keyboard


router = Router()


@router.callback_query(F.data == "balance")
async def balance_handler(
    callback: CallbackQuery
):
    try:
        balance = await coins_logic.get_balance(
            callback.from_user.id
        )

    except ValueError:
        await callback.answer(
            "Профиль не найден",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        f"💰 <b>Ваш баланс</b>\n\n"
        f"🪙 {balance} коинов",
        reply_markup=balance_keyboard(),
        parse_mode="HTML"
    )

    await callback.answer()