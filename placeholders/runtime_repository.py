from placeholders import repository_sql


def set_sql_enabled(_enabled: bool) -> None:
    return


async def find_user(telegram_id: int):
    return await repository_sql.find_user(telegram_id)


async def create_user(telegram_id: int, **fields):
    return await repository_sql.create_user(
        telegram_id,
        **fields
    )


async def update_user(telegram_id: int, **fields):
    return await repository_sql.update_user(
        telegram_id,
        **fields
    )


async def get_available_events():
    return await repository_sql.get_available_events()


async def get_event(event_id: int):
    return await repository_sql.get_event(event_id)


async def is_registered(
    telegram_id: int,
    event_id: int
):
    return await repository_sql.is_registered(
        telegram_id,
        event_id
    )


async def add_registration(
    telegram_id: int,
    event_id: int
):
    return await repository_sql.add_registration(
        telegram_id,
        event_id
    )


async def get_universities():
    return await repository_sql.get_universities()


async def get_university(university_id: int):
    return await repository_sql.get_university(
        university_id
    )