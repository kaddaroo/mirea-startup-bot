from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from placeholders import runtime_repository as repository

from ui_helpers import safe_callback_answer, safe_edit_callback_text

router = Router()


class FeedbackForm(StatesGroup):
    comment = State()


def rating_keyboard(event_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"⭐ {rating}", callback_data=f"feedback_rating:{event_id}:{rating}")
            for rating in range(1, 6)
        ]
    ])


@router.callback_query(F.data.startswith("feedback_rating:"))
async def feedback_rating(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)
    _, event_id, rating = callback.data.split(":", 2)
    event_id_int = int(event_id)
    rating_int = int(rating)
    await repository.save_feedback(callback.from_user.id, event_id_int, rating_int)
    await state.set_state(FeedbackForm.comment)
    await state.update_data(feedback_event_id=event_id_int)
    await safe_edit_callback_text(callback, 
        f"Спасибо! Вы поставили {rating_int}/5 ⭐\n\n"
        "Если хотите, напишите короткий комментарий. Это поможет нам сделать следующие мероприятия лучше.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⏭ Без комментария", callback_data="feedback_skip_comment")]
        ]),
    )


@router.message(FeedbackForm.comment)
async def feedback_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    event_id = data.get("feedback_event_id")
    comment = (message.text or "").strip()
    if event_id and comment:
        await repository.set_feedback_comment(message.from_user.id, event_id, comment[:4000])
    await state.clear()
    await message.answer("❤️ Спасибо за обратную связь!")


@router.callback_query(FeedbackForm.comment, F.data == "feedback_skip_comment")
async def feedback_skip(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)
    await state.clear()
    await safe_edit_callback_text(callback, "❤️ Спасибо за обратную связь!")
