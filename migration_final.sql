-- FINAL MIGRATION for Startup Club bot.
-- Make a DB backup first. Run this in phpMyAdmin on the bot database.

ALTER TABLE universities
    ADD COLUMN aliases TEXT NULL AFTER short_name;

ALTER TABLE events
    ADD COLUMN photo_file_id VARCHAR(255) NULL AFTER deadline,
    ADD COLUMN channel_message_id BIGINT NULL AFTER photo_file_id,
    ADD COLUMN auditorium VARCHAR(255) NULL AFTER address,
    ADD COLUMN route_url VARCHAR(1000) NULL AFTER auditorium,
    ADD COLUMN checkin_token VARCHAR(64) NULL AFTER route_url,
    ADD COLUMN checkin_open TINYINT(1) NOT NULL DEFAULT 0 AFTER checkin_token;

ALTER TABLE reg
    ADD COLUMN coins_awarded TINYINT(1) NOT NULL DEFAULT 0 AFTER attended,
    ADD COLUMN attended_at DATETIME NULL AFTER coins_awarded,
    ADD COLUMN reminder_24h_sent TINYINT(1) NOT NULL DEFAULT 0 AFTER attended_at,
    ADD COLUMN feedback_sent TINYINT(1) NOT NULL DEFAULT 0 AFTER reminder_24h_sent;

