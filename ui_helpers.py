from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
)


async def safe_callback_answer(
    callback: CallbackQuery,
    text: str | None = None,
    show_alert: bool = False,
) -> bool:
    """Answer a callback without crashing on an expired Telegram query."""
    try:
        await callback.answer(text=text, show_alert=show_alert)
        return True
    except TelegramBadRequest as error:
        error_text = str(error).lower()
        expired_markers = (
            "query is too old",
            "query id is invalid",
            "response timeout expired",
        )
        if any(marker in error_text for marker in expired_markers):
            return False
        raise


async def safe_edit_callback_text(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
    link_preview_options: LinkPreviewOptions | None = None,
):
    """Edit a callback message and ignore harmless duplicate-edit errors."""
    message = callback.message
    if message is None:
        return None

    try:
        return await message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            link_preview_options=link_preview_options,
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error).lower():
            return message
        raise


async def replace_callback_with_text(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    parse_mode: str | None = None,
    link_preview_options: LinkPreviewOptions | None = None,
):
    message = callback.message

    if message is None:
        return None

    has_media = bool(
        message.photo
        or message.video
        or message.document
        or message.animation
    )

    if not has_media:
        try:
            return await message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
                link_preview_options=link_preview_options,
            )
        except TelegramBadRequest:
            pass

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    return await callback.bot.send_message(
        chat_id=message.chat.id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode,
        link_preview_options=link_preview_options,
    )


async def replace_callback_with_photo(
    callback: CallbackQuery,
    photo: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup | None = None,
):
    message = callback.message

    if message is None:
        return None

    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    return await callback.bot.send_photo(
        chat_id=message.chat.id,
        photo=photo,
        caption=caption,
        reply_markup=reply_markup,
    )
