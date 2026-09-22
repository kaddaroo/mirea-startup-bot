from datetime import datetime
from zoneinfo import ZoneInfo
import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@StartupClubRTUMIREA")
COINS_PER_ATTENDANCE = int(os.getenv("COINS_PER_ATTENDANCE", "3"))
WORKER_INTERVAL_SECONDS = int(os.getenv("WORKER_INTERVAL_SECONDS", "60"))
COIN_SYNC_INTERVAL_SECONDS = WORKER_INTERVAL_SECONDS


def _parse_admin_ids(value: str) -> set[int]:
    result = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            result.add(int(item))
        except ValueError:
            raise ValueError("ADMIN_IDS должен содержать Telegram ID через запятую")
    return result


ADMIN_IDS = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден")

MOSCOW = ZoneInfo("Europe/Moscow")
REGISTRATION_DEADLINE = datetime(2026, 9, 26, 12, 0, 0, tzinfo=MOSCOW)

COURSES = ["1", "2", "3", "4", "Магистратура", "Аспирантура"]
