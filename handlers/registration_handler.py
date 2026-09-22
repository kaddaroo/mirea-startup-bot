import re

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from config import COINS_PER_ATTENDANCE
from main_menu.keyboard import main_menu_keyboard
from placeholders import runtime_repository as repository
from university_matcher import find_best_universities, string_normalise

from ui_helpers import safe_callback_answer, safe_edit_callback_text

router = Router()


class Registration(StatesGroup):
    consent = State()
    surname = State()
    name = State()
    patronymic = State()
    university = State()
    other_university = State()
    confirm_custom_university = State()
    course = State()
    institute = State()
    direction = State()
    direction_code = State()
    group = State()


async def is_user_registered(telegram_id: int) -> bool:
    return await repository.find_user(telegram_id) is not None


def _nav_keyboard(back_to: str | None = None) -> InlineKeyboardMarkup:
    row = []
    if back_to:
        row.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=f"form_back:{back_to}",
            )
        )
    row.append(
        InlineKeyboardButton(
            text="✖️ Отмена",
            callback_data="form_cancel",
        )
    )
    return InlineKeyboardMarkup(inline_keyboard=[row])


def get_consent_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Я согласен с обработкой ПДн",
                    callback_data="consent_accept",
                )
            ],
            [
                InlineKeyboardButton(
                    text="✖️ Отмена",
                    callback_data="form_cancel",
                )
            ],
        ]
    )


def get_university_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="РТУ МИРЭА",
                    callback_data="university_mirea",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Другой вуз",
                    callback_data="university_other",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="form_back:patronymic",
                ),
                InlineKeyboardButton(
                    text="✖️ Отмена",
                    callback_data="form_cancel",
                ),
            ],
        ]
    )


def get_course_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="course_1"),
                InlineKeyboardButton(text="2", callback_data="course_2"),
                InlineKeyboardButton(text="3", callback_data="course_3"),
                InlineKeyboardButton(text="4", callback_data="course_4"),
            ],
            [
                InlineKeyboardButton(
                    text="Магистратура",
                    callback_data="course_magistracy",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data="form_back:university",
                ),
                InlineKeyboardButton(
                    text="✖️ Отмена",
                    callback_data="form_cancel",
                ),
            ],
        ]
    )


def _normalise_name_part(value: str) -> str | None:
    value = value.strip()

    if not value:
        return None

    parts = value.split("-")
    if any(not part or not part.isalpha() for part in parts):
        return None

    return "-".join(part[0].upper() + part[1:].lower() for part in parts)


def _is_mirea(university: dict) -> bool:
    name = string_normalise(str(university.get("name") or ""))
    short_name = string_normalise(str(university.get("short_name") or ""))
    tokens = set(name.split()) | set(short_name.split())
    return "мирэа" in tokens


async def _save_selected_university(state: FSMContext, university: dict) -> None:
    await state.update_data(
        university=university["name"],
        university_id=university["id"],
        is_mirea=_is_mirea(university),
    )


