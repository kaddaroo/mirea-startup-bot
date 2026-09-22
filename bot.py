import asyncio

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN
from handlers.admin_engagement_handler import router as admin_engagement_router
from handlers.admin_marketing_handler import router as admin_marketing_router
from handlers.admin_panel_handler import router as admin_router
from handlers.coins_balance_handler import router as coins_router
from handlers.engagement_handler import router as engagement_router
from handlers.profile_view_handler import router as profile_router
from handlers.registration_handler import router as registration_router
from placeholders.events import router as events_router
from services import background_worker


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.include_router(admin_router)
    dp.include_router(admin_engagement_router)
    dp.include_router(admin_marketing_router)
    dp.include_router(engagement_router)
    dp.include_router(registration_router)
    dp.include_router(profile_router)
    dp.include_router(coins_router)
    dp.include_router(events_router)

    worker = asyncio.create_task(background_worker(bot))
    try:
        await dp.start_polling(bot)
    finally:
        worker.cancel()
        try:
            await worker
        except asyncio.CancelledError:
            pass
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
