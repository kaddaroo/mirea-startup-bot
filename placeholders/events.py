# from aiogram import F, Router, Bot
# from aiogram.types import (
#     CallbackQuery,
#     InlineKeyboardButton,
#     InlineKeyboardMarkup,
# )

# import repository
# from config import REGISTRATION_DEADLINE, CHANNEL_ID
# from datetime import datetime, timezone

# router = Router()

# keyboard_subcribe = InlineKeyboardMarkup(
#         [InlineKeyboardButton(text="Подписаться на канал", url='https://t.me/StartupClubRTUMIREA')],
#         [InlineKeyboardButton(text="Проверить подписку", callback_data='registration on event')]
#     )

# keyboard_event_list = InlineKeyboardMarkup([InlineKeyboardButton(text='Посмотреть доступные мероприятия')])

# keyboard_to_main_menu = InlineKeyboardMarkup(InlineKeyboardButton(text='Назад', callback_data=''))

# async def is_subcribed_on_channel(bot: Bot, user_id, group_id=CHANNEL_ID) -> bool:
#     member = await bot.get_chat_member(group_id, user_id)
    
#     return member.status in ('administrator', 'member', 'creator')

# def is_deadline_passed() -> bool:
#     return datetime.now(timezone.utc) > REGISTRATION_DEADLINE

# async def show_available_events() -> list:
    

# @router.callback_query(F.data=='registration on event')
# async def registration_on_event(bot: Bot, callbackquery: CallbackQuery):
#     if is_deadline_passed():
#         await callbackquery.message.edit_text("""К сожалению, регистрация уже закрыта.
#                                 Посмотрите другие мероприятия, доступные на данный момент.""")
#         InlineKeyboardButton()
#         return 
    
#     if await is_subcribed_on_channel(bot, callbackquery.from_user.id):
#         repository.add_registration(callbackquery.from_user.id, 'event code')
#         await callbackquery.message.edit_text(f"""Вы успешно записались на мероприятие!
#                                     Ждем вас {REGISTRATION_DEADLINE} по адресу {...}""")
#         return
#     await callbackquery.message.edit_text("Для записи на мероприятие, Вам нужно подписаться на канал", reply_markup=keyboard_subcribe)