async def _safe_delete_user_message(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        pass


async def _edit_wizard(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    data = await state.get_data()
    message_id = data.get("wizard_message_id")

    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return
        except TelegramBadRequest as error:
            if "message is not modified" in str(error).lower():
                return

    sent = await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
    )
    await state.update_data(wizard_message_id=sent.message_id)


async def _prompt_after_text(
    message: Message,
    bot: Bot,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    await _safe_delete_user_message(message)
    await _edit_wizard(
        bot=bot,
        chat_id=message.chat.id,
        state=state,
        text=text,
        reply_markup=reply_markup,
    )


async def save_user_profile(message: Message, data: dict) -> bool:
    if not message.from_user:
        return False

    university_id = data.get("university_id")
    if university_id is None:
        return False

    try:
        user = await repository.update_user(
            message.from_user.id,
            surname=data.get("surname"),
            name=data.get("name"),
            patronymic=data.get("patronymic"),
            id_university=university_id,
            institute=data.get("institute"),
            direction_code=data.get("direction_code"),
            group_name=data.get("group"),
        )
        if user is not None:
            await repository.mark_lead_completed(message.from_user.id)
            return True
        return False
    except Exception as error:
        print("Failed to save user registration:", repr(error))
        return False


async def show_consent(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(Registration.consent)
    sent = await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Для продолжения регистрации необходимо дать согласие "
        "на обработку персональных данных.",
        reply_markup=get_consent_keyboard(),
    )
    await state.update_data(
        wizard_message_id=sent.message_id,
        editing=False,
    )


async def _start_profile_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await safe_callback_answer(callback)
    await state.clear()
    await state.update_data(
        wizard_message_id=callback.message.message_id,
        editing=True,
    )
    await state.set_state(Registration.surname)
    await safe_edit_callback_text(callback, 
        "✏️ Редактирование профиля\n\nВведите вашу фамилию.\nНапример: Иванов",
        reply_markup=_nav_keyboard(),
    )


async def _show_step(callback: CallbackQuery, state: FSMContext, step: str) -> None:
    data = await state.get_data()

    if step == "surname":
        await state.set_state(Registration.surname)
        text = "Введите вашу фамилию.\nНапример: Иванов"
        keyboard = _nav_keyboard()
    elif step == "name":
        await state.set_state(Registration.name)
        text = "Введите ваше имя.\nНапример: Иван"
        keyboard = _nav_keyboard("surname")
    elif step == "patronymic":
        await state.set_state(Registration.patronymic)
        text = "Введите ваше отчество.\nНапример: Иванович"
        keyboard = _nav_keyboard("name")
    elif step == "university":
        await state.set_state(Registration.university)
        text = "Из какого ты вуза?\nНапример: РТУ МИРЭА"
        keyboard = get_university_keyboard()
    elif step == "other_university":
        await state.set_state(Registration.other_university)
        text = "Введите название вуза. Можно коротко: МГУ, МГТУ, МИРЭА."
        keyboard = _nav_keyboard("university")
    elif step == "course":
        await state.set_state(Registration.course)
        text = "Какой у тебя курс?"
        keyboard = get_course_keyboard()
    elif step == "institute":
        await state.set_state(Registration.institute)
        text = "Введите название института.\nНапример: ИПТИП"
        keyboard = _nav_keyboard("course")
    elif step == "direction":
        await state.set_state(Registration.direction)
        back_to = "institute" if data.get("is_mirea") else "course"
        text = "Введите название направления.\nНапример: Информатика и вычислительная техника"
        keyboard = _nav_keyboard(back_to)
    elif step == "direction_code":
        await state.set_state(Registration.direction_code)
        text = "Введите код направления.\nНапример: 09.03.02"
        keyboard = _nav_keyboard("direction")
    elif step == "group":
        await state.set_state(Registration.group)
        text = "Введите наименование группы.\nНапример: ЭФБО-02-26"
        keyboard = _nav_keyboard("direction_code")
    else:
        return

    await safe_edit_callback_text(callback, text, reply_markup=keyboard)


async def _finish_form(
    message: Message,
    bot: Bot,
    state: FSMContext,
    data: dict,
) -> None:
    editing = bool(data.get("editing"))
    title = "✅ Профиль обновлён!" if editing else "✅ Регистрация завершена!"

    lines = [
        title,
        "",
        f"Фамилия: {data.get('surname', '—')}",
        f"Имя: {data.get('name', '—')}",
        f"Отчество: {data.get('patronymic', '—')}",
        f"Вуз: {data.get('university', '—')}",
        f"Курс: {data.get('course', '—')}",
    ]
    if data.get("institute"):
        lines.append(f"Институт: {data['institute']}")
    if data.get("direction"):
        lines.append(f"Направление: {data['direction']}")
    if data.get("direction_code"):
        lines.append(f"Код направления: {data['direction_code']}")
    if data.get("group"):
        lines.append(f"Группа: {data['group']}")

    await _safe_delete_user_message(message)
    await _edit_wizard(
        bot=bot,
        chat_id=message.chat.id,
        state=state,
        text="\n".join(lines),
        reply_markup=main_menu_keyboard(),
    )
    await state.clear()


@router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, command: CommandObject):
    if not message.from_user:
        return

    user_id = message.from_user.id
    await repository.upsert_lead(
        user_id,
        message.from_user.username,
        message.from_user.first_name,
        last_step="start",
    )

    payload = (command.args or "").strip()

    if payload.startswith("checkin_"):
        token = payload[len("checkin_"):]
        result = await repository.checkin_by_token(user_id, token, COINS_PER_ATTENDANCE)
        status = result.get("status")
        event = result.get("event") or {}
        if status == "ok":
            await message.answer(
                f"✅ Посещение «{event.get('name', 'мероприятия')}» отмечено!\n"
                f"🪙 Начислено {COINS_PER_ATTENDANCE} коина."
            )
        elif status == "already":
            await message.answer("✅ Вы уже отметились на этом мероприятии.")
        elif status == "closed":
            await message.answer("🔒 Отметка посещения сейчас закрыта. Покажите QR администратору мероприятия.")
        elif status == "not_registered_event":
            await message.answer("Вы не были зарегистрированы на это мероприятие, поэтому отметить посещение через этот QR нельзя.")
        elif status == "not_registered_bot":
            await message.answer("Сначала нужно завершить регистрацию в боте.")
            await show_consent(message, state)
        else:
            await message.answer("QR-код недействителен или устарел.")
        return

    marketing_link = None
    if payload.startswith("m_"):
        token = payload[len("m_"):]
        marketing_link = await repository.record_marketing_visit(user_id, token)
        if marketing_link:
            await repository.upsert_lead(
                user_id, message.from_user.username, message.from_user.first_name,
                last_step="start", marketing_link_id=marketing_link["id"]
            )

    if await is_user_registered(user_id):
        await repository.mark_lead_completed(user_id)
        await state.clear()
        if marketing_link and marketing_link.get("event_id"):
            await message.answer(
                "👋 Вы перешли по ссылке мероприятия.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="🎫 Открыть мероприятие",
                        callback_data=f"event:{marketing_link['event_id']}",
                    )
                ]]),
            )
        else:
            await message.answer("🏠 Главное меню", reply_markup=main_menu_keyboard())
        return

    await show_consent(message, state)


