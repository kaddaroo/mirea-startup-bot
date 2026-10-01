from contextlib import contextmanager
import os
import time

import pymysql
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "connect_timeout": 5,
    "read_timeout": 10,
    "write_timeout": 10,
    "autocommit": False,
}

USER_COLUMNS = {
    "telegram_id", "surname", "name", "patronymic", "id_university",
    "institute", "direction_code", "group_name", "coins",
}


def get_connection(retries: int = 2):
    """Return an independent connection for one repository operation.

    The old implementation shared one global connection under one lock. A slow
    query therefore blocked every button that needed the database. Independent
    connections allow concurrent aiogram handlers to progress normally.
    """
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            return pymysql.connect(**DB_CONFIG)
        except pymysql.MySQLError as error:
            last_error = error
            if attempt < retries:
                time.sleep(0.5 * attempt)
    raise last_error


@contextmanager
def db_cursor():
    connection = get_connection()
    cursor = connection.cursor()
    try:
        yield connection, cursor
        connection.commit()
    except Exception:
        try:
            connection.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            cursor.close()
        finally:
            connection.close()


def init_db() -> None:
    with db_cursor() as (_connection, cursor):
        cursor.execute("SELECT 1")
