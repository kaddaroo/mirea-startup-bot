from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from main_menu.keyboard import main_menu_keyboard, profile_keyboard
from placeholders import runtime_repository as repository

router = Router()


async def _build_profile_text(telegram_id: int) -> str | None:
    user = await repository.find_user(telegram_id)
    if user is None:
        return None

    university_name = "—"
    university_id = user.get("id_university")
    if university_id is not None:
        university = await repository.get_university(university_id)
        if university is not None:
            university_name = university.get("short_name") or university.get("name") or "—"

    full_name = " ".join(
        part
        for part in (
            user.get("surname"),
            user.get("name"),
            user.get("patronymic"),
        )
        if part
    ) or "—"

    return (
        "👤 <b>Ваш профиль</b>\n\n"
        f"ФИО: {full_name}\n"
        f"🎓 Вуз: {university_name}\n"
        f"🏫 Институт: {user.get('institute') or '—'}\n"
        f"📚 Код направления: {user.get('direction_code') or '—'}\n"
        f"👥 Группа: {user.get('group_name') or '—'}\n"
        f"💰 Коины: {user.get('coins', 0)}"
    )


@router.message(Command("menu"))
async def menu_command(message: Message, state: FSMContext):
    if not message.from_user:
        return

    user = await repository.find_user(message.from_user.id)
    if user is None:
        await message.answer("Сначала зарегистрируйтесь через /start.")
        return

    await state.clear()
    await message.answer(
        "🏠 Главное меню",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "🏠 Главное меню",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    text = await _build_profile_text(callback.from_user.id)

    if text is None:
        await callback.answer("Профиль не найден", show_alert=True)
        return

    await callback.message.edit_text(
        text,
        reply_markup=profile_keyboard(),
        parse_mode="HTML",
    )
    await callback.answer()
