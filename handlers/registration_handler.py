from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from main_menu.keyboard import main_menu_keyboard
from placeholders import runtime_repository as repository
from university_matcher import find_best_universities, string_normalise

router = Router()


class Registration(StatesGroup):
    consent = State()
    surname = State()
    name = State()
    patronymic = State()
    university = State()
    other_university = State()
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
        return user is not None
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
    await state.clear()
    await state.update_data(
        wizard_message_id=callback.message.message_id,
        editing=True,
    )
    await state.set_state(Registration.surname)
    await callback.message.edit_text(
        "✏️ Редактирование профиля\n\nВведите вашу фамилию:",
        reply_markup=_nav_keyboard(),
    )
    await callback.answer()


async def _show_step(callback: CallbackQuery, state: FSMContext, step: str) -> None:
    data = await state.get_data()

    if step == "surname":
        await state.set_state(Registration.surname)
        text = "Введите вашу фамилию:"
        keyboard = _nav_keyboard()
    elif step == "name":
        await state.set_state(Registration.name)
        text = "Введите ваше имя:"
        keyboard = _nav_keyboard("surname")
    elif step == "patronymic":
        await state.set_state(Registration.patronymic)
        text = "Введите ваше отчество:"
        keyboard = _nav_keyboard("name")
    elif step == "university":
        await state.set_state(Registration.university)
        text = "Из какого ты вуза?"
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
        text = "Какой у тебя институт?"
        keyboard = _nav_keyboard("course")
    elif step == "direction":
        await state.set_state(Registration.direction)
        back_to = "institute" if data.get("is_mirea") else "course"
        text = "Какое у тебя направление?"
        keyboard = _nav_keyboard(back_to)
    elif step == "direction_code":
        await state.set_state(Registration.direction_code)
        text = "Какой код у твоего направления?"
        keyboard = _nav_keyboard("direction")
    elif step == "group":
        await state.set_state(Registration.group)
        text = "Какой номер у твоей группы?"
        keyboard = _nav_keyboard("direction_code")
    else:
        await callback.answer()
        return

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


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
async def start_handler(message: Message, state: FSMContext):
    if not message.from_user:
        return

    if await is_user_registered(message.from_user.id):
        await state.clear()
        await message.answer(
            "🏠 Главное меню",
            reply_markup=main_menu_keyboard(),
        )
        return

    await show_consent(message, state)


@router.callback_query(F.data == "edit_profile")
async def edit_profile(callback: CallbackQuery, state: FSMContext):
    await _start_profile_edit(callback, state)


@router.callback_query(F.data == "form_cancel")
async def cancel_form(callback: CallbackQuery, state: FSMContext):
    user = await repository.find_user(callback.from_user.id)
    await state.clear()

    if user is not None:
        await callback.message.edit_text(
            "🏠 Главное меню",
            reply_markup=main_menu_keyboard(),
        )
    else:
        await callback.message.edit_text(
            "Регистрация отменена. Чтобы начать заново, отправьте /start."
        )
    await callback.answer()


@router.callback_query(F.data.startswith("form_back:"))
async def form_back(callback: CallbackQuery, state: FSMContext):
    target = callback.data.split(":", 1)[1]
    await _show_step(callback, state, target)


@router.callback_query(Registration.consent, F.data == "consent_accept")
async def accept_consent(callback: CallbackQuery, state: FSMContext):
    await state.set_state(Registration.surname)
    await callback.message.edit_text(
        "Введите вашу фамилию:",
        reply_markup=_nav_keyboard(),
    )
    await callback.answer()


@router.message(Registration.surname)
async def process_surname(message: Message, bot: Bot, state: FSMContext):
    if not message.text:
        await _prompt_after_text(message, bot, state, "Пожалуйста, введите фамилию:", _nav_keyboard())
        return

    await state.update_data(surname=message.text.strip())
    await state.set_state(Registration.name)
    await _prompt_after_text(message, bot, state, "Введите ваше имя:", _nav_keyboard("surname"))


@router.message(Registration.name)
async def process_name(message: Message, bot: Bot, state: FSMContext):
    if not message.text:
        await _prompt_after_text(message, bot, state, "Пожалуйста, введите имя:", _nav_keyboard("surname"))
        return

    await state.update_data(name=message.text.strip())
    await state.set_state(Registration.patronymic)
    await _prompt_after_text(message, bot, state, "Введите ваше отчество:", _nav_keyboard("name"))


@router.message(Registration.patronymic)
async def process_patronymic(message: Message, bot: Bot, state: FSMContext):
    if not message.text:
        await _prompt_after_text(message, bot, state, "Пожалуйста, введите отчество:", _nav_keyboard("name"))
        return

    await state.update_data(patronymic=message.text.strip())
    await state.set_state(Registration.university)
    await _prompt_after_text(message, bot, state, "Из какого ты вуза?", get_university_keyboard())


@router.callback_query(
    Registration.university,
    F.data.in_({"university_mirea", "university_other"}),
)
async def process_university(callback: CallbackQuery, state: FSMContext):
    if callback.data == "university_mirea":
        universities = await repository.get_universities()
        mirea = next((item for item in universities if _is_mirea(item)), None)
        if mirea is None:
            await callback.answer("МИРЭА не найден в базе", show_alert=True)
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
        await _edit_wizard(
            bot,
            message.chat.id,
            state,
            "Не удалось найти такой вуз. Попробуйте ввести название ещё раз:",
            _nav_keyboard("university"),
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
    university_id = int(callback.data.split(":", 1)[1])
    university = await repository.get_university(university_id)
    if university is None:
        await callback.answer("Вуз не найден", show_alert=True)
        return

    await _save_selected_university(state, university)
    await state.set_state(Registration.course)
    await callback.message.edit_text(
        f"✅ Выбран: {university['name']}\n\nКакой у тебя курс?",
        reply_markup=get_course_keyboard(),
    )
    await callback.answer()


@router.callback_query(
    Registration.course,
    F.data.in_({"course_1", "course_2", "course_3", "course_4", "course_magistracy"}),
)
async def process_course(callback: CallbackQuery, state: FSMContext):
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
    await _prompt_after_text(message, bot, state, "Какое у тебя направление?", _nav_keyboard("institute"))


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
    await _prompt_after_text(message, bot, state, "Какой код у твоего направления?", _nav_keyboard("direction"))


@router.message(Registration.direction_code)
async def process_direction_code(message: Message, bot: Bot, state: FSMContext):
    if not message.text:
        await _prompt_after_text(message, bot, state, "Пожалуйста, введите код направления:", _nav_keyboard("direction"))
        return

    await state.update_data(direction_code=message.text.strip())
    await state.set_state(Registration.group)
    await _prompt_after_text(message, bot, state, "Какой номер у твоей группы?", _nav_keyboard("direction_code"))


@router.message(Registration.group)
async def process_group(message: Message, bot: Bot, state: FSMContext):
    if not message.text:
        await _prompt_after_text(message, bot, state, "Пожалуйста, введите номер группы:", _nav_keyboard("direction_code"))
        return

    await state.update_data(group=message.text.strip())
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
