from placeholders import repository_sql


def set_sql_enabled(_enabled: bool) -> None:
    return


async def find_user(telegram_id: int):
    return await repository_sql.find_user(telegram_id)


async def create_user(telegram_id: int, **fields):
    return await repository_sql.create_user(telegram_id, **fields)


async def update_user(telegram_id: int, **fields):
    return await repository_sql.update_user(telegram_id, **fields)


async def get_universities():
    return await repository_sql.get_universities()


async def get_university(university_id: int):
    return await repository_sql.get_university(university_id)


async def create_university(name: str):
    return await repository_sql.create_university(name)


async def get_available_events():
    return await repository_sql.get_available_events()


async def get_event(event_id: int):
    return await repository_sql.get_event(event_id)


async def update_event_photo(
    event_id: int,
    photo_file_id: str,
    channel_message_id: int | None = None,
) -> bool:
    return await repository_sql.update_event_photo(
        event_id,
        photo_file_id,
        channel_message_id,
    )


async def is_registered(telegram_id: int, event_id: int) -> bool:
    return await repository_sql.is_registered(telegram_id, event_id)


async def add_registration(telegram_id: int, event_id: int) -> bool:
    return await repository_sql.add_registration(telegram_id, event_id)


async def sync_attendance_coins(reward: int) -> int:
    return await repository_sql.sync_attendance_coins(reward)


async def create_event(
    *,
    name: str,
    description: str,
    address: str,
    start_date,
    end_date,
    deadline,
    photo_file_id: str | None = None,
    auditorium: str | None = None,
    route_url: str | None = None,
):
    return await repository_sql.create_event(
        name=name,
        description=description,
        address=address,
        start_date=start_date,
        end_date=end_date,
        deadline=deadline,
        photo_file_id=photo_file_id,
        auditorium=auditorium,
        route_url=route_url,
    )


async def get_admin_events(limit: int = 20):
    return await repository_sql.get_admin_events(limit)

async def upsert_lead(telegram_id: int, username: str | None, first_name: str | None,
                      last_step: str | None = None, marketing_link_id: int | None = None):
    return await repository_sql.upsert_lead(
        telegram_id, username, first_name, last_step, marketing_link_id
    )


async def mark_lead_completed(telegram_id: int):
    return await repository_sql.mark_lead_completed(telegram_id)


async def get_incomplete_leads(limit: int = 50):
    return await repository_sql.get_incomplete_leads(limit)


async def mark_lead_reminder_sent(telegram_id: int):
    return await repository_sql.mark_lead_reminder_sent(telegram_id)


async def get_due_reminders(limit: int = 100):
    return await repository_sql.get_due_reminders(limit)


async def mark_reminder_sent(reg_id: int):
    return await repository_sql.mark_reminder_sent(reg_id)


async def get_due_feedback(limit: int = 100):
    return await repository_sql.get_due_feedback(limit)


async def mark_feedback_sent(reg_id: int):
    return await repository_sql.mark_feedback_sent(reg_id)


async def save_feedback(telegram_id: int, event_id: int, rating: int, comment: str | None = None):
    return await repository_sql.save_feedback(telegram_id, event_id, rating, comment)


async def set_feedback_comment(telegram_id: int, event_id: int, comment: str):
    return await repository_sql.set_feedback_comment(telegram_id, event_id, comment)


async def set_checkin_open(event_id: int, is_open: bool):
    return await repository_sql.set_checkin_open(event_id, is_open)


async def checkin_by_token(telegram_id: int, token: str, reward: int):
    return await repository_sql.checkin_by_token(telegram_id, token, reward)


async def create_marketing_link(event_id: int | None, source: str, campaign: str | None, placement: str | None):
    return await repository_sql.create_marketing_link(event_id, source, campaign, placement)


async def record_marketing_visit(telegram_id: int, token: str):
    return await repository_sql.record_marketing_visit(telegram_id, token)


async def marketing_stats(limit: int = 30):
    return await repository_sql.marketing_stats(limit)

async def ensure_event_checkin_token(event_id: int):
    return await repository_sql.ensure_event_checkin_token(event_id)