@router.callback_query(F.data == "continue_registration")
async def continue_registration(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)
    if await is_user_registered(callback.from_user.id):
        await state.clear()
        await safe_edit_callback_text(callback, "🏠 Главное меню", reply_markup=main_menu_keyboard())
        return
    await state.clear()
    await state.set_state(Registration.consent)
    await state.update_data(wizard_message_id=callback.message.message_id, editing=False)
    await safe_edit_callback_text(callback, 
        "👋 Продолжим регистрацию.\n\nДля начала подтвердите согласие на обработку персональных данных.",
        reply_markup=get_consent_keyboard(),
    )


@router.callback_query(F.data == "edit_profile")
async def edit_profile(callback: CallbackQuery, state: FSMContext):
    await _start_profile_edit(callback, state)


@router.callback_query(F.data == "form_cancel")
async def cancel_form(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)
    user = await repository.find_user(callback.from_user.id)
    await state.clear()

    if user is not None:
        await safe_edit_callback_text(callback, 
            "🏠 Главное меню",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await safe_edit_callback_text(callback, 
            "Регистрация отменена. Чтобы начать заново, отправьте /start."
        )


@router.callback_query(F.data.startswith("form_back:"))
async def form_back(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)
    target = callback.data.split(":", 1)[1]
    await _show_step(callback, state, target)


@router.callback_query(Registration.consent, F.data == "consent_accept")
async def accept_consent(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)
    await state.set_state(Registration.surname)
    await safe_edit_callback_text(callback, 
        "Введите вашу фамилию.\nНапример: Иванов",
        reply_markup=_nav_keyboard(),
    )


@router.message(Registration.surname)
async def process_surname(message: Message, bot: Bot, state: FSMContext):
    surname = _normalise_name_part(message.text or "")
    if surname is None:
        await _prompt_after_text(
            message,
            bot,
            state,
            "Введите фамилию только буквами.\nНапример: Иванов",
            _nav_keyboard(),
        )
        return

    await state.update_data(surname=surname)
    await state.set_state(Registration.name)
    await _prompt_after_text(message, bot, state, "Введите ваше имя.\nНапример: Иван", _nav_keyboard("surname"))


@router.message(Registration.name)
async def process_name(message: Message, bot: Bot, state: FSMContext):
    name = _normalise_name_part(message.text or "")
    if name is None:
        await _prompt_after_text(
            message,
            bot,
            state,
            "Введите имя только буквами.\nНапример: Тимур",
            _nav_keyboard("surname"),
        )
        return

    await state.update_data(name=name)
    await state.set_state(Registration.patronymic)
    await _prompt_after_text(message, bot, state, "Введите ваше отчество.\nНапример: Иванович", _nav_keyboard("name"))


@router.message(Registration.patronymic)
async def process_patronymic(message: Message, bot: Bot, state: FSMContext):
    patronymic = _normalise_name_part(message.text or "")
    if patronymic is None:
        await _prompt_after_text(
            message,
            bot,
            state,
            "Введите отчество только буквами.\nНапример: Айдарович",
            _nav_keyboard("name"),
        )
        return

    await state.update_data(patronymic=patronymic)
    await state.set_state(Registration.university)
    await _prompt_after_text(message, bot, state, "Из какого ты вуза?\nНапример: РТУ МИРЭА", get_university_keyboard())


@router.callback_query(
    Registration.university,
    F.data.in_({"university_mirea", "university_other"}),
)
async def process_university(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)

    if callback.data == "university_mirea":
        universities = await repository.get_universities()
        mirea = next((item for item in universities if _is_mirea(item)), None)
        if mirea is None:
            await safe_edit_callback_text(
                callback,
                "⚠️ МИРЭА не найден в базе. Попробуйте позже.",
                reply_markup=get_university_keyboard(),
            )
            return

        await _save_selected_university(state, mirea)
        await _show_step(callback, state, "course")
        return

    await _show_step(callback, state, "other_university")


@router.message(Registration.other_university)
async def process_other_university(message: Message, bot: Bot, state: FSMContext):
    if not message.text:
        await _prompt_after_text(
            message,
            bot,
            state,
            "Пожалуйста, введите название вуза:",
            _nav_keyboard("university"),
        )
        return

    query = message.text.strip()
    universities = await repository.get_universities()
    result = find_best_universities(query, universities)
    await _safe_delete_user_message(message)

    if result["status"] == "not_found":
        await state.update_data(pending_university=query)
        await state.set_state(Registration.confirm_custom_university)
        await _edit_wizard(
            bot,
            message.chat.id,
            state,
            f"Я не нашёл «{query}» в справочнике.\n\n"
            "Если название введено правильно, можно продолжить регистрацию.",
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="✅ Всё верно",
                            callback_data="custom_university_confirm",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="✏️ Ввести заново",
                            callback_data="custom_university_retry",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="✖️ Отмена",
                            callback_data="form_cancel",
                        )
                    ],
                ]
            ),
        )
        return

    if result["status"] == "found":
        university = result["candidates"][0]
        await _save_selected_university(state, university)
        await state.set_state(Registration.course)
        await _edit_wizard(
            bot,
            message.chat.id,
            state,
            f"✅ Нашёл: {university['name']}\n\nКакой у тебя курс?",
            get_course_keyboard(),
        )
        return

    buttons = [
        [
            InlineKeyboardButton(
                text=candidate.get("short_name") or candidate["name"],
                callback_data=f"university_pick:{candidate['id']}",
            )
        ]
        for candidate in result["candidates"]
    ]
    buttons.append(
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data="form_back:university"),
            InlineKeyboardButton(text="✖️ Отмена", callback_data="form_cancel"),
        ]
    )
    await _edit_wizard(
        bot,
        message.chat.id,
        state,
        "Я нашёл несколько похожих вузов. Выберите нужный:",
        InlineKeyboardMarkup(inline_keyboard=buttons),
    )


