from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from config import CHANNEL_ID, MOSCOW
from placeholders import runtime_repository as repository

router = Router()


keyboard_event_list = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎫 Посмотреть мероприятия", callback_data="show_events")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")],
    ]
)

keyboard_registration_closed = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎫 Другие мероприятия", callback_data="show_events")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")],
    ]
)

keyboard_after_registration = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎫 Другие мероприятия", callback_data="show_events")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")],
    ]
)


def format_datetime(value) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d.%m.%Y в %H:%M")
    return str(value)


def is_deadline_passed(deadline) -> bool:
    if deadline is None:
        return False

    if isinstance(deadline, str):
        if deadline.startswith("0000-00-00"):
            return True
        try:
            deadline = datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return True

    now = datetime.now(MOSCOW).replace(tzinfo=None)
    return now > deadline


def get_event_text(event: dict) -> str:
    return (
        f"🎫 {event['name']}\n\n"
        f"📝 {event['description']}\n\n"
        f"📍 {event['address']}\n"
        f"🗓 Начало: {format_datetime(event['start_date'])}\n"
        f"🏁 Окончание: {format_datetime(event['end_date'])}"
    )


def get_event_keyboard(
    event_id: int,
    *,
    registered: bool = False,
    closed: bool = False,
) -> InlineKeyboardMarkup:
    if registered:
        primary = InlineKeyboardButton(
            text="✅ Вы уже записаны",
            callback_data="noop",
        )
    elif closed:
        primary = InlineKeyboardButton(
            text="🔒 Регистрация закрыта",
            callback_data="noop",
        )
    else:
        primary = InlineKeyboardButton(
            text="✅ Записаться",
            callback_data=f"register_event:{event_id}",
        )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [primary],
            [InlineKeyboardButton(text="🎫 Другие мероприятия", callback_data="show_events")],
            [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")],
        ]
    )


def get_subscribe_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📣 Подписаться на канал",
                    url="https://t.me/StartupClubRTUMIREA",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Проверить подписку",
                    callback_data=f"check_subscription:{event_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К мероприятию",
                    callback_data=f"event:{event_id}",
                )
            ],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
    )


async def get_subscription_status(
    bot: Bot,
    user_id: int,
    group_id=CHANNEL_ID,
) -> bool | None:
    try:
        member = await bot.get_chat_member(group_id, user_id)
    except (TelegramBadRequest, TelegramForbiddenError) as error:
        print("Subscription check failed:", repr(error))
        return None

    return member.status in ("administrator", "member", "creator")


async def _show_event_card(callback: CallbackQuery, event_id: int) -> None:
    event = await repository.get_event(event_id)
    if event is None:
        await callback.message.edit_text(
            "Мероприятие не найдено.",
            reply_markup=keyboard_event_list,
        )
        return

    registered = await repository.is_registered(callback.from_user.id, event_id)
    closed = is_deadline_passed(event.get("deadline"))

    await callback.message.edit_text(
        get_event_text(event),
        reply_markup=get_event_keyboard(
            event_id,
            registered=registered,
            closed=closed,
        ),
    )


async def _validate_event_for_registration(
    callback: CallbackQuery,
    event_id: int,
):
    user = await repository.find_user(callback.from_user.id)
    if user is None:
        await callback.message.edit_text(
            "Сначала завершите регистрацию в боте через /start.",
            reply_markup=keyboard_event_list,
        )
        return None

    event = await repository.get_event(event_id)
    if event is None:
        await callback.message.edit_text(
            "Мероприятие не найдено.",
            reply_markup=keyboard_event_list,
        )
        return None

    if is_deadline_passed(event.get("deadline")):
        await callback.message.edit_text(
            "К сожалению, регистрация на это мероприятие завершена.\n\n"
            "Анонс следующего мероприятия вы сможете увидеть "
            "в нашем канале и в этом боте.",
            reply_markup=keyboard_registration_closed,
        )
        return None

    if await repository.is_registered(callback.from_user.id, event_id):
        await callback.message.edit_text(
            "✅ Вы уже записаны на это мероприятие.\n\n" + get_event_text(event),
            reply_markup=get_event_keyboard(event_id, registered=True),
        )
        return None

    return event