CREATE TABLE IF NOT EXISTS bot_leads (
    telegram_id BIGINT NOT NULL,
    username VARCHAR(255) NULL,
    first_name VARCHAR(255) NULL,
    started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    registration_completed TINYINT(1) NOT NULL DEFAULT 0,
    last_step VARCHAR(64) NULL,
    reminder_sent TINYINT(1) NOT NULL DEFAULT 0,
    marketing_link_id INT NULL,
    PRIMARY KEY (telegram_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS marketing_links (
    id INT NOT NULL AUTO_INCREMENT,
    token VARCHAR(48) NOT NULL,
    event_id INT NULL,
    source VARCHAR(100) NOT NULL,
    campaign VARCHAR(150) NULL,
    placement VARCHAR(150) NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY ux_marketing_token (token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS marketing_visits (
    id BIGINT NOT NULL AUTO_INCREMENT,
    telegram_id BIGINT NOT NULL,
    marketing_link_id INT NOT NULL,
    opened_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    registered TINYINT(1) NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY ix_marketing_visit_link (marketing_link_id),
    KEY ix_marketing_visit_user (telegram_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS event_feedback (
    id BIGINT NOT NULL AUTO_INCREMENT,
    id_event INT NOT NULL,
    id_user INT NOT NULL,
    rating TINYINT NOT NULL,
    comment TEXT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY ux_feedback_event_user (id_event, id_user)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Common Moscow universities + aliases. Unknown universities can also be created by the bot.
INSERT INTO universities (name, short_name, aliases)
SELECT seed.name, seed.short_name, seed.aliases
FROM (
    SELECT 'Российский технологический университет МИРЭА' AS name, 'РТУ МИРЭА' AS short_name, 'МИРЭА,РТУ,Московский технологический университет' AS aliases
    UNION ALL SELECT 'Московский государственный университет имени М. В. Ломоносова', 'МГУ', 'МГУ им. Ломоносова,Ломоносовский университет'
    UNION ALL SELECT 'Московский государственный технический университет имени Н. Э. Баумана', 'МГТУ им. Н. Э. Баумана', 'МГТУ,Бауманка,Бауманский'
    UNION ALL SELECT 'Национальный исследовательский университет «Высшая школа экономики»', 'НИУ ВШЭ', 'ВШЭ,Вышка,HSE'
    UNION ALL SELECT 'Московский государственный институт международных отношений (университет) МИД России', 'МГИМО', 'МГИМО МИД России'
    UNION ALL SELECT 'Российский экономический университет имени Г. В. Плеханова', 'РЭУ им. Г. В. Плеханова', 'РЭУ,Плехановский,Плешка'
    UNION ALL SELECT 'Финансовый университет при Правительстве Российской Федерации', 'Финансовый университет', 'Финуниверситет,ФУ'
    UNION ALL SELECT 'Российская академия народного хозяйства и государственной службы при Президенте Российской Федерации', 'РАНХиГС', 'РАНХИГС,Президентская академия'
    UNION ALL SELECT 'Российский университет дружбы народов имени Патриса Лумумбы', 'РУДН', 'РУДН имени Патриса Лумумбы'
    UNION ALL SELECT 'Национальный исследовательский ядерный университет «МИФИ»', 'НИЯУ МИФИ', 'МИФИ'
    UNION ALL SELECT 'Национальный исследовательский технологический университет «МИСИС»', 'НИТУ МИСИС', 'МИСИС'
    UNION ALL SELECT 'Московский авиационный институт (национальный исследовательский университет)', 'МАИ', 'Московский авиационный институт'
    UNION ALL SELECT 'Национальный исследовательский университет «МЭИ»', 'НИУ МЭИ', 'МЭИ'
    UNION ALL SELECT 'Московский физико-технический институт (национальный исследовательский университет)', 'МФТИ', 'Физтех'
    UNION ALL SELECT 'Российский государственный университет нефти и газа (НИУ) имени И. М. Губкина', 'РГУ нефти и газа им. И. М. Губкина', 'Губкинский,Губкина'
    UNION ALL SELECT 'Национальный исследовательский Московский государственный строительный университет', 'НИУ МГСУ', 'МГСУ'
    UNION ALL SELECT 'Московский политехнический университет', 'Московский Политех', 'Мосполитех,МПУ'
    UNION ALL SELECT 'Московский автомобильно-дорожный государственный технический университет', 'МАДИ', 'МАДИ'
    UNION ALL SELECT 'Российский университет транспорта', 'РУТ (МИИТ)', 'МИИТ,РУТ'
    UNION ALL SELECT 'Российский химико-технологический университет имени Д. И. Менделеева', 'РХТУ им. Д. И. Менделеева', 'РХТУ,Менделеевка'
    UNION ALL SELECT 'Российский государственный университет имени А. Н. Косыгина', 'РГУ им. А. Н. Косыгина', 'РГУ Косыгина,Косыгина'
    UNION ALL SELECT 'Московский государственный юридический университет имени О. Е. Кутафина', 'МГЮА', 'МГЮА им. Кутафина,Кутафина'
    UNION ALL SELECT 'Первый Московский государственный медицинский университет имени И. М. Сеченова', 'Сеченовский университет', 'Первый МГМУ,Сеченовка'
    UNION ALL SELECT 'Российский национальный исследовательский медицинский университет имени Н. И. Пирогова', 'РНИМУ им. Н. И. Пирогова', 'РНИМУ,Пироговка'
    UNION ALL SELECT 'Московский государственный медико-стоматологический университет имени А. И. Евдокимова', 'МГМСУ', 'МГМСУ им. Евдокимова'
    UNION ALL SELECT 'Московский государственный лингвистический университет', 'МГЛУ', 'ИнЯз'
    UNION ALL SELECT 'Российский государственный гуманитарный университет', 'РГГУ', 'РГГУ'
    UNION ALL SELECT 'Московский педагогический государственный университет', 'МПГУ', 'МПГУ'
    UNION ALL SELECT 'Московский городской педагогический университет', 'МГПУ', 'МГПУ'
    UNION ALL SELECT 'Московский государственный психолого-педагогический университет', 'МГППУ', 'МГППУ'
    UNION ALL SELECT 'Государственный университет управления', 'ГУУ', 'ГУУ'
    UNION ALL SELECT 'Российский государственный аграрный университет — МСХА имени К. А. Тимирязева', 'РГАУ-МСХА', 'Тимирязевка,МСХА'
    UNION ALL SELECT 'Московский государственный университет технологий и управления имени К. Г. Разумовского', 'МГУТУ им. К. Г. Разумовского', 'МГУТУ'
    UNION ALL SELECT 'Московский технический университет связи и информатики', 'МТУСИ', 'МТУСИ'
) AS seed
WHERE NOT EXISTS (
    SELECT 1 FROM universities AS existing
    WHERE LOWER(existing.short_name) = LOWER(seed.short_name)
);
