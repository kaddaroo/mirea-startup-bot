from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()


def _env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    return value.strip().strip('"').strip("'")


DATABASE_URL = _env("DATABASE_URL")
BOT_TOKEN = _env("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден")

REGISTRATION_DEADLINE = datetime(2026, 9, 26, 12, 0, 0)
CHANNEL_ID = '@mirea_startup_bot'

UNIVERSITIES = ['РТУ МИРЭА', 'МГТУ им. Баумана', 'МГТУ им. Н.Э. Баумана', 'НИУ ВШЭ', 'МГУ']
COURSES = ['1', '2', '3', '4', 'Магистратура', 'Аспирантура']
INSTITUTES = ['Институт информационных технологий', 'Институт радиоэлектроники и информационной безопасности', 'Институт кибербезопасности и цифровой криминалистики', 'Институт искусственного интеллекта', 'Институт космических технологий', 'Институт дизайна и урбанистики', 'Институт управления, экономики и финансов', 'Институт биомедицинских систем и технологий', 'Институт передовых производственных технологий', 'Институт перспективных производственных технологий', 'Институт перспективных производственных технологий', 'Институт перспективных производственных технологий']

