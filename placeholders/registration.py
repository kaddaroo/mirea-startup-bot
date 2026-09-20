from placeholders import repository
import config

from datetime import datetime, timezone

def deep_link(payload):
    return payload if payload else None

def is_new_user(telegram_id: int) -> bool:
    return repository.find_user(telegram_id) is None

def save_pdn_consent(telegram_id: int) -> None:
    repository.update_user(telegram_id, pdn_consent=True)

def validate_first_name(text: str) -> bool:
    return len(text.split()) == 1 and text.isalpha()

def validate_last_name(text: str) -> bool:
    return validate_first_name(text)

def validate_surname(text: str) -> bool:
    return validate_first_name(text) or text == ""

def suggest_university() -> list[str]:
    return config.UNIVERSITIES

def get_institutie_option(university: str) -> list[str]:
    if university == "РТУ МИРЭА":
        return config.INSTITUTES

def get_course_option() -> list[str]:
    return config.COURSES

def is_deadline_passed() -> bool:
    return datetime.now(timezone.utc) > config.REGISTRATION_DEADLINE