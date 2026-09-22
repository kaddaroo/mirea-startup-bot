from datetime import datetime

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import ADMIN_IDS, MOSCOW
from placeholders import runtime_repository as repository
from ui_helpers import replace_callback_with_text, safe_callback_answer

router = Router()
DATE_FORMAT = "%d.%m.%Y %H:%M"


class EventCreate(StatesGroup):
    name = State()
    description = State()
    address = State()
    auditorium = State()
    route_url = State()
    start_date = State()
    end_date = State()
    deadline = State()
    photo = State()
    confirm = State()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать мероприятие", callback_data="admin_event_create")],
            [InlineKeyboardButton(text="📋 Список мероприятий", callback_data="admin_events_list")],
            [InlineKeyboardButton(text="🔗 Маркетинговая ссылка", callback_data="admin_marketing_create")],
            [InlineKeyboardButton(text="📊 Маркетинговая статистика", callback_data="admin_marketing_stats")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")],
        ]
    )


def wizard_keyboard(back_to: str | None = None, *, photo_step: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if photo_step:
        rows.append([InlineKeyboardButton(text="⏭ Без фото", callback_data="admin_event_photo_skip")])

    navigation = []
    if back_to:
        navigation.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_event_back:{back_to}")
        )
    navigation.append(InlineKeyboardButton(text="✖️ Отмена", callback_data="admin_event_cancel"))
    rows.append(navigation)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Сохранить в БД", callback_data="admin_event_save")],
            [InlineKeyboardButton(text="⬅️ Назад к фото", callback_data="admin_event_back:photo")],
            [InlineKeyboardButton(text="✖️ Отмена", callback_data="admin_event_cancel")],
        ]
    )


def parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value.strip(), DATE_FORMAT)
    except ValueError:
        return None


def format_date(value: datetime | None) -> str:
    return value.strftime(DATE_FORMAT) if value else "—"


def preview_text(data: dict) -> str:
    photo_status = "есть" if data.get("photo_file_id") else "нет"
    return (
        "🔎 Проверьте мероприятие перед сохранением\n\n"
        f"🎫 Название: {data.get('name', '—')}\n"
        f"📝 Описание: {data.get('description', '—')}\n"
        f"📍 Адрес: {data.get('address', '—')}\n"
        f"🏢 Аудитория: {data.get('auditorium') or '—'}\n"
        f"🗺 Как добраться: {data.get('route_url') or '—'}\n"
        f"🗓 Начало: {format_date(data.get('start_date'))}\n"
        f"🏁 Окончание: {format_date(data.get('end_date'))}\n"
        f"⏳ Дедлайн регистрации: {format_date(data.get('deadline'))}\n"
        f"🖼 Фото: {photo_status}"
    )


