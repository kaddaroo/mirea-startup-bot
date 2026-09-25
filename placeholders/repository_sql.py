import asyncio
import secrets

import pymysql

from database.db import USER_COLUMNS, db_cursor


def _column_exists(cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(
        """
        SELECT 1
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        LIMIT 1
        """,
        (table_name, column_name),
    )
    return cursor.fetchone() is not None


def _ensure_rewards_schema_sync() -> None:
    """Add only the columns required by coin rules 1-3. Safe to run on every start."""
    required_columns = {
        "users": [
            (
                "first_attendance_bonus_awarded",
                "TINYINT(1) NOT NULL DEFAULT 0 AFTER coins",
            ),
        ],
        "event_feedback": [
            ("location_rating", "TINYINT NULL AFTER rating"),
            ("speakers_rating", "TINYINT NULL AFTER location_rating"),
            ("organization_rating", "TINYINT NULL AFTER speakers_rating"),
            ("overall_rating", "TINYINT NULL AFTER organization_rating"),
            ("liked_improve", "TEXT NULL AFTER comment"),
            ("wishes", "TEXT NULL AFTER liked_improve"),
            ("coins_awarded", "TINYINT(1) NOT NULL DEFAULT 0 AFTER wishes"),
        ],
    }

    with db_cursor() as (_connection, cursor):
        for table_name, columns in required_columns.items():
            for column_name, definition in columns:
                if _column_exists(cursor, table_name, column_name):
                    continue
                cursor.execute(
                    f"ALTER TABLE `{table_name}` ADD COLUMN `{column_name}` {definition}"
                )


async def ensure_rewards_schema() -> None:
    await asyncio.to_thread(_ensure_rewards_schema_sync)


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


def _get_universities_sync():
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT id, name, short_name, aliases
            FROM universities
            ORDER BY id
            """
        )
        return cursor.fetchall()


async def get_universities():
    return await asyncio.to_thread(_get_universities_sync)


def _get_university_sync(university_id: int):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT id, name, short_name, aliases
            FROM universities
            WHERE id = %s
            """,
            (university_id,),
        )
        return cursor.fetchone()


async def get_university(university_id: int):
    return await asyncio.to_thread(_get_university_sync, university_id)


def _create_university_sync(name: str):
    clean_name = " ".join(name.strip().split())

    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT id, name, short_name, aliases
            FROM universities
            WHERE LOWER(name) = LOWER(%s)
               OR LOWER(short_name) = LOWER(%s)
            LIMIT 1
            """,
            (clean_name, clean_name),
        )
        existing = cursor.fetchone()
        if existing is not None:
            return existing

        cursor.execute(
            """
            INSERT INTO universities (name, short_name, aliases)
            VALUES (%s, %s, '')
            """,
            (clean_name, clean_name),
        )
        university_id = cursor.lastrowid

        cursor.execute(
            """
            SELECT id, name, short_name, aliases
            FROM universities
            WHERE id = %s
            """,
            (university_id,),
        )
        return cursor.fetchone()


async def create_university(name: str):
    return await asyncio.to_thread(_create_university_sync, name)


def _get_available_events_sync():
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT
                id,
                name,
                description,
                address,
                start_date,
                end_date,
                deadline,
                photo_file_id,
                channel_message_id,
                auditorium,
                route_url,
                checkin_token,
                checkin_open
            FROM events
            WHERE end_date >= NOW()
            ORDER BY start_date
            """
        )
        return cursor.fetchall()


async def get_available_events():
    return await asyncio.to_thread(_get_available_events_sync)


def _get_event_sync(event_id: int):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT
                id,
                name,
                description,
                address,
                start_date,
                end_date,
                deadline,
                photo_file_id,
                channel_message_id,
                auditorium,
                route_url,
                checkin_token,
                checkin_open
            FROM events
            WHERE id = %s
            """,
            (event_id,),
        )
        return cursor.fetchone()


async def get_event(event_id: int):
    return await asyncio.to_thread(_get_event_sync, event_id)


def _update_event_photo_sync(
    event_id: int,
    photo_file_id: str,
    channel_message_id: int | None = None,
) -> bool:
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            UPDATE events
            SET photo_file_id = %s,
                channel_message_id = %s
            WHERE id = %s
            """,
            (photo_file_id, channel_message_id, event_id),
        )
        return cursor.rowcount > 0


