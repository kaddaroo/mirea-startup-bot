_users: dict[int, dict] = {}
_registrations: dict[str, set[int]] = {}          # event_code -> set(telegram_id)
_attendance: dict[tuple, str] = {}                 # (telegram_id, event_code) -> "came"/"not_came"


def find_user(telegram_id: int) -> dict | None:
    return _users.get(telegram_id)


def create_user(telegram_id: int, **fields) -> dict:
    profile = {"telegram_id": telegram_id, "coins": 0, **fields}
    _users[telegram_id] = profile
    return profile


def update_user(telegram_id: int, **fields) -> None:
    if telegram_id in _users:
        _users[telegram_id].update(fields)


def add_registration(telegram_id: int, event_code: str) -> None:
    _registrations.setdefault(event_code, set()).add(telegram_id)


def is_registered(telegram_id: int, event_code: str) -> bool:
    return telegram_id in _registrations.get(event_code, set())


def set_attendance(telegram_id: int, event_code: str, status: str) -> None:
    _attendance[(telegram_id, event_code)] = status


def has_any_past_event(telegram_id: int) -> bool:
    """Проверка, было ли у пользователя посещение хоть одного ивента раньше — для бонуса +3"""
    return any(
        tg_id == telegram_id and status == "came"
        for (tg_id, _ev), status in _attendance.items()
    )