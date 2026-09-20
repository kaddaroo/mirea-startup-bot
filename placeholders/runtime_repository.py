import asyncio

from placeholders import repository_sql


def set_sql_enabled(_enabled: bool) -> None:
    return


async def find_user(telegram_id: int):
    return await repository_sql.find_user(telegram_id)


async def create_user(telegram_id: int, **fields):
    return await repository_sql.create_user(telegram_id, **fields)


async def update_user(telegram_id: int, **fields):
    return await repository_sql.update_user(telegram_id, **fields)