async def update_event_photo(
    event_id: int,
    photo_file_id: str,
    channel_message_id: int | None = None,
) -> bool:
    return await asyncio.to_thread(
        _update_event_photo_sync,
        event_id,
        photo_file_id,
        channel_message_id,
    )


def _is_registered_sync(telegram_id: int, event_id: int) -> bool:
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT 1
            FROM reg
            JOIN users ON users.id = reg.id_user
            WHERE users.telegram_id = %s
              AND reg.id_event = %s
            LIMIT 1
            """,
            (telegram_id, event_id),
        )
        return cursor.fetchone() is not None


async def is_registered(telegram_id: int, event_id: int) -> bool:
    return await asyncio.to_thread(_is_registered_sync, telegram_id, event_id)


def _add_registration_sync(telegram_id: int, event_id: int) -> bool:
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            "SELECT id FROM users WHERE telegram_id = %s",
            (telegram_id,),
        )
        user = cursor.fetchone()
        if user is None:
            return False

        cursor.execute(
            """
            SELECT 1
            FROM reg
            WHERE id_user = %s
              AND id_event = %s
            LIMIT 1
            """,
            (user["id"], event_id),
        )
        if cursor.fetchone() is not None:
            return False

        cursor.execute(
            """
            INSERT INTO reg (id_user, id_event, attended, coins_awarded)
            VALUES (%s, %s, 0, 0)
            """,
            (user["id"], event_id),
        )
        return True


async def add_registration(telegram_id: int, event_id: int) -> bool:
    return await asyncio.to_thread(_add_registration_sync, telegram_id, event_id)


def _sync_attendance_coins_sync(reward: int, first_attendance_bonus: int) -> int:
    """Award attendance coins once; add the first-event bonus only for a user's first attendance."""
    awarded = 0

    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT r.id, r.id_user
            FROM reg AS r
            WHERE r.attended = 1
              AND COALESCE(r.coins_awarded, 0) = 0
            ORDER BY COALESCE(r.attended_at, r.UPD), r.id
            """
        )
        rows = cursor.fetchall()

        for row in rows:
            cursor.execute(
                "SELECT id, first_attendance_bonus_awarded FROM users WHERE id = %s FOR UPDATE",
                (row["id_user"],),
            )
            user = cursor.fetchone()
            if user is None:
                continue

            cursor.execute(
                """
                UPDATE reg
                SET coins_awarded = 1
                WHERE id = %s
                  AND attended = 1
                  AND COALESCE(coins_awarded, 0) = 0
                """,
                (row["id"],),
            )
            if cursor.rowcount != 1:
                continue

            bonus = 0
            if not user.get("first_attendance_bonus_awarded"):
                cursor.execute(
                    """
                    SELECT COUNT(*) AS attended_count
                    FROM reg
                    WHERE id_user = %s AND attended = 1
                    """,
                    (row["id_user"],),
                )
                attended_count = int(cursor.fetchone()["attended_count"] or 0)
                if attended_count == 1:
                    cursor.execute(
                        """
                        UPDATE users
                        SET first_attendance_bonus_awarded = 1
                        WHERE id = %s
                          AND first_attendance_bonus_awarded = 0
                        """,
                        (row["id_user"],),
                    )
                    if cursor.rowcount == 1:
                        bonus = first_attendance_bonus

            cursor.execute(
                """
                UPDATE users
                SET coins = COALESCE(coins, 0) + %s
                WHERE id = %s
                """,
                (reward + bonus, row["id_user"]),
            )
            awarded += 1

    return awarded


async def sync_attendance_coins(reward: int, first_attendance_bonus: int) -> int:
    return await asyncio.to_thread(
        _sync_attendance_coins_sync,
        reward,
        first_attendance_bonus,
    )

def _create_event_sync(
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
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            INSERT INTO events (
                name,
                description,
                address,
                start_date,
                end_date,
                deadline,
                photo_file_id,
                auditorium,
                route_url,
                checkin_token,
                checkin_open
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
            """,
            (
                name,
                description,
                address,
                start_date,
                end_date,
                deadline,
                photo_file_id,
                auditorium,
                route_url,
                secrets.token_urlsafe(16),
            ),
        )
        event_id = cursor.lastrowid
        cursor.execute(
            """
            SELECT
                id,
                name,
                description,
                address,
                start_date,
                end_date,
                deadline,
                photo_file_id,
                channel_message_id,
                auditorium,
                route_url,
                checkin_token,
                checkin_open
            FROM events
            WHERE id = %s
            """,
            (event_id,),
        )
        return cursor.fetchone()


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
    return await asyncio.to_thread(
        _create_event_sync,
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


def _get_admin_events_sync(limit: int = 20):
    safe_limit = max(1, min(int(limit), 100))
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            f"""
            SELECT
                id,
                name,
                description,
                address,
                start_date,
                end_date,
                deadline,
                photo_file_id,
                channel_message_id,
                auditorium,
                route_url,
                checkin_token,
                checkin_open
            FROM events
            ORDER BY start_date DESC, id DESC
            LIMIT {safe_limit}
            """
        )
        return cursor.fetchall()


