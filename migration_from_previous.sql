-- Use this if you already applied the previous migration that added:
-- universities.aliases, events.photo_file_id/channel_message_id, reg.coins_awarded.

ALTER TABLE events
    ADD COLUMN auditorium VARCHAR(255) NULL AFTER address,
    ADD COLUMN route_url VARCHAR(1000) NULL AFTER auditorium,
    ADD COLUMN checkin_token VARCHAR(64) NULL AFTER route_url,
    ADD COLUMN checkin_open TINYINT(1) NOT NULL DEFAULT 0 AFTER checkin_token;

ALTER TABLE reg
    ADD COLUMN attended_at DATETIME NULL AFTER coins_awarded,
    ADD COLUMN reminder_24h_sent TINYINT(1) NOT NULL DEFAULT 0 AFTER attended_at,
    ADD COLUMN feedback_sent TINYINT(1) NOT NULL DEFAULT 0 AFTER reminder_24h_sent;

CREATE TABLE IF NOT EXISTS bot_leads (
    telegram_id BIGINT NOT NULL PRIMARY KEY,
    username VARCHAR(255) NULL,
    first_name VARCHAR(255) NULL,
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    registration_completed TINYINT(1) NOT NULL DEFAULT 0,
    last_step VARCHAR(64) NULL,
    reminder_sent TINYINT(1) NOT NULL DEFAULT 0,
    marketing_link_id INT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS marketing_links (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    token VARCHAR(48) NOT NULL UNIQUE,
    event_id INT NULL,
    source VARCHAR(100) NOT NULL,
    campaign VARCHAR(150) NULL,
    placement VARCHAR(150) NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS marketing_visits (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    telegram_id BIGINT NOT NULL,
    marketing_link_id INT NOT NULL,
    opened_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    registered TINYINT(1) NOT NULL DEFAULT 0,
    KEY ix_marketing_visit_link (marketing_link_id),
    KEY ix_marketing_visit_user (telegram_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS event_feedback (
    id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    id_event INT NOT NULL,
    id_user INT NOT NULL,
    rating TINYINT NOT NULL,
    comment TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY ux_feedback_event_user (id_event, id_user)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
