import asyncio

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from handlers.registration_handler import router as registration_router
from handlers.coins_balance import router as coins_router
from main_menu.profile_view import router as profile_router
from database.db import DB_CONFIG, REMOTE_MYSQL_HINT, init_db
from placeholders.runtime_repository import set_sql_enabled


async def main():
    set_sql_enabled(True)
    try:
        await asyncio.to_thread(init_db)
        print("Database connected successfully")
    except Exception as e:
        print("Database initialization failed:", repr(e))
        print(
            REMOTE_MYSQL_HINT.format(
                host=DB_CONFIG["host"],
                port=DB_CONFIG["port"],
            )
        )
        print("Бот всё равно запускается. Регистрация запишет пользователя, когда MySQL станет доступен.")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(registration_router)
    dp.include_router(coins_router)
    dp.include_router(profile_router)


    try:
        import importlib

        events_module = importlib.import_module("placeholders.events")
        if hasattr(events_module, "router"):
            dp.include_router(events_module.router)
    except Exception:
        print("Notice: placeholders.events not loaded — continuing without events router")

    try:

        try:
            await bot.delete_webhook(drop_pending_updates=True)
            print("Deleted existing webhook (if any)")
        except Exception as we:
            print("Warning: could not delete webhook:", repr(we))

        await dp.start_polling(bot)
    except Exception as e:
        print("Bot failed to start polling (network/API issue):", repr(e))
        return


if __name__ == "__main__":
    asyncio.run(main())