async def get_admin_events(limit: int = 20):
    return await asyncio.to_thread(_get_admin_events_sync, limit)

# ---- Engagement / reminders / analytics ---------------------------------

def _upsert_lead_sync(
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    last_step: str | None = None,
    marketing_link_id: int | None = None,
):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            INSERT INTO bot_leads (
                telegram_id, username, first_name, last_step, marketing_link_id
            ) VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                username = VALUES(username),
                first_name = VALUES(first_name),
                last_step = COALESCE(VALUES(last_step), last_step),
                marketing_link_id = COALESCE(VALUES(marketing_link_id), marketing_link_id),
                updated_at = CURRENT_TIMESTAMP
            """,
            (telegram_id, username, first_name, last_step, marketing_link_id),
        )


async def upsert_lead(telegram_id: int, username: str | None, first_name: str | None,
                      last_step: str | None = None, marketing_link_id: int | None = None):
    return await asyncio.to_thread(
        _upsert_lead_sync, telegram_id, username, first_name, last_step, marketing_link_id
    )


def _mark_lead_completed_sync(telegram_id: int):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            UPDATE bot_leads
            SET registration_completed = 1, last_step = 'completed'
            WHERE telegram_id = %s
            """,
            (telegram_id,),
        )
        cursor.execute(
            """
            UPDATE marketing_visits
            SET registered = 1
            WHERE id = (
                SELECT id FROM (
                    SELECT id
                    FROM marketing_visits
                    WHERE telegram_id = %s
                    ORDER BY opened_at DESC, id DESC
                    LIMIT 1
                ) AS latest_visit
            )
            """,
            (telegram_id,),
        )


async def mark_lead_completed(telegram_id: int):
    return await asyncio.to_thread(_mark_lead_completed_sync, telegram_id)


