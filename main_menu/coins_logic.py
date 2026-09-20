from placeholders import runtime_repository as repository


def _field(user, name: str, default=0):
    if isinstance(user, dict):
        return user.get(name, default)
    return getattr(user, name, default)


async def get_balance(telegram_id: int) -> int:
    user = await repository.find_user(telegram_id)

    if user is None:
        raise ValueError("User not found")

    return _field(user, "coins") or 0

