import asyncio

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from handlers.coins_balance_handler import router as coins_router
from handlers.profile_view_handler import router as profile_router
from handlers.registration_handler import router as registration_router
from placeholders.events import router as events_router


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(registration_router)
    dp.include_router(profile_router)
    dp.include_router(coins_router)
    dp.include_router(events_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