async def safe_delete(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


async def edit_wizard(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    data = await state.get_data()
    message_id = data.get("admin_wizard_message_id")

    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return
        except TelegramBadRequest:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=message_id)
            except TelegramBadRequest:
                pass

    sent = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
    await state.update_data(admin_wizard_message_id=sent.message_id)


async def prompt_after_message(
    message: Message,
    bot: Bot,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    await safe_delete(message)
    await edit_wizard(bot, message.chat.id, state, text, reply_markup)


async def callback_wizard(
    callback: CallbackQuery,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    sent = await replace_callback_with_text(callback, text, reply_markup=reply_markup)
    if sent is not None:
        await state.update_data(admin_wizard_message_id=sent.message_id)


async def show_step(callback: CallbackQuery, state: FSMContext, step: str) -> None:
    await safe_callback_answer(callback)

    if step == "name":
        await state.set_state(EventCreate.name)
        text = "➕ Новое мероприятие\n\nВведите название.\nНапример: Startup Meetup #5"
        keyboard = wizard_keyboard()
    elif step == "description":
        await state.set_state(EventCreate.description)
        text = "Введите описание мероприятия.\nНапример: Встреча с основателями стартапов и нетворкинг."
        keyboard = wizard_keyboard("name")
    elif step == "address":
        await state.set_state(EventCreate.address)
        text = "Введите адрес проведения.\nНапример: проспект Вернадского, 78"
        keyboard = wizard_keyboard("description")
    elif step == "auditorium":
        await state.set_state(EventCreate.auditorium)
        text = "Введите аудиторию / помещение.\nНапример: А-11 или Актовый зал"
        keyboard = wizard_keyboard("address")
    elif step == "route_url":
        await state.set_state(EventCreate.route_url)
        text = "Вставьте ссылку «Как добраться».\nНапример: https://yandex.ru/maps/...\nЕсли ссылки нет, отправьте -"
        keyboard = wizard_keyboard("auditorium")
    elif step == "start_date":
        await state.set_state(EventCreate.start_date)
        text = "Введите дату и время начала.\nНапример: 26.09.2026 16:00"
        keyboard = wizard_keyboard("route_url")
    elif step == "end_date":
        await state.set_state(EventCreate.end_date)
        text = "Введите дату и время окончания.\nНапример: 26.09.2026 18:00"
        keyboard = wizard_keyboard("start_date")
    elif step == "deadline":
        await state.set_state(EventCreate.deadline)
        text = "Введите дедлайн регистрации.\nНапример: 26.09.2026 12:00"
        keyboard = wizard_keyboard("end_date")
    elif step == "photo":
        await state.set_state(EventCreate.photo)
        text = "Отправьте фото мероприятия одним изображением или нажмите «Без фото»."
        keyboard = wizard_keyboard("deadline", photo_step=True)
    else:
        return

    await callback_wizard(callback, state, text, keyboard)


async def show_preview_from_message(message: Message, bot: Bot, state: FSMContext) -> None:
    await safe_delete(message)
    data = await state.get_data()
    await state.set_state(EventCreate.confirm)

    photo_file_id = data.get("photo_file_id")
    if not photo_file_id:
        await edit_wizard(bot, message.chat.id, state, preview_text(data), confirm_keyboard())
        return

    old_message_id = data.get("admin_wizard_message_id")
    if old_message_id:
        try:
            await bot.delete_message(message.chat.id, old_message_id)
        except TelegramBadRequest:
            pass

    caption = preview_text(data)
    if len(caption) > 1024:
        caption = caption[:1020].rstrip() + "…"

    sent = await bot.send_photo(
        chat_id=message.chat.id,
        photo=photo_file_id,
        caption=caption,
        reply_markup=confirm_keyboard(),
    )
    await state.update_data(admin_wizard_message_id=sent.message_id)


async def show_preview_from_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    data = await state.get_data()
    await state.set_state(EventCreate.confirm)
    await callback_wizard(callback, state, preview_text(data), confirm_keyboard())


async def reject_non_admin_message(message: Message) -> None:
    await message.answer("⛔ У вас нет доступа к админ-панели.")


@router.message(Command("myid"))
async def my_id_command(message: Message):
    if not message.from_user:
        return
    await message.answer(f"Ваш Telegram ID: <code>{message.from_user.id}</code>", parse_mode="HTML")


@router.message(Command("admin"))
async def admin_command(message: Message, state: FSMContext):
    if not message.from_user:
        return
    if not is_admin(message.from_user.id):
        await reject_non_admin_message(message)
        return

    await state.clear()
    await message.answer("🛠 Админ-панель", reply_markup=admin_menu_keyboard())


@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await safe_callback_answer(callback, "Нет доступа", show_alert=True)
        return

    await safe_callback_answer(callback)

    await state.clear()
    await callback_wizard(callback, state, "🛠 Админ-панель", admin_menu_keyboard())


@router.callback_query(F.data == "admin_event_create")
async def create_event_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await safe_callback_answer(callback, "Нет доступа", show_alert=True)
        return

    await safe_callback_answer(callback)

    await state.clear()
    await state.update_data(admin_wizard_message_id=callback.message.message_id)
    await state.set_state(EventCreate.name)
    await callback_wizard(
        callback,
        state,
        "➕ Новое мероприятие\n\nВведите название.\nНапример: Startup Meetup #5",
        wizard_keyboard(),
    )


@router.callback_query(F.data == "admin_event_cancel")
async def cancel_event_create(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await safe_callback_answer(callback, "Нет доступа", show_alert=True)
        return

    await safe_callback_answer(callback)

    await state.clear()
    await callback_wizard(callback, state, "🛠 Создание мероприятия отменено.", admin_menu_keyboard())


@router.callback_query(F.data.startswith("admin_event_back:"))
async def event_back(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await safe_callback_answer(callback, "Нет доступа", show_alert=True)
        return

    target = callback.data.split(":", 1)[1]
    await show_step(callback, state, target)


@router.message(EventCreate.name)
async def event_name(message: Message, bot: Bot, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    value = (message.text or "").strip()
    if not value:
        await prompt_after_message(message, bot, state, "Название не может быть пустым. Введите название:", wizard_keyboard())
        return
    if len(value) > 200:
        await prompt_after_message(message, bot, state, "Название слишком длинное. Максимум 200 символов:", wizard_keyboard())
        return

    await state.update_data(name=value)
    await state.set_state(EventCreate.description)
    await prompt_after_message(message, bot, state, "Введите описание мероприятия.\nНапример: Встреча с основателями стартапов и нетворкинг.", wizard_keyboard("name"))


@router.message(EventCreate.description)
async def event_description(message: Message, bot: Bot, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    value = (message.text or "").strip()
    if not value:
        await prompt_after_message(message, bot, state, "Описание не может быть пустым. Введите описание:", wizard_keyboard("name"))
        return
    if len(value) > 3000:
        await prompt_after_message(message, bot, state, "Описание слишком длинное. Максимум 3000 символов:", wizard_keyboard("name"))
        return

    await state.update_data(description=value)
    await state.set_state(EventCreate.address)
    await prompt_after_message(message, bot, state, "Введите адрес проведения.\nНапример: проспект Вернадского, 78", wizard_keyboard("description"))


@router.message(EventCreate.address)
async def event_address(message: Message, bot: Bot, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    value = (message.text or "").strip()
    if not value:
        await prompt_after_message(message, bot, state, "Адрес не может быть пустым. Введите адрес:", wizard_keyboard("description"))
        return
    if len(value) > 400:
        await prompt_after_message(message, bot, state, "Адрес слишком длинный. Максимум 400 символов:", wizard_keyboard("description"))
        return

    await state.update_data(address=value)
    await state.set_state(EventCreate.auditorium)
    await prompt_after_message(
        message, bot, state,
        "Введите аудиторию / помещение.\nНапример: А-11 или Актовый зал",
        wizard_keyboard("address"),
    )


@router.message(EventCreate.auditorium)
async def event_auditorium(message: Message, bot: Bot, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    value = (message.text or "").strip()
    if not value:
        await prompt_after_message(message, bot, state, "Введите аудиторию.\nНапример: А-11", wizard_keyboard("address"))
        return
    await state.update_data(auditorium=value)
    await state.set_state(EventCreate.route_url)
    await prompt_after_message(
        message, bot, state,
        "Вставьте ссылку «Как добраться».\nНапример: https://yandex.ru/maps/...\nЕсли ссылки нет, отправьте -",
        wizard_keyboard("auditorium"),
    )


@router.message(EventCreate.route_url)
async def event_route_url(message: Message, bot: Bot, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    value = (message.text or "").strip()
    if not value:
        await prompt_after_message(message, bot, state, "Введите ссылку или -", wizard_keyboard("auditorium"))
        return
    route_url = None if value == "-" else value
    if route_url and not route_url.startswith(("http://", "https://")):
        await prompt_after_message(message, bot, state, "Ссылка должна начинаться с http:// или https://.\nНапример: https://yandex.ru/maps/...", wizard_keyboard("auditorium"))
        return
    await state.update_data(route_url=route_url)
    await state.set_state(EventCreate.start_date)
    await prompt_after_message(
        message, bot, state,
        "Введите дату и время начала.\nНапример: 26.09.2026 16:00",
        wizard_keyboard("route_url"),
    )


@router.message(EventCreate.start_date)
async def event_start_date(message: Message, bot: Bot, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    value = parse_date(message.text or "")
    if value is None:
        await prompt_after_message(
            message, bot, state,
            "Неверный формат. Введите начало так: 26.09.2026 16:00",
            wizard_keyboard("route_url"),
        )
        return

    now = datetime.now(MOSCOW).replace(tzinfo=None)
    if value <= now:
        await prompt_after_message(
            message, bot, state,
            "Начало мероприятия должно быть в будущем. Введите дату ещё раз:",
            wizard_keyboard("route_url"),
        )
        return

    await state.update_data(start_date=value)
    await state.set_state(EventCreate.end_date)
    await prompt_after_message(
        message, bot, state,
        "Введите дату и время окончания.\nНапример: 26.09.2026 18:00",
        wizard_keyboard("start_date"),
    )


@router.message(EventCreate.end_date)
async def event_end_date(message: Message, bot: Bot, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    value = parse_date(message.text or "")
    data = await state.get_data()
    start_date = data.get("start_date")

    if value is None:
        await prompt_after_message(
            message, bot, state,
            "Неверный формат. Введите окончание так: 26.09.2026 18:00",
            wizard_keyboard("start_date"),
        )
        return
    if start_date and value <= start_date:
        await prompt_after_message(
            message, bot, state,
            "Окончание должно быть позже начала. Введите дату ещё раз:",
            wizard_keyboard("start_date"),
        )
        return

    await state.update_data(end_date=value)
    await state.set_state(EventCreate.deadline)
    await prompt_after_message(
        message, bot, state,
        "Введите дедлайн регистрации.\nНапример: 26.09.2026 12:00",
        wizard_keyboard("end_date"),
    )


@router.message(EventCreate.deadline)
async def event_deadline(message: Message, bot: Bot, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    value = parse_date(message.text or "")
    data = await state.get_data()
    start_date = data.get("start_date")

    if value is None:
        await prompt_after_message(
            message, bot, state,
            "Неверный формат. Введите дедлайн так: 26.09.2026 12:00",
            wizard_keyboard("end_date"),
        )
        return
    if start_date and value > start_date:
        await prompt_after_message(
            message, bot, state,
            "Дедлайн регистрации не может быть позже начала мероприятия. Введите ещё раз:",
            wizard_keyboard("end_date"),
        )
        return

    await state.update_data(deadline=value)
    await state.set_state(EventCreate.photo)
    await prompt_after_message(
        message, bot, state,
        "Отправьте фото мероприятия одним изображением или нажмите «Без фото».",
        wizard_keyboard("deadline", photo_step=True),
    )


@router.message(EventCreate.photo, F.photo)
async def event_photo(message: Message, bot: Bot, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return

    await state.update_data(photo_file_id=message.photo[-1].file_id)
    await show_preview_from_message(message, bot, state)


@router.message(EventCreate.photo)
async def event_photo_invalid(message: Message, bot: Bot, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    await prompt_after_message(
        message, bot, state,
        "Нужно отправить именно фото или нажать «Без фото».",
        wizard_keyboard("deadline", photo_step=True),
    )


@router.callback_query(EventCreate.photo, F.data == "admin_event_photo_skip")
async def event_photo_skip(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await safe_callback_answer(callback, "Нет доступа", show_alert=True)
        return

    await state.update_data(photo_file_id=None)
    await show_preview_from_callback(callback, state)


@router.callback_query(EventCreate.confirm, F.data == "admin_event_save")
async def event_save(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await safe_callback_answer(callback, "Нет доступа", show_alert=True)
        return

    await safe_callback_answer(callback)

    data = await state.get_data()
    try:
        event = await repository.create_event(
            name=data["name"],
            description=data["description"],
            address=data["address"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            deadline=data["deadline"],
            photo_file_id=data.get("photo_file_id"),
            auditorium=data.get("auditorium"),
            route_url=data.get("route_url"),
        )
    except Exception as error:
        print("Admin event create failed:", repr(error))
        await callback_wizard(
            callback,
            state,
            "⚠️ Не удалось сохранить мероприятие в БД. Попробуйте ещё раз.",
            confirm_keyboard(),
        )
        return

    await state.clear()
    await callback_wizard(
        callback,
        state,
        f"✅ Мероприятие сохранено в БД.\n\nID: {event['id']}\n🎫 {event['name']}\n\n"
        "Оно уже доступно пользователям в разделе «Мероприятия».",
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Получить QR для отметки", callback_data=f"admin_event_qr:{event['id']}")],
            [InlineKeyboardButton(text="🟢 Открыть check-in", callback_data=f"admin_checkin_open:{event['id']}")],
            [InlineKeyboardButton(text="⬅️ Админ-панель", callback_data="admin_menu")],
        ]),
    )


@router.callback_query(F.data == "admin_events_list")
async def admin_events_list(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await safe_callback_answer(callback, "Нет доступа", show_alert=True)
        return

    await safe_callback_answer(callback)

    await state.clear()
    events = await repository.get_admin_events(limit=20)

    if not events:
        text = "📋 В БД пока нет мероприятий."
    else:
        lines = ["📋 Последние мероприятия в БД:", ""]
        for event in events:
            lines.append(
                f"#{event['id']} — {event['name'][:70]}\n"
                f"   {format_date(event.get('start_date'))}"
            )
        text = "\n".join(lines)

    rows = []
    for event in events[:10]:
        rows.append([
            InlineKeyboardButton(
                text=f"🛠 #{event['id']} {event['name'][:32]}",
                callback_data=f"admin_event_manage:{event['id']}",
            )
        ])
    rows.extend([
        [InlineKeyboardButton(text="➕ Создать мероприятие", callback_data="admin_event_create")],
        [InlineKeyboardButton(text="⬅️ Админ-панель", callback_data="admin_menu")],
    ])
    keyboard = InlineKeyboardMarkup(inline_keyboard=rows)
    await callback_wizard(callback, state, text, keyboard)
