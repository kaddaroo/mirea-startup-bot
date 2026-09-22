from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from handlers.admin_panel_handler import admin_menu_keyboard, is_admin
from placeholders import runtime_repository as repository

from ui_helpers import safe_callback_answer, safe_edit_callback_text

router = Router()


class MarketingCreate(StatesGroup):
    event_id = State()
    source = State()
    campaign = State()
    placement = State()


def nav() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✖️ Отмена", callback_data="admin_menu")]
    ])


@router.callback_query(F.data == "admin_marketing_create")
async def marketing_start(callback: CallbackQuery, state: FSMContext):
    await safe_callback_answer(callback)
    if not is_admin(callback.from_user.id):
        return
    await state.clear()
    await state.set_state(MarketingCreate.event_id)
    await safe_edit_callback_text(callback, 
        "🔗 Новая маркетинговая ссылка\n\nВведите ID мероприятия.\nНапример: 12\nЕсли ссылка общая, отправьте 0.",
        reply_markup=nav(),
    )


@router.message(MarketingCreate.event_id)
async def marketing_event(message: Message, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    try:
        event_id = int((message.text or "").strip())
    except ValueError:
        await message.answer("Введите число. Например: 12 или 0.", reply_markup=nav())
        return
    if event_id != 0 and await repository.get_event(event_id) is None:
        await message.answer("Мероприятие с таким ID не найдено. Попробуйте ещё раз.", reply_markup=nav())
        return
    await state.update_data(event_id=None if event_id == 0 else event_id)
    await state.set_state(MarketingCreate.source)
    await message.answer("Введите источник.\nНапример: telegram, vk, poster, partner", reply_markup=nav())


@router.message(MarketingCreate.source)
async def marketing_source(message: Message, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    value = (message.text or "").strip()
    if not value:
        return
    await state.update_data(source=value[:100])
    await state.set_state(MarketingCreate.campaign)
    await message.answer("Введите название кампании.\nНапример: september_meetup", reply_markup=nav())


@router.message(MarketingCreate.campaign)
async def marketing_campaign(message: Message, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    await state.update_data(campaign=(message.text or "").strip()[:150] or None)
    await state.set_state(MarketingCreate.placement)
    await message.answer("Введите размещение.\nНапример: startup_channel или poster_A11", reply_markup=nav())


@router.message(MarketingCreate.placement)
async def marketing_placement(message: Message, bot: Bot, state: FSMContext):
    if not message.from_user or not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    placement = (message.text or "").strip()[:150] or None
    link = await repository.create_marketing_link(
        data.get("event_id"), data["source"], data.get("campaign"), placement
    )
    me = await bot.get_me()
    url = f"https://t.me/{me.username}?start=m_{link['token']}"
    await state.clear()
    await message.answer(
        "✅ Маркетинговая ссылка создана.\n\n"
        f"Источник: {link['source']}\n"
        f"Кампания: {link.get('campaign') or '—'}\n"
        f"Размещение: {link.get('placement') or '—'}\n\n"
        f"{url}",
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(F.data == "admin_marketing_stats")
async def marketing_stats(callback: CallbackQuery):
    await safe_callback_answer(callback)
    if not is_admin(callback.from_user.id):
        return
    rows = await repository.marketing_stats(30)
    if not rows:
        text = "📊 Маркетинговых ссылок пока нет."
    else:
        lines = ["📊 Маркетинговые ссылки", ""]
        for row in rows:
            visits = int(row.get("visits") or 0)
            regs = int(row.get("registrations") or 0)
            conversion = (regs / visits * 100) if visits else 0
            lines.append(
                f"#{row['id']} {row['source']} / {row.get('placement') or '—'}\n"
                f"Переходы: {visits} · регистрации: {regs} · {conversion:.1f}%"
            )
        text = "\n\n".join(lines)
    await safe_edit_callback_text(callback, text, reply_markup=admin_menu_keyboard())
