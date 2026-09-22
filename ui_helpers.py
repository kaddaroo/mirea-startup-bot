from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
)


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