def _get_incomplete_leads_sync(limit: int = 50):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT telegram_id, first_name
            FROM bot_leads
            WHERE registration_completed = 0
              AND reminder_sent = 0
              AND started_at <= NOW() - INTERVAL 2 HOUR
            ORDER BY started_at
            LIMIT %s
            """,
            (limit,),
        )
        return cursor.fetchall()


async def get_incomplete_leads(limit: int = 50):
    return await asyncio.to_thread(_get_incomplete_leads_sync, limit)


def _mark_lead_reminder_sent_sync(telegram_id: int):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            "UPDATE bot_leads SET reminder_sent = 1 WHERE telegram_id = %s",
            (telegram_id,),
        )


async def mark_lead_reminder_sent(telegram_id: int):
    return await asyncio.to_thread(_mark_lead_reminder_sent_sync, telegram_id)


def _get_due_reminders_sync(limit: int = 100):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT
                r.id AS reg_id,
                u.telegram_id,
                e.id AS event_id,
                e.name,
                e.start_date,
                e.address,
                e.auditorium,
                e.route_url
            FROM reg r
            JOIN users u ON u.id = r.id_user
            JOIN events e ON e.id = r.id_event
            WHERE COALESCE(r.reminder_24h_sent, 0) = 0
              AND e.start_date > NOW()
              AND e.start_date <= NOW() + INTERVAL 24 HOUR
            ORDER BY e.start_date
            LIMIT %s
            """,
            (limit,),
        )
        return cursor.fetchall()


async def get_due_reminders(limit: int = 100):
    return await asyncio.to_thread(_get_due_reminders_sync, limit)


def _mark_reminder_sent_sync(reg_id: int):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            "UPDATE reg SET reminder_24h_sent = 1 WHERE id = %s",
            (reg_id,),
        )


async def mark_reminder_sent(reg_id: int):
    return await asyncio.to_thread(_mark_reminder_sent_sync, reg_id)


def _get_due_feedback_sync(limit: int = 100):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT
                r.id AS reg_id,
                u.telegram_id,
                e.id AS event_id,
                e.name
            FROM reg r
            JOIN users u ON u.id = r.id_user
            JOIN events e ON e.id = r.id_event
            WHERE r.attended = 1
              AND COALESCE(r.feedback_sent, 0) = 0
              AND e.end_date <= NOW()
            ORDER BY e.end_date
            LIMIT %s
            """,
            (limit,),
        )
        return cursor.fetchall()


async def get_due_feedback(limit: int = 100):
    return await asyncio.to_thread(_get_due_feedback_sync, limit)


def _mark_feedback_sent_sync(reg_id: int):
    with db_cursor() as (_connection, cursor):
        cursor.execute("UPDATE reg SET feedback_sent = 1 WHERE id = %s", (reg_id,))


async def mark_feedback_sent(reg_id: int):
    return await asyncio.to_thread(_mark_feedback_sent_sync, reg_id)


def _complete_feedback_sync(
    telegram_id: int,
    event_id: int,
    location_rating: int,
    speakers_rating: int,
    organization_rating: int,
    overall_rating: int,
    liked_improve: str,
    wishes: str,
    reward: int,
):
    ratings = (
        location_rating,
        speakers_rating,
        organization_rating,
        overall_rating,
    )
    if any(rating not in range(1, 6) for rating in ratings):
        return {"status": "invalid", "reward": 0}

    with db_cursor() as (_connection, cursor):
        cursor.execute(
            "SELECT id FROM users WHERE telegram_id = %s FOR UPDATE",
            (telegram_id,),
        )
        user = cursor.fetchone()
        if user is None:
            return {"status": "not_registered_bot", "reward": 0}

        cursor.execute(
            """
            SELECT id
            FROM reg
            WHERE id_user = %s
              AND id_event = %s
              AND attended = 1
            LIMIT 1
            """,
            (user["id"], event_id),
        )
        if cursor.fetchone() is None:
            return {"status": "not_attended", "reward": 0}

        cursor.execute(
            """
            SELECT id, COALESCE(coins_awarded, 0) AS coins_awarded
            FROM event_feedback
            WHERE id_event = %s AND id_user = %s
            LIMIT 1
            FOR UPDATE
            """,
            (event_id, user["id"]),
        )
        existing = cursor.fetchone()

        if existing is None:
            cursor.execute(
                """
                INSERT INTO event_feedback (
                    id_event,
                    id_user,
                    rating,
                    location_rating,
                    speakers_rating,
                    organization_rating,
                    overall_rating,
                    comment,
                    liked_improve,
                    wishes,
                    coins_awarded
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, 0)
                """,
                (
                    event_id,
                    user["id"],
                    overall_rating,
                    location_rating,
                    speakers_rating,
                    organization_rating,
                    overall_rating,
                    liked_improve,
                    wishes,
                ),
            )
            feedback_id = cursor.lastrowid
            already_awarded = False
        else:
            feedback_id = existing["id"]
            already_awarded = bool(existing.get("coins_awarded"))
            cursor.execute(
                """
                UPDATE event_feedback
                SET rating = %s,
                    location_rating = %s,
                    speakers_rating = %s,
                    organization_rating = %s,
                    overall_rating = %s,
                    liked_improve = %s,
                    wishes = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    overall_rating,
                    location_rating,
                    speakers_rating,
                    organization_rating,
                    overall_rating,
                    liked_improve,
                    wishes,
                    feedback_id,
                ),
            )

        if already_awarded:
            return {"status": "ok", "reward": 0}

        cursor.execute(
            """
            UPDATE event_feedback
            SET coins_awarded = 1
            WHERE id = %s
              AND COALESCE(coins_awarded, 0) = 0
            """,
            (feedback_id,),
        )
        if cursor.rowcount != 1:
            return {"status": "ok", "reward": 0}

        cursor.execute(
            """
            UPDATE users
            SET coins = COALESCE(coins, 0) + %s
            WHERE id = %s
            """,
            (reward, user["id"]),
        )
        return {"status": "ok", "reward": reward}