@router.callback_query(
    Registration.other_university,
    F.data.startswith("university_pick:"),
)
async def pick_university(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)
    university_id = int(callback.data.split(":", 1)[1])
    university = await repository.get_university(university_id)
    if university is None:
        await safe_edit_callback_text(
            callback,
            "⚠️ Вуз не найден. Выберите вуз ещё раз.",
            reply_markup=get_university_keyboard(),
        )
        return

    await _save_selected_university(state, university)
    await state.set_state(Registration.course)
    await safe_edit_callback_text(callback, 
        f"✅ Выбран: {university['name']}\n\nКакой у тебя курс?",
        reply_markup=get_course_keyboard(),
    )


@router.callback_query(
    Registration.confirm_custom_university,
    F.data == "custom_university_confirm",
)
async def confirm_custom_university(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)
    data = await state.get_data()
    name = data.get("pending_university")

    if not name:
        await safe_edit_callback_text(
            callback,
            "⚠️ Название вуза потеряно. Введите его ещё раз.",
            reply_markup=_nav_keyboard("university"),
        )
        await state.set_state(Registration.other_university)
        return

    university = await repository.create_university(name)
    await _save_selected_university(state, university)
    await _show_step(callback, state, "course")


@router.callback_query(
    Registration.confirm_custom_university,
    F.data == "custom_university_retry",
)
async def retry_custom_university(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)
    await _show_step(callback, state, "other_university")


