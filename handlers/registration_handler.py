from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)


from placeholders import runtime_repository as repository

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
    """Проверяет, зарегистрирован ли пользователь (по наличию профиля).

    Использует текущий репозиторий (in-memory) — работает и при недоступной БД.
    """
    user = await repository.find_user(telegram_id)
    return user is not None


def get_consent_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт inline-клавиатуру с кнопкой согласия
    на обработку персональных данных.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Я согласен с обработкой ПДн",
                    callback_data="consent_accept",
                )
            ]
        ]
    )


def get_university_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт inline-клавиатуру с вариантами вуза.
    """

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
        ]
    )


def get_course_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт inline-клавиатуру с вариантами курса.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="1",
                    callback_data="course_1",
                ),
                InlineKeyboardButton(
                    text="2",
                    callback_data="course_2",
                ),
                InlineKeyboardButton(
                    text="3",
                    callback_data="course_3",
                ),
                InlineKeyboardButton(
                    text="4",
                    callback_data="course_4",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Магистратура",
                    callback_data="course_magistracy",
                )
            ],
        ]
    )


async def show_consent(
    message: Message,
    state: FSMContext,
):
    """
    Показывает пользователю согласие на обработку
    персональных данных и переводит его в состояние consent.
    """

    await state.set_state(Registration.consent)

    await message.answer(
        "👋 Добро пожаловать!\n\n"
        "Для продолжения регистрации необходимо дать "
        "согласие на обработку персональных данных.\n\n"
        "Нажимая кнопку ниже, вы подтверждаете своё "
        "согласие на обработку персональных данных.",
        reply_markup=get_consent_keyboard(),
    )


@router.message(CommandStart())
async def start_handler(
    message: Message,
    state: FSMContext,
):
    """
    Точка входа в регистрацию.

    Возможные варианты:
    /start
    /start event_26sep

    Если пользователь уже зарегистрирован,
    регистрация пропускается.
    """

    if not message.from_user:
        return

    # Получаем параметр Deep Link.
    command_parts = message.text.split(maxsplit=1)

    event_parameter = None

    if len(command_parts) > 1:
        event_parameter = command_parts[1]

    # Сохраняем идентификатор мероприятия,
    # если пользователь пришёл по Deep Link.
    if event_parameter:
        await state.update_data(event=event_parameter)

    # Проверяем, зарегистрирован ли пользователь.
    registered = await is_user_registered(message.from_user.id)

    if registered:
        # Позже здесь будет переход
        # в профиль пользователя.
        await message.answer(
            "Ты уже зарегистрирован."
        )
        return

    await show_consent(message, state)


@router.callback_query(
    Registration.consent,
    F.data == "consent_accept",
)
async def accept_consent(
    callback: CallbackQuery,
    state: FSMContext,
):
    """
    Обрабатывает согласие пользователя
    на обработку персональных данных.
    """

    if not callback.from_user:
        await callback.answer()
        return

    if await repository.find_user(callback.from_user.id) is None:
        try:
            await repository.create_user(callback.from_user.id)
        except Exception:
            await callback.message.answer(
                "Не удалось сохранить пользователя в базу. Попробуйте /start ещё раз."
            )
            await callback.answer()
            return

    await state.set_state(Registration.surname)

    await callback.message.edit_text(
        "✅ Согласие получено.\n\n"
        "Введите вашу фамилию:"
    )

    await callback.answer()


@router.message(Registration.surname)
async def process_surname(
    message: Message,
    state: FSMContext,
):
    """
    Получает фамилию пользователя.
    """

    if not message.text:
        await message.answer(
            "Пожалуйста, введите фамилию."
        )
        return

    await state.update_data(
        surname=message.text.strip()
    )

    await state.set_state(Registration.name)

    await message.answer(
        "Введите ваше имя:"
    )


@router.message(Registration.name)
async def process_name(
    message: Message,
    state: FSMContext,
):
    """
    Получает имя пользователя.
    """

    if not message.text:
        await message.answer(
            "Пожалуйста, введите имя."
        )
        return

    await state.update_data(
        name=message.text.strip()
    )

    await state.set_state(Registration.patronymic)

    await message.answer(
        "Введите ваше отчество:"
    )


@router.message(Registration.patronymic)
async def process_patronymic(
    message: Message,
    state: FSMContext,
):
    """
    Получает отчество пользователя и спрашивает вуз.
    """

    if not message.text:
        await message.answer(
            "Пожалуйста, введите отчество."
        )
        return

    await state.update_data(
        patronymic=message.text.strip()
    )

    await state.set_state(Registration.university)

    await message.answer(
        "Из какого ты вуза?",
        reply_markup=get_university_keyboard(),
    )


@router.callback_query(
    Registration.university,
    F.data.in_({"university_mirea", "university_other"}),
)
async def process_university(
    callback: CallbackQuery,
    state: FSMContext,
):
    """
    Получает выбор вуза пользователя.

    Для РТУ МИРЭА спрашивает курс.
    Для другого вуза просит ввести название вуза.
    """

    if callback.data == "university_mirea":
        await state.update_data(university="РТУ МИРЭА")
        await state.set_state(Registration.course)

        await callback.message.edit_text(
            "Какой у тебя курс?",
            reply_markup=get_course_keyboard(),
        )
        await callback.answer()
        return

    await state.set_state(Registration.other_university)

    await callback.message.edit_text(
        "Из какого ты ВУЗА?"
    )

    await callback.answer()


@router.message(Registration.other_university)
async def process_other_university(
    message: Message,
    state: FSMContext,
):
    """
    Получает название другого вуза и спрашивает курс.
    """

    if not message.text:
        await message.answer(
            "Пожалуйста, введите название вуза."
        )
        return

    await state.update_data(
        university=message.text.strip()
    )

    await state.set_state(Registration.course)

    await message.answer(
        "Какой у тебя курс?",
        reply_markup=get_course_keyboard(),
    )


@router.callback_query(
    Registration.course,
    F.data.in_(
        {
            "course_1",
            "course_2",
            "course_3",
            "course_4",
            "course_magistracy",
        }
    ),
)
async def process_course(
    callback: CallbackQuery,
    state: FSMContext,
):
    """
    Получает курс пользователя.

    Для РТУ МИРЭА спрашивает институт.
    Для другого вуза спрашивает направление.
    """

    course_labels = {
        "course_1": "1",
        "course_2": "2",
        "course_3": "3",
        "course_4": "4",
        "course_magistracy": "Магистратура",
    }

    await state.update_data(course=course_labels[callback.data])

    data = await state.get_data()

    if data.get("university") == "РТУ МИРЭА":
        await state.set_state(Registration.institute)

        await callback.message.edit_text(
            "Какой у тебя институт?"
        )
    else:
        await state.set_state(Registration.direction)

        await callback.message.edit_text(
            "Какое у тебя направление?"
        )

    await callback.answer()


@router.message(Registration.institute)
async def process_institute(
    message: Message,
    state: FSMContext,
):
    """
    Получает институт пользователя.
    """

    if not message.text:
        await message.answer(
            "Пожалуйста, введите институт."
        )
        return

    await state.update_data(
        institute=message.text.strip()
    )

    await state.set_state(Registration.direction)

    await message.answer(
        "Какое у тебя направление?"
    )


@router.message(Registration.direction)
async def process_direction(
    message: Message,
    state: FSMContext,
):
    """
    Получает направление пользователя.

    Для РТУ МИРЭА продолжает сбор данных.
    Для другого вуза завершает регистрацию.
    """

    if not message.text:
        await message.answer(
            "Пожалуйста, введите направление."
        )
        return

    await state.update_data(
        direction=message.text.strip()
    )

    data = await state.get_data()

    if data.get("university") != "РТУ МИРЭА":
        # Сохраняем данные в репозитории (in-memory или SQL, в зависимости от настроек).
        try:
            await repository.update_user(
                message.from_user.id,
                surname=data.get("surname"),
                name=data.get("name"),
                patronymic=data.get("patronymic"),
                id_university=1 if data.get("university") == "РТУ МИРЭА" else None,
            )
        except Exception:
            await message.answer(
                "Не удалось сохранить регистрацию в базу. Попробуйте ещё раз."
            )
            return

        await state.clear()

        await message.answer(
            "✅ Регистрация завершена!\n\n"
            f"Фамилия: {data['surname']}\n"
            f"Имя: {data['name']}\n"
            f"Отчество: {data['patronymic']}\n"
            f"Вуз: {data['university']}\n"
            f"Курс: {data['course']}\n"
            f"Направление: {data['direction']}"
        )
        return

    await state.set_state(Registration.direction_code)

    await message.answer(
        "Какой код у твоего направления?"
    )


@router.message(Registration.direction_code)
async def process_direction_code(
    message: Message,
    state: FSMContext,
):
    """
    Получает код направления пользователя.
    """

    if not message.text:
        await message.answer(
            "Пожалуйста, введите код направления."
        )
        return

    await state.update_data(
        direction_code=message.text.strip()
    )

    await state.set_state(Registration.group)

    await message.answer(
        "Какой номер у твоей группы?"
    )


@router.message(Registration.group)
async def process_group(
    message: Message,
    state: FSMContext,
):
    """
    Получает номер группы и завершает регистрацию.
    """

    if not message.text:
        await message.answer(
            "Пожалуйста, введите номер группы."
        )
        return

    await state.update_data(
        group=message.text.strip()
    )

    data = await state.get_data()

    # Сохраняем данные в репозитории (in-memory или SQL).
    try:
        await repository.update_user(
            message.from_user.id,
            surname=data.get("surname"),
            name=data.get("name"),
            patronymic=data.get("patronymic"),
            id_university=1 if data.get("university") == "РТУ МИРЭА" else None,
            institute=data.get("institute"),
            direction_code=data.get("direction_code"),
            group_name=data.get("group"),
        )
    except Exception:
        await message.answer(
            "Не удалось сохранить регистрацию в базу. Попробуйте ещё раз."
        )
        return

    await state.clear()

    await message.answer(
        "✅ Регистрация завершена!\n\n"
        f"Фамилия: {data['surname']}\n"
        f"Имя: {data['name']}\n"
        f"Отчество: {data['patronymic']}\n"
        f"Вуз: {data['university']}\n"
        f"Курс: {data['course']}\n"
        f"Институт: {data['institute']}\n"
        f"Направление: {data['direction']}\n"
        f"Код направления: {data['direction_code']}\n"
        f"Группа: {data['group']}"
    )
