from placeholders import repository


def get_balance(telegram_id: int) -> int:
    user = repository.find_user(telegram_id)

    if user is None:
        raise ValueError("User not found")

    return user["coins"]

