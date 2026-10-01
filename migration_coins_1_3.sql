-- FALLBACK ONLY.
-- The final replacement package applies these columns automatically at bot startup.
-- Run manually only if the database user has no ALTER permission during startup.

ALTER TABLE users
    ADD COLUMN first_attendance_bonus_awarded TINYINT(1) NOT NULL DEFAULT 0 AFTER coins;

ALTER TABLE event_feedback
    ADD COLUMN location_rating TINYINT NULL AFTER rating,
    ADD COLUMN speakers_rating TINYINT NULL AFTER location_rating,
    ADD COLUMN organization_rating TINYINT NULL AFTER speakers_rating,
    ADD COLUMN overall_rating TINYINT NULL AFTER organization_rating,
    ADD COLUMN liked_improve TEXT NULL AFTER comment,
    ADD COLUMN wishes TEXT NULL AFTER liked_improve,
    ADD COLUMN coins_awarded TINYINT(1) NOT NULL DEFAULT 0 AFTER wishes;