async def complete_feedback(
    telegram_id: int,
    event_id: int,
    location_rating: int,
    speakers_rating: int,
    organization_rating: int,
    overall_rating: int,
    liked_improve: str,
    wishes: str,
    reward: int,
):
    return await asyncio.to_thread(
        _complete_feedback_sync,
        telegram_id,
        event_id,
        location_rating,
        speakers_rating,
        organization_rating,
        overall_rating,
        liked_improve,
        wishes,
        reward,
    )


def _set_checkin_open_sync(event_id: int, is_open: bool):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            "UPDATE events SET checkin_open = %s WHERE id = %s",
            (1 if is_open else 0, event_id),
        )
        return cursor.rowcount > 0


async def set_checkin_open(event_id: int, is_open: bool):
    return await asyncio.to_thread(_set_checkin_open_sync, event_id, is_open)


def _checkin_by_token_sync(
    telegram_id: int,
    token: str,
    reward: int,
    first_attendance_bonus: int,
):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            "SELECT id, name, checkin_open FROM events WHERE checkin_token = %s LIMIT 1",
            (token,),
        )
        event = cursor.fetchone()
        if event is None:
            return {"status": "invalid"}
        if not event.get("checkin_open"):
            return {"status": "closed", "event": event}

        # Lock the user row so two simultaneous QR scans cannot award coins twice.
        cursor.execute(
            """
            SELECT id, first_attendance_bonus_awarded
            FROM users
            WHERE telegram_id = %s
            FOR UPDATE
            """,
            (telegram_id,),
        )
        user = cursor.fetchone()
        if user is None:
            return {"status": "not_registered_bot", "event": event}

        cursor.execute(
            """
            SELECT id, attended, coins_awarded
            FROM reg
            WHERE id_user = %s AND id_event = %s
            LIMIT 1
            """,
            (user["id"], event["id"]),
        )
        reg = cursor.fetchone()
        if reg is None:
            return {"status": "not_registered_event", "event": event}
        if reg.get("attended"):
            return {"status": "already", "event": event}

        cursor.execute(
            """
            SELECT 1
            FROM reg
            WHERE id_user = %s
              AND attended = 1
            LIMIT 1
            """,
            (user["id"],),
        )
        had_previous_attendance = cursor.fetchone() is not None

        cursor.execute(
            """
            UPDATE reg
            SET attended = 1,
                attended_at = NOW()
            WHERE id = %s
              AND attended = 0
            """,
            (reg["id"],),
        )
        if cursor.rowcount != 1:
            return {"status": "already", "event": event}

        attendance_reward = 0
        bonus = 0

        cursor.execute(
            """
            UPDATE reg
            SET coins_awarded = 1
            WHERE id = %s
              AND COALESCE(coins_awarded, 0) = 0
            """,
            (reg["id"],),
        )
        if cursor.rowcount == 1:
            attendance_reward = reward

            if (
                not had_previous_attendance
                and not user.get("first_attendance_bonus_awarded")
            ):
                cursor.execute(
                    """
                    UPDATE users
                    SET first_attendance_bonus_awarded = 1
                    WHERE id = %s
                      AND first_attendance_bonus_awarded = 0
                    """,
                    (user["id"],),
                )
                if cursor.rowcount == 1:
                    bonus = first_attendance_bonus

            cursor.execute(
                """
                UPDATE users
                SET coins = COALESCE(coins, 0) + %s
                WHERE id = %s
                """,
                (attendance_reward + bonus, user["id"]),
            )

        return {
            "status": "ok",
            "event": event,
            "attendance_reward": attendance_reward,
            "first_attendance_bonus": bonus,
            "coins_awarded": attendance_reward + bonus,
        }


