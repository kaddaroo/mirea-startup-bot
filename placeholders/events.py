import re
from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import CHANNEL_ID, MOSCOW
from placeholders import runtime_repository as repository
from ui_helpers import replace_callback_with_photo, replace_callback_with_text

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
    description = event.get("description") or "Описание появится позже."
    address = event.get("address") or "Уточняется"

    lines = [
        f"🎫 {event['name']}",
        "",
        f"📝 {description}",
        "",
        f"📍 {address}",
    ]
    if event.get("auditorium"):
        lines.append(f"🏢 Аудитория: {event['auditorium']}")
    lines.extend([
        f"🗓 Начало: {format_datetime(event['start_date'])}",
        f"🏁 Окончание: {format_datetime(event['end_date'])}",
    ])
    if event.get("route_url"):
        lines.extend(["", f"🗺 Как добраться: {event['route_url']}"])
    return "\n".join(lines)


def get_event_caption(event: dict) -> str:
    text = get_event_text(event)
    if len(text) <= 1024:
        return text
    return text[:1020].rstrip() + "…"


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
        await replace_callback_with_text(
            callback,
            "Мероприятие не найдено.",
            reply_markup=keyboard_event_list,
        )
        return

    registered = await repository.is_registered(callback.from_user.id, event_id)
    closed = is_deadline_passed(event.get("deadline"))
    keyboard = get_event_keyboard(
        event_id,
        registered=registered,
        closed=closed,
    )

    photo_file_id = event.get("photo_file_id")
    if photo_file_id:
        await replace_callback_with_photo(
            callback,
            photo=photo_file_id,
            caption=get_event_caption(event),
            reply_markup=keyboard,
        )
        return

    await replace_callback_with_text(
        callback,
        get_event_text(event),
        reply_markup=keyboard,
    )


async def _validate_event_for_registration(
    callback: CallbackQuery,
    event_id: int,
):
    user = await repository.find_user(callback.from_user.id)
    if user is None:
        await replace_callback_with_text(
            callback,
            "Сначала завершите регистрацию в боте через /start.",
            reply_markup=keyboard_event_list,
        )
        return None

    event = await repository.get_event(event_id)
    if event is None:
        await replace_callback_with_text(
            callback,
            "Мероприятие не найдено.",
            reply_markup=keyboard_event_list,
        )
        return None

    if is_deadline_passed(event.get("deadline")):
        await replace_callback_with_text(
            callback,
            "К сожалению, регистрация на это мероприятие завершена.\n\n"
            "Анонс следующего мероприятия вы сможете увидеть "
            "в нашем канале и в этом боте.",
            reply_markup=keyboard_registration_closed,
        )
        return None

    if await repository.is_registered(callback.from_user.id, event_id):
        await replace_callback_with_text(
            callback,
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
            await replace_callback_with_text(
                callback,
                "✅ Вы уже записаны на это мероприятие.\n\n" + get_event_text(event),
                reply_markup=get_event_keyboard(event_id, registered=True),
            )
            return

        await replace_callback_with_text(
            callback,
            "Не удалось записаться на мероприятие. Попробуйте ещё раз чуть позже.",
            reply_markup=get_event_keyboard(event_id),
        )
        return

    await replace_callback_with_text(
        callback,
        "✅ Вы успешно записались!\n\n"
        f"🎫 {event['name']}\n"
        f"🗓 {format_datetime(event['start_date'])}\n"
        f"📍 {event.get('address') or 'Уточняется'}",
        reply_markup=keyboard_after_registration,
    )


def _channel_is_configured_channel(message: Message) -> bool:
    if isinstance(CHANNEL_ID, int):
        return message.chat.id == CHANNEL_ID

    configured = str(CHANNEL_ID).lstrip("@").lower()
    username = (message.chat.username or "").lower()
    return bool(configured and username == configured)


@router.channel_post(F.photo)
async def capture_event_photo_from_channel(message: Message):
    """Store a Telegram photo file_id for posts containing #event_<id> or event:<id>."""
    if not _channel_is_configured_channel(message):
        return

    caption = message.caption or ""
    match = re.search(r"(?:#event_|event:)(\d+)", caption, flags=re.IGNORECASE)
    if match is None:
        return

    event_id = int(match.group(1))
    photo_file_id = message.photo[-1].file_id

    updated = await repository.update_event_photo(
        event_id,
        photo_file_id,
        message.message_id,
    )

    if updated:
        print(f"Saved channel photo for event {event_id}")
    else:
        print(f"Channel photo ignored: event {event_id} not found")


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data == "show_events")
async def show_available_events(callback: CallbackQuery):
    await callback.answer()

    events = await repository.get_available_events()
    if not events:
        await replace_callback_with_text(
            callback,
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

    await replace_callback_with_text(
        callback,
        "Выберите мероприятие:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(F.data.startswith("event:"))
async def show_event(callback: CallbackQuery):
    await callback.answer()
    event_id = int(callback.data.split(":", 1)[1])
    await _show_event_card(callback, event_id)


@router.callback_query(F.data.startswith("register_event:"))
async def registration_on_event(callback: CallbackQuery, bot: Bot):
    await callback.answer()

    event_id = int(callback.data.split(":", 1)[1])
    event = await _validate_event_for_registration(callback, event_id)
    if event is None:
        return

    subscription = await get_subscription_status(bot, callback.from_user.id)
    if subscription is None:
        await replace_callback_with_text(
            callback,
            "Не удалось проверить подписку на канал.\n\n"
            "Бот должен быть администратором канала, чтобы проверять участников. "
            "После добавления бота в администраторы нажмите «Проверить подписку».",
            reply_markup=get_subscribe_keyboard(event_id),
        )
        return

    if subscription:
        await complete_registration(callback, event_id, event)
        return

    await replace_callback_with_text(
        callback,
        "Чтобы продолжить регистрацию и быть в курсе всех наших мероприятий "
        "и не только, необходимо подписаться на канал клуба 👇",
        reply_markup=get_subscribe_keyboard(event_id),
    )


@router.callback_query(F.data.startswith("check_subscription:"))
async def check_subscription(callback: CallbackQuery, bot: Bot):
    await callback.answer()

    event_id = int(callback.data.split(":", 1)[1])
    event = await _validate_event_for_registration(callback, event_id)
    if event is None:
        return

    subscription = await get_subscription_status(bot, callback.from_user.id)
    if subscription is None:
        await replace_callback_with_text(
            callback,
            "Не удалось проверить подписку. Бот должен быть администратором канала, "
            "чтобы надёжно проверять участников.",
            reply_markup=get_subscribe_keyboard(event_id),
        )
        return

    if subscription:
        await complete_registration(callback, event_id, event)
    else:
        await replace_callback_with_text(
            callback,
            "Подписка пока не найдена. Подпишитесь на канал и нажмите "
            "«Проверить подписку» ещё раз.",
            reply_markup=get_subscribe_keyboard(event_id),
        )
