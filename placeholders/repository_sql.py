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