async def checkin_by_token(
    telegram_id: int,
    token: str,
    reward: int,
    first_attendance_bonus: int,
):
    return await asyncio.to_thread(
        _checkin_by_token_sync,
        telegram_id,
        token,
        reward,
        first_attendance_bonus,
    )

def _create_marketing_link_sync(event_id: int | None, source: str, campaign: str | None, placement: str | None):
    token = secrets.token_urlsafe(9)
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            INSERT INTO marketing_links (token, event_id, source, campaign, placement)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (token, event_id, source, campaign, placement),
        )
        return {"id": cursor.lastrowid, "token": token, "event_id": event_id,
                "source": source, "campaign": campaign, "placement": placement}


async def create_marketing_link(event_id: int | None, source: str, campaign: str | None, placement: str | None):
    return await asyncio.to_thread(_create_marketing_link_sync, event_id, source, campaign, placement)


def _record_marketing_visit_sync(telegram_id: int, token: str):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            "SELECT id, event_id FROM marketing_links WHERE token = %s AND active = 1 LIMIT 1",
            (token,),
        )
        link = cursor.fetchone()
        if link is None:
            return None
        cursor.execute(
            "INSERT INTO marketing_visits (telegram_id, marketing_link_id) VALUES (%s, %s)",
            (telegram_id, link["id"]),
        )
        return link


async def record_marketing_visit(telegram_id: int, token: str):
    return await asyncio.to_thread(_record_marketing_visit_sync, telegram_id, token)


def _marketing_stats_sync(limit: int = 30):
    with db_cursor() as (_connection, cursor):
        cursor.execute(
            """
            SELECT ml.id, ml.source, ml.campaign, ml.placement, ml.event_id,
                   COUNT(mv.id) AS visits,
                   SUM(CASE WHEN mv.registered = 1 THEN 1 ELSE 0 END) AS registrations
            FROM marketing_links ml
            LEFT JOIN marketing_visits mv ON mv.marketing_link_id = ml.id
            GROUP BY ml.id, ml.source, ml.campaign, ml.placement, ml.event_id
            ORDER BY ml.id DESC
            LIMIT %s
            """,
            (limit,),
        )
        return cursor.fetchall()


async def marketing_stats(limit: int = 30):
    return await asyncio.to_thread(_marketing_stats_sync, limit)


def _ensure_event_checkin_token_sync(event_id: int):
    with db_cursor() as (_connection, cursor):
        cursor.execute("SELECT checkin_token FROM events WHERE id = %s", (event_id,))
        row = cursor.fetchone()
        if row is None:
            return None
        token = row.get("checkin_token")
        if not token:
            token = secrets.token_urlsafe(16)
            cursor.execute(
                "UPDATE events SET checkin_token = %s WHERE id = %s AND checkin_token IS NULL",
                (token, event_id),
            )
        return token


async def ensure_event_checkin_token(event_id: int):
    return await asyncio.to_thread(_ensure_event_checkin_token_sync, event_id)
