from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import COINS_PER_FEEDBACK
from placeholders import runtime_repository as repository
from ui_helpers import safe_callback_answer, safe_edit_callback_text

router = Router()


class FeedbackForm(StatesGroup):
    liked_improve = State()
    wishes = State()


RATING_STEPS = {
    "location": ("🏠 Локация", "speakers"),
    "speakers": ("🎤 Спикеры (интересность, польза, подача)", "organization"),
    "organization": ("🧩 Организация (коммуникация, чёткость, атмосфера)", "overall"),
    "overall": ("✨ Общее впечатление от мероприятия", None),
}

PREVIOUS_RATING_STEP = {
    "speakers": "location",
    "organization": "speakers",
    "overall": "organization",
}


def _main_menu_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]


def rating_keyboard(event_id: int, criterion: str = "location") -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"⭐ {rating}",
                callback_data=f"feedback_score:{event_id}:{criterion}:{rating}",
            )
            for rating in range(1, 6)
        ]
    ]

    previous = PREVIOUS_RATING_STEP.get(criterion)
    if previous:
        rows.append(
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"feedback_back:{event_id}:{previous}",
                )
            ]
        )

    rows.append(_main_menu_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def text_step_keyboard(event_id: int, target: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=f"feedback_back:{event_id}:{target}",
                )
            ],
            _main_menu_row(),
        ]
    )


def feedback_finished_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")],
            [InlineKeyboardButton(text="🎫 Мероприятия", callback_data="show_events")],
            _main_menu_row(),
        ]
    )


def feedback_error_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎫 Мероприятия", callback_data="show_events")],
            _main_menu_row(),
        ]
    )


def _rating_prompt(criterion: str) -> str:
    label = RATING_STEPS[criterion][0]
    return f"Оцените по шкале от 1 до 5:\n\n{label}"


async def _restart_feedback(callback: CallbackQuery, state: FSMContext, event_id: int) -> None:
    await state.clear()
    await state.update_data(feedback_event_id=event_id)
    await safe_edit_callback_text(
        callback,
        "📝 Форма обратной связи\n\n" + _rating_prompt("location"),
        reply_markup=rating_keyboard(event_id, "location"),
    )


@router.callback_query(F.data.startswith("feedback_rating:"))
async def legacy_feedback_rating(callback: CallbackQuery, state: FSMContext):
    """Old feedback buttons may still exist in Telegram after deployment."""
    await safe_callback_answer(callback)
    try:
        _, event_id, _rating = callback.data.split(":", 2)
        event_id_int = int(event_id)
    except (ValueError, AttributeError):
        return

    await _restart_feedback(callback, state, event_id_int)


@router.callback_query(F.data.startswith("feedback_back:"))
async def feedback_back(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)

    try:
        _, event_id, target = callback.data.split(":", 2)
        event_id_int = int(event_id)
    except (ValueError, AttributeError):
        return

    data = await state.get_data()
    if data.get("feedback_event_id") != event_id_int:
        await _restart_feedback(callback, state, event_id_int)
        return

    if target in RATING_STEPS:
        # Remove answers that are after the step the user returned to.
        order = ["location", "speakers", "organization", "overall"]
        target_index = order.index(target)
        cleanup = {f"{criterion}_rating": None for criterion in order[target_index:]}
        cleanup.update({"liked_improve": None})
        await state.update_data(**cleanup)
        await state.set_state(None)
        await safe_edit_callback_text(
            callback,
            _rating_prompt(target),
            reply_markup=rating_keyboard(event_id_int, target),
        )
        return

    if target == "liked_improve":
        await state.update_data(liked_improve=None)
        await state.set_state(FeedbackForm.liked_improve)
        await safe_edit_callback_text(
            callback,
            "2. Что понравилось больше всего? Что можно улучшить?\n\n"
            "Напишите ответ одним сообщением.",
            reply_markup=text_step_keyboard(event_id_int, "overall"),
        )


