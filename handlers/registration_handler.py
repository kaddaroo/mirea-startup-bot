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


router = Router()


class Registration(StatesGroup):
    consent = State()
    surname = State()
    name = State()
    patronymic = State()


async def is_user_registered(telegram_id: int) -> bool:
    """
    Проверяет, зарегистрирован ли пользователь.

    В будущем здесь будет обращение к БД.
    Сейчас функция является временной заглушкой.
    """

    # добавить проверку пользователя в БД
    return False


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

    # Новый пользователь — запускаем регистрацию.
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
    Получает отчество пользователя и завершает регистрацию.
    """

    if not message.text:
        await message.answer(
            "Пожалуйста, введите отчество."
        )
        return

    await state.update_data(
        patronymic=message.text.strip()
    )

    data = await state.get_data()

    # В будущем здесь будет обращение к БД
    # для сохранения данных зарегистрированного пользователя.

    await state.clear()

    await message.answer(
        "✅ Регистрация завершена!\n\n"
        f"Фамилия: {data['surname']}\n"
        f"Имя: {data['name']}\n"
        f"Отчество: {data['patronymic']}"
    )
