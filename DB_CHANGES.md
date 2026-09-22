# Что добавляется в БД

## `universities`
- `aliases TEXT` — варианты названия: `Бауманка`, `Вышка`, `Физтех` и т. п.

## `events`
- `photo_file_id VARCHAR(255)` — Telegram file_id афиши/фото; **сам файл в MySQL не нужен**.
- `channel_message_id BIGINT` — ID поста канала, если фото пришло оттуда.
- `auditorium VARCHAR(255)` — аудитория/помещение.
- `route_url VARCHAR(1000)` — ссылка «Как добраться».
- `checkin_token VARCHAR(64)` — секретный токен QR/deep link для отметки посещения.
- `checkin_open TINYINT(1)` — открыт ли сейчас check-in.

## `reg`
- `coins_awarded TINYINT(1)` — защита от повторного начисления коинов.
- `attended_at DATETIME` — когда пользователь отметился.
- `reminder_24h_sent TINYINT(1)` — отправлено ли 24-часовое напоминание.
- `feedback_sent TINYINT(1)` — отправлена ли форма обратной связи.

## `bot_leads`
Пользователи, которые запустили бота, но могли не завершить регистрацию. Нужна для сообщения «Привет, ты тут?».

## `marketing_links`
Deep links и их метки: мероприятие, source, campaign, placement, token.

## `marketing_visits`
Фиксирует переходы по маркетинговым ссылкам и факт завершения регистрации.

## `event_feedback`
Оценка 1–5 и необязательный комментарий после посещения.
