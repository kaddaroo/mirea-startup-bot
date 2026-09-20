import asyncio

import pymysql

from database.db import USER_COLUMNS, db_cursor


def _filter_fields(fields: dict) -> dict:
    return {key: value for key, value in fields.items() if key in USER_COLUMNS}


def _fetch_user(cursor, telegram_id: int):
    cursor.execute(
        "SELECT * FROM `users` WHERE telegram_id = %s",
        (telegram_id,),
    )
    return cursor.fetchone()


def _insert_user(cursor, telegram_id: int, fields: dict):
    payload = {"telegram_id": telegram_id, "coins": 0}
    payload.update(fields)
    payload["telegram_id"] = telegram_id

    columns = ", ".join(f"`{key}`" for key in payload)
    placeholders = ", ".join(["%s"] * len(payload))
    cursor.execute(
        f"INSERT INTO `users` ({columns}) VALUES ({placeholders})",
        tuple(payload.values()),
    )


def _find_user_sync(telegram_id: int):
    with db_cursor() as (_connection, cursor):
        return _fetch_user(cursor, telegram_id)


def _create_user_sync(telegram_id: int, **fields):
    payload = _filter_fields(fields)
    with db_cursor() as (connection, cursor):
        try:
            _insert_user(cursor, telegram_id, payload)
        except pymysql.err.IntegrityError:
            connection.rollback()
        return _fetch_user(cursor, telegram_id)


def _update_user_sync(telegram_id: int, **fields):
    payload = _filter_fields(fields)
    with db_cursor() as (_connection, cursor):
        existing = _fetch_user(cursor, telegram_id)

        if existing is None:
            _insert_user(cursor, telegram_id, payload)
            return _fetch_user(cursor, telegram_id)

        if not payload:
            return existing

        assignments = ", ".join(f"`{key}` = %s" for key in payload)
        cursor.execute(
            f"UPDATE `users` SET {assignments} WHERE telegram_id = %s",
            tuple(payload.values()) + (telegram_id,),
        )
        return _fetch_user(cursor, telegram_id)


async def find_user(telegram_id: int):
    return await asyncio.to_thread(_find_user_sync, telegram_id)


async def create_user(telegram_id: int, **fields):
    return await asyncio.to_thread(_create_user_sync, telegram_id, **fields)


async def update_user(telegram_id: int, **fields):
    return await asyncio.to_thread(_update_user_sync, telegram_id, **fields)


def _get_universities_sync():
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT id, name, short_name
            FROM universities
            ORDER BY id
            """
        )
        return cursor.fetchall()


async def get_universities():
    return await asyncio.to_thread(_get_universities_sync)


def _get_university_sync(university_id: int):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT id, name, short_name
            FROM universities
            WHERE id = %s
            """,
            (university_id,),
        )
        return cursor.fetchone()


async def get_university(university_id: int):
    return await asyncio.to_thread(_get_university_sync, university_id)


def _get_available_events_sync():
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT
                id,
                name,
                description,
                address,
                start_date,
                end_date,
                deadline
            FROM events
            WHERE end_date >= NOW()
            ORDER BY start_date
            """
        )
        return cursor.fetchall()


async def get_available_events():
    return await asyncio.to_thread(_get_available_events_sync)


def _get_event_sync(event_id: int):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT
                id,
                name,
                description,
                address,
                start_date,
                end_date,
                deadline
            FROM events
            WHERE id = %s
            """,
            (event_id,),
        )
        return cursor.fetchone()


async def get_event(event_id: int):
    return await asyncio.to_thread(_get_event_sync, event_id)


def _is_registered_sync(telegram_id: int, event_id: int) -> bool:
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT 1
            FROM reg
            JOIN users ON users.id = reg.id_user
            WHERE users.telegram_id = %s
              AND reg.id_event = %s
            LIMIT 1
            """,
            (telegram_id, event_id),
        )
        return cursor.fetchone() is not None


async def is_registered(telegram_id: int, event_id: int) -> bool:
    return await asyncio.to_thread(_is_registered_sync, telegram_id, event_id)


def _add_registration_sync(telegram_id: int, event_id: int) -> bool:
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE telegram_id = %s
            """,
            (telegram_id,),
        )
        user = cursor.fetchone()

        if user is None:
            return False

        cursor.execute(
            """
            SELECT 1
            FROM reg
            WHERE id_user = %s
              AND id_event = %s
            LIMIT 1
            """,
            (user["id"], event_id),
        )

        if cursor.fetchone() is not None:
            return False

        cursor.execute(
            """
            INSERT INTO reg (id_user, id_event, attended)
            VALUES (%s, %s, 0)
            """,
            (user["id"], event_id),
        )
        return True


async def add_registration(telegram_id: int, event_id: int) -> bool:
    return await asyncio.to_thread(_add_registration_sync, telegram_id, event_id)