@router.callback_query(
    Registration.course,
    F.data.in_({"course_1", "course_2", "course_3", "course_4", "course_magistracy"}),
)
async def process_course(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)
    course_labels = {
        "course_1": "1",
        "course_2": "2",
        "course_3": "3",
        "course_4": "4",
        "course_magistracy": "Магистратура",
    }
    await state.update_data(course=course_labels[callback.data])
    data = await state.get_data()
    await _show_step(callback, state, "institute" if data.get("is_mirea") else "direction")


@router.message(Registration.institute)
async def process_institute(message: Message, bot: Bot, state: FSMContext):
    if not message.text:
        await _prompt_after_text(message, bot, state, "Пожалуйста, введите институт:", _nav_keyboard("course"))
        return

    await state.update_data(institute=message.text.strip())
    await state.set_state(Registration.direction)
    await _prompt_after_text(message, bot, state, "Введите название направления.\nНапример: Информатика и вычислительная техника", _nav_keyboard("institute"))


@router.message(Registration.direction)
async def process_direction(message: Message, bot: Bot, state: FSMContext):
    if not message.text:
        data = await state.get_data()
        back_to = "institute" if data.get("is_mirea") else "course"
        await _prompt_after_text(message, bot, state, "Пожалуйста, введите направление:", _nav_keyboard(back_to))
        return

    await state.update_data(direction=message.text.strip())
    data = await state.get_data()

    if not data.get("is_mirea"):
        if not await save_user_profile(message, data):
            await _prompt_after_text(
                message,
                bot,
                state,
                "Не удалось сохранить профиль. Попробуйте ещё раз позже.",
                _nav_keyboard("course"),
            )
            return
        await _finish_form(message, bot, state, data)
        return

    await state.set_state(Registration.direction_code)
    await _prompt_after_text(message, bot, state, "Введите код направления.\nНапример: 09.03.02", _nav_keyboard("direction"))


@router.message(Registration.direction_code)
async def process_direction_code(message: Message, bot: Bot, state: FSMContext):
    if not message.text:
        await _prompt_after_text(message, bot, state, "Пожалуйста, введите код направления:", _nav_keyboard("direction"))
        return

    value = message.text.strip()
    if not re.fullmatch(r"\d{2}\.\d{2}\.\d{2}", value):
        await _prompt_after_text(
            message, bot, state,
            "Введите код направления в формате 11.11.11.\nНапример: 09.03.02",
            _nav_keyboard("direction"),
        )
        return

    await state.update_data(direction_code=value)
    await state.set_state(Registration.group)
    await _prompt_after_text(message, bot, state, "Введите наименование группы.\nНапример: ЭФБО-02-26", _nav_keyboard("direction_code"))


@router.message(Registration.group)
async def process_group(message: Message, bot: Bot, state: FSMContext):
    if not message.text:
        await _prompt_after_text(message, bot, state, "Пожалуйста, введите номер группы:", _nav_keyboard("direction_code"))
        return

    value = message.text.strip().upper()
    if not re.fullmatch(r"[А-ЯЁA-Z]{2,10}-\d{2}-\d{2}", value):
        await _prompt_after_text(
            message, bot, state,
            "Введите полное наименование группы в формате АААА-11-11.\nНапример: ЭФБО-02-26",
            _nav_keyboard("direction_code"),
        )
        return

    await state.update_data(group=value)
    data = await state.get_data()

    if not await save_user_profile(message, data):
        await _prompt_after_text(
            message,
            bot,
            state,
            "Не удалось сохранить профиль. Попробуйте ещё раз позже.",
            _nav_keyboard("direction_code"),
        )
        return

    await _finish_form(message, bot, state, data)