@router.callback_query(F.data.startswith("feedback_score:"))
async def feedback_score(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)

    try:
        _, event_id, criterion, rating = callback.data.split(":", 3)
        event_id_int = int(event_id)
        rating_int = int(rating)
    except (ValueError, AttributeError):
        return

    if criterion not in RATING_STEPS or rating_int not in range(1, 6):
        return

    data = await state.get_data()

    if criterion == "location":
        # Starting a form from the first question should always create a clean draft.
        await state.clear()
        await state.update_data(feedback_event_id=event_id_int)
        data = {"feedback_event_id": event_id_int}
    elif data.get("feedback_event_id") != event_id_int:
        await _restart_feedback(callback, state, event_id_int)
        return

    await state.update_data(**{f"{criterion}_rating": rating_int})

    next_criterion = RATING_STEPS[criterion][1]
    if next_criterion is not None:
        await safe_edit_callback_text(
            callback,
            _rating_prompt(next_criterion),
            reply_markup=rating_keyboard(event_id_int, next_criterion),
        )
        return

    await state.set_state(FeedbackForm.liked_improve)
    await safe_edit_callback_text(
        callback,
        "2. Что понравилось больше всего? Что можно улучшить?\n\n"
        "Напишите ответ одним сообщением.",
        reply_markup=text_step_keyboard(event_id_int, "overall"),
    )


@router.message(FeedbackForm.liked_improve)
async def feedback_liked_improve(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    data = await state.get_data()
    event_id = data.get("feedback_event_id")

    if not text:
        await message.answer(
            "Пожалуйста, отправьте ответ текстовым сообщением.",
            reply_markup=(
                text_step_keyboard(int(event_id), "overall")
                if event_id
                else feedback_error_keyboard()
            ),
        )
        return

    if not event_id:
        await state.clear()
        await message.answer(
            "Не удалось продолжить форму: данные формы потерялись.",
            reply_markup=feedback_error_keyboard(),
        )
        return

    await state.update_data(liked_improve=text[:4000])
    await state.set_state(FeedbackForm.wishes)
    await message.answer(
        "3. Ваши пожелания по будущим мероприятиям и комментарии:\n"
        "спикеры, форматы, сферы (AI, GameDev, Foodtech...).\n\n"
        "Напишите ответ одним сообщением.",
        reply_markup=text_step_keyboard(int(event_id), "liked_improve"),
    )


@router.message(FeedbackForm.wishes)
async def feedback_wishes(message: Message, state: FSMContext):
    wishes = (message.text or "").strip()
    data = await state.get_data()
    event_id = data.get("feedback_event_id")

    if not wishes:
        await message.answer(
            "Пожалуйста, отправьте ответ текстовым сообщением.",
            reply_markup=(
                text_step_keyboard(int(event_id), "liked_improve")
                if event_id
                else feedback_error_keyboard()
            ),
        )
        return

    required = (
        "location_rating",
        "speakers_rating",
        "organization_rating",
        "overall_rating",
        "liked_improve",
    )
    if not event_id or any(data.get(key) is None for key in required):
        await state.clear()
        await message.answer(
            "Не удалось завершить форму: часть ответов потерялась. "
            "Откройте форму обратной связи ещё раз.",
            reply_markup=feedback_error_keyboard(),
        )
        return

    result = await repository.complete_feedback(
        telegram_id=message.from_user.id,
        event_id=int(event_id),
        location_rating=int(data["location_rating"]),
        speakers_rating=int(data["speakers_rating"]),
        organization_rating=int(data["organization_rating"]),
        overall_rating=int(data["overall_rating"]),
        liked_improve=str(data["liked_improve"]),
        wishes=wishes[:4000],
        reward=COINS_PER_FEEDBACK,
    )
    await state.clear()

    status = result.get("status")
    reward = int(result.get("reward") or 0)

    if status == "not_attended":
        await message.answer(
            "Форма доступна только участникам, чьё присутствие на мероприятии подтверждено.",
            reply_markup=feedback_error_keyboard(),
        )
        return

    if status == "not_registered_bot":
        await message.answer(
            "Профиль пользователя не найден. Отправьте /start.",
            reply_markup=feedback_error_keyboard(),
        )
        return

    if status != "ok":
        await message.answer(
            "Не удалось сохранить обратную связь. Попробуйте ещё раз позже.",
            reply_markup=feedback_error_keyboard(),
        )
        return

    if reward:
        await message.answer(
            "❤️ Спасибо за обратную связь!\n\n"
            f"🪙 За заполнение формы начислено {reward} коинов.",
            reply_markup=feedback_finished_keyboard(),
        )
    else:
        await message.answer(
            "❤️ Спасибо за обратную связь!\n\n"
            "Эта форма уже была учтена ранее, поэтому повторно коины не начисляются.",
            reply_markup=feedback_finished_keyboard(),
        )