async def complete_registration(
    callback: CallbackQuery,
    event_id: int,
    event: dict,
) -> None:
    success = await repository.add_registration(
        callback.from_user.id,
        event_id,
    )

    if not success:
        if await repository.is_registered(callback.from_user.id, event_id):
            await callback.message.edit_text(
                "✅ Вы уже записаны на это мероприятие.\n\n" + get_event_text(event),
                reply_markup=get_event_keyboard(event_id, registered=True),
            )
            return

        await callback.message.edit_text(
            "Не удалось записаться на мероприятие. Попробуйте ещё раз чуть позже.",
            reply_markup=get_event_keyboard(event_id),
        )
        return

    await callback.message.edit_text(
        "✅ Вы успешно записались!\n\n"
        f"🎫 {event['name']}\n"
        f"🗓 {format_datetime(event['start_date'])}\n"
        f"📍 {event['address']}",
        reply_markup=keyboard_after_registration,
    )


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "show_events")
async def show_available_events(callback: CallbackQuery):
    await callback.answer()

    events = await repository.get_available_events()
    if not events:
        await callback.message.edit_text(
            "Сейчас нет доступных мероприятий.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")]
                ]
            ),
        )
        return

    buttons = [
        [
            InlineKeyboardButton(
                text=event["name"],
                callback_data=f"event:{event['id']}",
            )
        ]
        for event in events
    ]
    buttons.append(
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")]
    )

    await callback.message.edit_text(
        "Выберите мероприятие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("event:"))
async def show_event(callback: CallbackQuery):
    await callback.answer()
    event_id = int(callback.data.split(":", 1)[1])
    await _show_event_card(callback, event_id)


@router.callback_query(F.data.startswith("register_event:"))
async def registration_on_event(
    callback: CallbackQuery,
    bot: Bot
):
    await callback.answer()

    event_id = int(callback.data.split(":", 1)[1])
    event = await _validate_event_for_registration(callback, event_id)
    if event is None:
        return

    subscription = await get_subscription_status(bot, callback.from_user.id)
    if subscription is None:
        await callback.message.edit_text(
            "Не удалось проверить подписку на канал.\n\n"
            "Для этой проверки бот должен иметь доступ к участникам канала. "
            "Попросите администратора канала добавить бота в администраторы, "
            "а затем нажмите «Проверить подписку».",
            reply_markup=get_subscribe_keyboard(event_id),
        )
        return

    if subscription:
        await complete_registration(callback, event_id, event)
        return

    await callback.message.edit_text(
        "Чтобы продолжить регистрацию и быть в курсе всех наших мероприятий "
        "и не только, необходимо подписаться на канал клуба 👇",
        reply_markup=get_subscribe_keyboard(event_id),
    )


@router.callback_query(F.data.startswith("check_subscription:"))
async def check_subscription(
    bot: Bot,
    callback: CallbackQuery
):
    await callback.answer()

    event_id = int(callback.data.split(":", 1)[1])
    event = await _validate_event_for_registration(callback, event_id)
    if event is None:
        return

    subscription = await get_subscription_status(bot, callback.from_user.id)
    if subscription is None:
        await callback.message.edit_text(
            "Не удалось проверить подписку. Бот должен быть администратором канала, "
            "чтобы надёжно проверять участников.",
            reply_markup=get_subscribe_keyboard(event_id),
        )
        return

    if subscription:
        await complete_registration(callback, event_id, event)
    else:
        await callback.message.edit_text(
            "Подписка пока не найдена. Подпишитесь на канал и нажмите "
            "«Проверить подписку» ещё раз.",
            reply_markup=get_subscribe_keyboard(event_id),
        )
