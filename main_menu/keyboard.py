from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 Мой профиль",
                    callback_data="profile"
                ),
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data="edit_profile"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💰 Мой баланс",
                    callback_data="balance"
                )
            ]
        ]
    )