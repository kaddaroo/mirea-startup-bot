from contextlib import contextmanager
import os
import threading
import time

import pymysql
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "5.188.159.76"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "dady_ru"),
    "password": os.getenv("MYSQL_PASSWORD", "#waT4mEcanFLYithenetW0rk"),
    "database": os.getenv("MYSQL_DATABASE", "dady_ru"),
    "charset": "utf8",
    "cursorclass": pymysql.cursors.DictCursor,
    "connect_timeout": 8,
    "read_timeout": 30,
    "write_timeout": 30,
    "autocommit": False,
}

USER_COLUMNS = {
    "telegram_id",
    "surname",
    "name",
    "patronymic",
    "id_university",
    "institute",
    "direction_code",
    "group_name",
    "coins",
}

CREATE_USER_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS `users` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `telegram_id` BIGINT NOT NULL,
    `surname` VARCHAR(255) DEFAULT NULL,
    `name` VARCHAR(255) DEFAULT NULL,
    `patronymic` VARCHAR(255) DEFAULT NULL,
    `id_university` INT DEFAULT NULL,
    `institute` VARCHAR(255) DEFAULT NULL,
    `direction_code` VARCHAR(50) DEFAULT NULL,
    `group_name` VARCHAR(255) DEFAULT NULL,
    `coins` INT DEFAULT 0,
    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
    `UPD` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `telegram_id` (`telegram_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8
"""

REMOTE_MYSQL_HINT = """
Не удалось подключиться к MySQL {host}:{port} (timeout).

phpMyAdmin открывается в браузере, потому что он работает НА сервере.
С вашего компьютера порт 3306, скорее всего, закрыт.

Что сделать:
1. В панели хостинга включите удалённый доступ к MySQL.
2. Добавьте ваш текущий IP в список разрешённых (или символ % — любой IP).
3. Подождите 1–2 минуты и снова запустите: python bot.py

Если бот будет крутиться на том же хостинге, в .env поставьте:
MYSQL_HOST=localhost
""".strip()

_lock = threading.RLock()
_connection = None


def get_connection(retries: int = 3):
    global _connection
    last_error = None

    with _lock:
        if _connection is not None:
            try:
                _connection.ping(reconnect=True)
                return _connection
            except pymysql.MySQLError:
                try:
                    _connection.close()
                except Exception:
                    pass
                _connection = None

        for attempt in range(1, retries + 1):
            try:
                print(
                    f"Connecting to MySQL {DB_CONFIG['host']}:{DB_CONFIG['port']} "
                    f"(attempt {attempt}/{retries})..."
                )
                _connection = pymysql.connect(**DB_CONFIG)
                print("MySQL connection established")
                return _connection
            except pymysql.MySQLError as error:
                last_error = error
                _connection = None
                print(f"MySQL connect failed: {error}")
                if attempt == retries:
                    break
                time.sleep(min(attempt * 2, 8))

    raise last_error


@contextmanager
def db_cursor():
    with _lock:
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
            cursor.close()


def init_db() -> None:
    with db_cursor() as (_connection_obj, cursor):
        cursor.execute(CREATE_USER_TABLE_SQL)
        cursor.execute("SELECT 1")
