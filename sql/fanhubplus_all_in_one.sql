-- =====================================================================
-- FAN HUB PLUS - COMPLETE DATABASE PACKAGE
-- This single file contains the base schema and all supplemental
-- CRUD, reporting, Use Case alignment, and Use Case gap-fix objects.
-- Target: MySQL 8.0.16+ / MariaDB 10.6+
-- Install: mysql -u root -p < fanhubplus_all_in_one.sql
-- WARNING: run on a test database first; the base script creates/uses
-- the fanhubplus database and the extensions alter that schema.
-- =====================================================================

-- =====================================================================
-- FAN HUB PLUS - COMPLETE DATABASE DESIGN (single-file install)
-- Contents : 26 tables, 3 views, 1 trigger, 2 functions, 29 procedures,
--            1 event, reference seed data.
-- Target   : MySQL 8.0.16+ / MariaDB 10.6+ (InnoDB, utf8mb4)
-- Install  : mysql -u root -p < fanhubplus_full.sql
-- Re-install: DROP DATABASE fanhubplus;  then run again.
-- Users are NOT seeded: create the admin/user accounts through the app
-- (passwords must be hashed with bcrypt/argon2).
-- =====================================================================
CREATE DATABASE IF NOT EXISTS fanhubplus
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE fanhubplus;

-- ---------------------------------------------------------------------
-- 1. USERS & AUTH
-- ---------------------------------------------------------------------
-- Visitor = not logged in (no row). Registered user / admin = row in users.
CREATE TABLE users (
  user_id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name              VARCHAR(100) NOT NULL,
  email             VARCHAR(255) NOT NULL,
  password_hash     VARCHAR(255) NOT NULL,
  role              ENUM('user','admin') NOT NULL DEFAULT 'user',
  avatar_url        VARCHAR(500) NULL,
  bio               VARCHAR(500) NULL,
  theme             ENUM('light','dark') NOT NULL DEFAULT 'light',          -- display preference
  font_size         ENUM('small','medium','large') NOT NULL DEFAULT 'medium', -- display preference
  is_active         BOOLEAN NOT NULL DEFAULT TRUE,
  email_verified_at DATETIME NULL,
  last_login_at     DATETIME NULL,                                           -- "active users" stats
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB;

-- Password reset + email verification (store only the HASH of the token)
CREATE TABLE user_tokens (
  token_id   INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id    INT UNSIGNED NOT NULL,
  purpose    ENUM('password_reset','email_verify') NOT NULL,
  token_hash CHAR(64) NOT NULL,
  expires_at DATETIME NOT NULL,
  used_at    DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (token_id),
  UNIQUE KEY uq_user_tokens_hash (token_hash),
  KEY idx_user_tokens_user (user_id, purpose),
  CONSTRAINT fk_user_tokens_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. CATEGORIES, FANDOMS, GENRES, TAGS
-- ---------------------------------------------------------------------
-- Category = the 8 top-level areas (Anime, Gaming, ...).
CREATE TABLE categories (
  category_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name        VARCHAR(50) NOT NULL,
  slug        VARCHAR(60) NOT NULL,
  description TEXT NULL,
  cover_url   VARCHAR(500) NULL,
  PRIMARY KEY (category_id),
  UNIQUE KEY uq_categories_name (name),
  UNIQUE KEY uq_categories_slug (slug)
) ENGINE=InnoDB;

-- Fandom = a specific universe/franchise/group inside a category
-- (e.g. "Attack on Titan" in Anime, "BTS" in K-Pop).
-- Design decision: one fandom belongs to ONE category. A franchise present
-- in two categories (anime + manga) is stored as two fandom rows.
CREATE TABLE fandoms (
  fandom_id   INT UNSIGNED NOT NULL AUTO_INCREMENT,
  category_id INT UNSIGNED NOT NULL,
  name        VARCHAR(120) NOT NULL,
  slug        VARCHAR(140) NOT NULL,
  description TEXT NULL,
  cover_url   VARCHAR(500) NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (fandom_id),
  UNIQUE KEY uq_fandoms_slug (slug),
  UNIQUE KEY uq_fandoms_cat_name (category_id, name),
  CONSTRAINT fk_fandoms_category FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

-- Profile: favourite categories / fandoms (many-to-many)
CREATE TABLE user_categories (
  user_id     INT UNSIGNED NOT NULL,
  category_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (user_id, category_id),
  CONSTRAINT fk_ucat_user     FOREIGN KEY (user_id)     REFERENCES users (user_id)           ON DELETE CASCADE,
  CONSTRAINT fk_ucat_category FOREIGN KEY (category_id) REFERENCES categories (category_id)  ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE user_fandoms (
  user_id   INT UNSIGNED NOT NULL,
  fandom_id INT UNSIGNED NOT NULL,
  PRIMARY KEY (user_id, fandom_id),
  CONSTRAINT fk_ufan_user   FOREIGN KEY (user_id)   REFERENCES users (user_id)     ON DELETE CASCADE,
  CONSTRAINT fk_ufan_fandom FOREIGN KEY (fandom_id) REFERENCES fandoms (fandom_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE genres (
  genre_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name     VARCHAR(60) NOT NULL,
  PRIMARY KEY (genre_id),
  UNIQUE KEY uq_genres_name (name)
) ENGINE=InnoDB;

-- Admin-controlled tags (media tagging, merchandise labels such as 'Limited Edition')
CREATE TABLE tags (
  tag_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name   VARCHAR(60) NOT NULL,
  PRIMARY KEY (tag_id),
  UNIQUE KEY uq_tags_name (name)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 3. CONTENT (articles, video, audio, image, trailer, explainer)
-- ---------------------------------------------------------------------
CREATE TABLE contents (
  content_id       INT UNSIGNED NOT NULL AUTO_INCREMENT,
  category_id      INT UNSIGNED NOT NULL,
  fandom_id        INT UNSIGNED NULL,
  title            VARCHAR(255) NOT NULL,
  slug             VARCHAR(280) NOT NULL,
  type             ENUM('article','video','audio','image','trailer','explainer') NOT NULL,
  summary          VARCHAR(500) NULL,
  description      TEXT NULL,
  body             LONGTEXT NULL,               -- rich text (HTML) for featured articles
  media_url        VARCHAR(500) NULL,           -- uploaded/hosted media file
  embed_url        VARCHAR(500) NULL,           -- YouTube/Vimeo/Spotify embed
  thumbnail_url    VARCHAR(500) NULL,
  duration_seconds INT UNSIGNED NULL,
  release_date     DATE NULL,                   -- future date => appears in Upcoming Releases
  popularity_score INT UNSIGNED NOT NULL DEFAULT 0,
  view_count       INT UNSIGNED NOT NULL DEFAULT 0,
  is_featured      BOOLEAN NOT NULL DEFAULT FALSE,
  status           ENUM('draft','published','archived') NOT NULL DEFAULT 'published',
  created_by       INT UNSIGNED NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (content_id),
  UNIQUE KEY uq_contents_slug (slug),
  KEY idx_contents_category (category_id, status),
  KEY idx_contents_fandom (fandom_id),
  KEY idx_contents_type (type),
  KEY idx_contents_release (release_date),
  KEY idx_contents_popularity (popularity_score),
  FULLTEXT KEY ft_contents_search (title, description),
  CONSTRAINT fk_contents_category FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE RESTRICT,
  CONSTRAINT fk_contents_fandom   FOREIGN KEY (fandom_id)   REFERENCES fandoms (fandom_id)      ON DELETE SET NULL,
  CONSTRAINT fk_contents_creator  FOREIGN KEY (created_by)  REFERENCES users (user_id)          ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE content_genres (
  content_id INT UNSIGNED NOT NULL,
  genre_id   INT UNSIGNED NOT NULL,
  PRIMARY KEY (content_id, genre_id),
  CONSTRAINT fk_cg_content FOREIGN KEY (content_id) REFERENCES contents (content_id) ON DELETE CASCADE,
  CONSTRAINT fk_cg_genre   FOREIGN KEY (genre_id)   REFERENCES genres (genre_id)     ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE content_tags (
  content_id INT UNSIGNED NOT NULL,
  tag_id     INT UNSIGNED NOT NULL,
  PRIMARY KEY (content_id, tag_id),
  CONSTRAINT fk_ct_content FOREIGN KEY (content_id) REFERENCES contents (content_id) ON DELETE CASCADE,
  CONSTRAINT fk_ct_tag     FOREIGN KEY (tag_id)     REFERENCES tags (tag_id)         ON DELETE CASCADE
) ENGINE=InnoDB;

-- Image gallery for a content item
CREATE TABLE content_images (
  image_id   INT UNSIGNED NOT NULL AUTO_INCREMENT,
  content_id INT UNSIGNED NOT NULL,
  image_url  VARCHAR(500) NOT NULL,
  caption    VARCHAR(255) NULL,
  sort_order INT NOT NULL DEFAULT 0,
  PRIMARY KEY (image_id),
  KEY idx_ci_content (content_id, sort_order),
  CONSTRAINT fk_ci_content FOREIGN KEY (content_id) REFERENCES contents (content_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Timeline / storytelling entries for articles and event highlights
CREATE TABLE content_timeline_entries (
  entry_id    INT UNSIGNED NOT NULL AUTO_INCREMENT,
  content_id  INT UNSIGNED NOT NULL,
  entry_date  DATE NULL,
  title       VARCHAR(200) NOT NULL,
  description TEXT NULL,
  image_url   VARCHAR(500) NULL,
  sort_order  INT NOT NULL DEFAULT 0,
  PRIMARY KEY (entry_id),
  KEY idx_cte_content (content_id, sort_order),
  CONSTRAINT fk_cte_content FOREIGN KEY (content_id) REFERENCES contents (content_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 4. CHARACTER PROFILES
-- ---------------------------------------------------------------------
CREATE TABLE character_profiles (
  character_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
  category_id  INT UNSIGNED NOT NULL,
  fandom_id    INT UNSIGNED NULL,
  name         VARCHAR(150) NOT NULL,
  alias        VARCHAR(150) NULL,
  bio          TEXT NULL,
  image_url    VARCHAR(500) NULL,
  view_count   INT UNSIGNED NOT NULL DEFAULT 0,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (character_id),
  KEY idx_char_category (category_id),
  KEY idx_char_fandom (fandom_id),
  KEY idx_char_name (name),
  FULLTEXT KEY ft_char_search (name, alias, bio),
  CONSTRAINT fk_char_category FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE RESTRICT,
  CONSTRAINT fk_char_fandom   FOREIGN KEY (fandom_id)   REFERENCES fandoms (fandom_id)      ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 5. MERCHANDISE SHOWCASE (display only - no orders/payments)
-- ---------------------------------------------------------------------
CREATE TABLE merchandise_items (
  item_id       INT UNSIGNED NOT NULL AUTO_INCREMENT,
  category_id   INT UNSIGNED NOT NULL,
  fandom_id     INT UNSIGNED NULL,
  name          VARCHAR(200) NOT NULL,
  description   TEXT NULL,
  image_url     VARCHAR(500) NULL,
  reference_url VARCHAR(500) NULL,              -- link to official page (info only)
  release_date  DATE NULL,
  is_upcoming   BOOLEAN NOT NULL DEFAULT FALSE,
  view_count    INT UNSIGNED NOT NULL DEFAULT 0,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (item_id),
  KEY idx_merch_category (category_id),
  KEY idx_merch_fandom (fandom_id),
  KEY idx_merch_upcoming (is_upcoming, release_date),
  CONSTRAINT fk_merch_category FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE RESTRICT,
  CONSTRAINT fk_merch_fandom   FOREIGN KEY (fandom_id)   REFERENCES fandoms (fandom_id)      ON DELETE SET NULL
) ENGINE=InnoDB;

-- Several tags per item ('Limited Edition' + 'Pre-Order' ...)
CREATE TABLE merchandise_tags (
  item_id INT UNSIGNED NOT NULL,
  tag_id  INT UNSIGNED NOT NULL,
  PRIMARY KEY (item_id, tag_id),
  CONSTRAINT fk_mt_item FOREIGN KEY (item_id) REFERENCES merchandise_items (item_id) ON DELETE CASCADE,
  CONSTRAINT fk_mt_tag  FOREIGN KEY (tag_id)  REFERENCES tags (tag_id)               ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE merchandise_images (
  image_id   INT UNSIGNED NOT NULL AUTO_INCREMENT,
  item_id    INT UNSIGNED NOT NULL,
  image_url  VARCHAR(500) NOT NULL,
  caption    VARCHAR(255) NULL,
  sort_order INT NOT NULL DEFAULT 0,
  PRIMARY KEY (image_id),
  KEY idx_mi_item (item_id, sort_order),
  CONSTRAINT fk_mi_item FOREIGN KEY (item_id) REFERENCES merchandise_items (item_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 6. BOOKMARKS, NOTES, SHARING, RATINGS
-- ---------------------------------------------------------------------
-- One bookmark points to exactly ONE of: content / character / merchandise.
-- (Enforced by trigger trg_bookmarks_one_target at the bottom of this file.)
CREATE TABLE bookmarks (
  bookmark_id    INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id        INT UNSIGNED NOT NULL,
  content_id     INT UNSIGNED NULL,
  character_id   INT UNSIGNED NULL,
  merchandise_id INT UNSIGNED NULL,
  note           TEXT NULL,
  share_token    CHAR(32) NULL,                 -- optional public share link
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (bookmark_id),
  UNIQUE KEY uq_bm_share (share_token),
  UNIQUE KEY uq_bm_content (user_id, content_id),
  UNIQUE KEY uq_bm_character (user_id, character_id),
  UNIQUE KEY uq_bm_merch (user_id, merchandise_id),
  CONSTRAINT fk_bm_user      FOREIGN KEY (user_id)        REFERENCES users (user_id)                 ON DELETE CASCADE,
  CONSTRAINT fk_bm_content   FOREIGN KEY (content_id)     REFERENCES contents (content_id)           ON DELETE CASCADE,
  CONSTRAINT fk_bm_character FOREIGN KEY (character_id)   REFERENCES character_profiles (character_id) ON DELETE CASCADE,
  CONSTRAINT fk_bm_merch     FOREIGN KEY (merchandise_id) REFERENCES merchandise_items (item_id)     ON DELETE CASCADE
) ENGINE=InnoDB;

-- 5-star rating, one per user per content item
CREATE TABLE content_ratings (
  rating_id  INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id    INT UNSIGNED NOT NULL,
  content_id INT UNSIGNED NOT NULL,
  score      TINYINT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (rating_id),
  UNIQUE KEY uq_rating_user_content (user_id, content_id),
  KEY idx_rating_content (content_id),
  CONSTRAINT chk_rating_score CHECK (score BETWEEN 1 AND 5),
  CONSTRAINT fk_rating_user    FOREIGN KEY (user_id)    REFERENCES users (user_id)       ON DELETE CASCADE,
  CONSTRAINT fk_rating_content FOREIGN KEY (content_id) REFERENCES contents (content_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 7. CHATBOT (optional feature)
-- ---------------------------------------------------------------------
CREATE TABLE chatbot_faqs (
  faq_id      INT UNSIGNED NOT NULL AUTO_INCREMENT,
  category_id INT UNSIGNED NULL,
  question    TEXT NOT NULL,
  answer      TEXT NOT NULL,
  keywords    VARCHAR(500) NULL,
  is_active   BOOLEAN NOT NULL DEFAULT TRUE,
  created_by  INT UNSIGNED NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (faq_id),
  FULLTEXT KEY ft_faq_search (question, keywords),
  CONSTRAINT fk_faq_category FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE SET NULL,
  CONSTRAINT fk_faq_creator  FOREIGN KEY (created_by)  REFERENCES users (user_id)          ON DELETE SET NULL
) ENGINE=InnoDB;

-- A conversation. user_id NULL = visitor. current_step drives the multi-step onboarding flow.
CREATE TABLE chat_sessions (
  session_id            INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id               INT UNSIGNED NULL,
  session_token         CHAR(36) NOT NULL,
  current_step          TINYINT UNSIGNED NOT NULL DEFAULT 0,
  onboarding_completed  BOOLEAN NOT NULL DEFAULT FALSE,
  started_at            DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_activity_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (session_id),
  UNIQUE KEY uq_chat_token (session_token),
  KEY idx_chat_user (user_id),
  CONSTRAINT fk_chat_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

CREATE TABLE chatbot_queries (
  query_id       INT UNSIGNED NOT NULL AUTO_INCREMENT,
  session_id     INT UNSIGNED NOT NULL,
  user_id        INT UNSIGNED NULL,
  message        TEXT NOT NULL,
  response       TEXT NULL,
  matched_faq_id INT UNSIGNED NULL,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (query_id),
  KEY idx_cq_session (session_id, created_at),
  KEY idx_cq_created (created_at),                       -- chatbot interaction volume stats
  CONSTRAINT fk_cq_session FOREIGN KEY (session_id)     REFERENCES chat_sessions (session_id) ON DELETE CASCADE,
  CONSTRAINT fk_cq_user    FOREIGN KEY (user_id)        REFERENCES users (user_id)            ON DELETE SET NULL,
  CONSTRAINT fk_cq_faq     FOREIGN KEY (matched_faq_id) REFERENCES chatbot_faqs (faq_id)      ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 8. FEEDBACK
-- ---------------------------------------------------------------------
CREATE TABLE feedbacks (
  feedback_id    INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id        INT UNSIGNED NULL,               -- NULL = visitor
  contact_email  VARCHAR(255) NULL,
  type           ENUM('bug','suggestion','query') NOT NULL,
  subject        VARCHAR(200) NOT NULL,
  message        TEXT NOT NULL,
  status         ENUM('new','in_progress','resolved','closed') NOT NULL DEFAULT 'new',
  admin_response TEXT NULL,
  handled_by     INT UNSIGNED NULL,
  resolved_at    DATETIME NULL,
  created_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (feedback_id),
  KEY idx_fb_status (status, type),
  CONSTRAINT fk_fb_user    FOREIGN KEY (user_id)    REFERENCES users (user_id) ON DELETE SET NULL,
  CONSTRAINT fk_fb_handler FOREIGN KEY (handled_by) REFERENCES users (user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 9. EVENTS (map + calendar)
-- ---------------------------------------------------------------------
CREATE TABLE events (
  event_id    INT UNSIGNED NOT NULL AUTO_INCREMENT,
  category_id INT UNSIGNED NULL,
  fandom_id   INT UNSIGNED NULL,
  title       VARCHAR(255) NOT NULL,
  description TEXT NULL,
  event_type  ENUM('convention','cosplay_meetup','screening','premiere','other') NOT NULL DEFAULT 'other',
  venue       VARCHAR(255) NULL,
  address     VARCHAR(255) NULL,
  city        VARCHAR(100) NOT NULL,
  country     VARCHAR(100) NULL,
  latitude    DECIMAL(9,6) NULL,
  longitude   DECIMAL(9,6) NULL,
  start_at    DATETIME NOT NULL,
  end_at      DATETIME NULL,
  ticket_url  VARCHAR(500) NULL,
  cover_url   VARCHAR(500) NULL,
  created_by  INT UNSIGNED NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (event_id),
  KEY idx_events_city (city),
  KEY idx_events_start (start_at),
  KEY idx_events_geo (latitude, longitude),
  CONSTRAINT chk_events_lat CHECK (latitude  IS NULL OR latitude  BETWEEN -90  AND 90),
  CONSTRAINT chk_events_lng CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
  CONSTRAINT fk_events_category FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE SET NULL,
  CONSTRAINT fk_events_fandom   FOREIGN KEY (fandom_id)   REFERENCES fandoms (fandom_id)      ON DELETE SET NULL,
  CONSTRAINT fk_events_creator  FOREIGN KEY (created_by)  REFERENCES users (user_id)          ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 10. FAN SUBMISSIONS (admin approval workflow)
-- ---------------------------------------------------------------------
CREATE TABLE fan_submissions (
  submission_id        INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id              INT UNSIGNED NOT NULL,
  category_id          INT UNSIGNED NOT NULL,
  title                VARCHAR(255) NOT NULL,
  body                 LONGTEXT NOT NULL,
  cover_image_url      VARCHAR(500) NULL,
  status               ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending',
  reviewed_by          INT UNSIGNED NULL,
  reviewed_at          DATETIME NULL,
  reject_reason        VARCHAR(500) NULL,
  published_content_id INT UNSIGNED NULL,          -- set when approved and published as content
  created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (submission_id),
  KEY idx_fs_status (status, created_at),
  KEY idx_fs_user (user_id),
  CONSTRAINT fk_fs_user      FOREIGN KEY (user_id)              REFERENCES users (user_id)           ON DELETE CASCADE,
  CONSTRAINT fk_fs_category  FOREIGN KEY (category_id)          REFERENCES categories (category_id)  ON DELETE RESTRICT,
  CONSTRAINT fk_fs_reviewer  FOREIGN KEY (reviewed_by)          REFERENCES users (user_id)           ON DELETE SET NULL,
  CONSTRAINT fk_fs_published FOREIGN KEY (published_content_id) REFERENCES contents (content_id)     ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 11. ACTIVITY LOG (dashboard "recent activity" + admin statistics)
-- ---------------------------------------------------------------------
CREATE TABLE activity_logs (
  log_id      BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id     INT UNSIGNED NULL,
  action      VARCHAR(50) NOT NULL,                -- e.g. login, bookmark_add, rating_add, view
  entity_type VARCHAR(30) NULL,                    -- content / character / merchandise / event ...
  entity_id   INT UNSIGNED NULL,
  details     VARCHAR(255) NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (log_id),
  KEY idx_al_user (user_id, created_at),
  KEY idx_al_created (created_at),
  CONSTRAINT fk_al_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 12. VIEWS
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_content_rating_stats AS
SELECT c.content_id,
       ROUND(AVG(r.score), 2) AS avg_score,
       COUNT(r.rating_id)     AS rating_count
FROM contents c
LEFT JOIN content_ratings r ON r.content_id = c.content_id
GROUP BY c.content_id;

-- Upcoming releases = future-dated content + merchandise flagged as upcoming
CREATE OR REPLACE VIEW v_upcoming_releases AS
SELECT 'content' AS source, content_id AS id, category_id, title AS name, release_date
FROM contents
WHERE status = 'published' AND release_date > CURDATE()
UNION ALL
SELECT 'merchandise', item_id, category_id, name, release_date
FROM merchandise_items
WHERE is_upcoming = TRUE;

CREATE OR REPLACE VIEW v_category_popularity AS
SELECT cat.category_id,
       cat.name,
       COUNT(c.content_id)              AS content_count,
       COALESCE(SUM(c.view_count), 0)   AS total_views
FROM categories cat
LEFT JOIN contents c ON c.category_id = cat.category_id
GROUP BY cat.category_id, cat.name;

-- ---------------------------------------------------------------------
-- 13. SEED DATA (reference data only)
-- ---------------------------------------------------------------------
INSERT INTO categories (name, slug, description) VALUES
 ('Anime',    'anime',    'Japanese animated series and films'),
 ('Gaming',   'gaming',   'Video games, esports and game culture'),
 ('Movies',   'movies',   'Feature films and cinema news'),
 ('TV Shows', 'tv-shows', 'Television series and streaming shows'),
 ('K-Pop',    'k-pop',    'Korean pop music, idols and groups'),
 ('Comics',   'comics',   'Western comics and graphic novels'),
 ('Manga',    'manga',    'Japanese comics and light novels'),
 ('Cosplay',  'cosplay',  'Costume play, craftsmanship and events');

INSERT INTO genres (name) VALUES
 ('Action'),('Adventure'),('Comedy'),('Drama'),('Fantasy'),('Horror'),
 ('Romance'),('Sci-Fi'),('Slice of Life'),('Thriller'),('Music'),('Sports');

INSERT INTO tags (name) VALUES
 ('Limited Edition'),('Pre-Order'),('Collectible'),('Exclusive'),('Official'),('Fan Made'),('Trailer'),('Soundtrack');

INSERT INTO chatbot_faqs (question, answer, keywords) VALUES
 ('What is Fan Hub Plus?', 'Fan Hub Plus is a portal that brings anime, gaming, movies, TV, K-Pop, comics, manga and cosplay fandoms together in one place.', 'about platform what is'),
 ('How do I bookmark an item?', 'Log in, open any article, character, video or merchandise item, then click the bookmark icon. You can add a private note too.', 'bookmark save favorite note'),
 ('Can I buy merchandise here?', 'No. The merchandise showcase is for display and discovery only; there are no orders or payments on this site.', 'buy merchandise purchase payment'),
 ('How do I submit my own article?', 'Registered users can submit fan content from their dashboard. An administrator reviews it before it is published.', 'submit fan article content approval');

-- ---------------------------------------------------------------------
-- 14. TRIGGER: a bookmark must reference exactly one target
-- (MySQL forbids CHECK constraints on columns used in FK cascade actions,
--  so this rule is enforced with a trigger instead.)
-- ---------------------------------------------------------------------
DELIMITER $$
CREATE TRIGGER trg_bookmarks_one_target
BEFORE INSERT ON bookmarks
FOR EACH ROW
BEGIN
  IF (NEW.content_id IS NOT NULL) + (NEW.character_id IS NOT NULL) + (NEW.merchandise_id IS NOT NULL) <> 1 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'A bookmark must reference exactly one of content, character or merchandise';
  END IF;
END$$
DELIMITER ;

USE fanhubplus;

DELIMITER $$

-- ---------------------------------------------------------------------
-- HELPERS (functions)
-- ---------------------------------------------------------------------
DROP FUNCTION IF EXISTS fn_is_admin$$
CREATE FUNCTION fn_is_admin(p_user_id INT UNSIGNED) RETURNS BOOLEAN
READS SQL DATA
BEGIN
  DECLARE v_count INT DEFAULT 0;
  SELECT COUNT(*) INTO v_count
    FROM users
   WHERE user_id = p_user_id AND role = 'admin' AND is_active = TRUE;
  RETURN v_count > 0;
END$$

-- Popularity = views + 5*ratings + 10*avg_score + 3*bookmarks
DROP FUNCTION IF EXISTS fn_popularity_score$$
CREATE FUNCTION fn_popularity_score(p_content_id INT UNSIGNED) RETURNS INT UNSIGNED
READS SQL DATA
BEGIN
  DECLARE v_views INT UNSIGNED DEFAULT 0;
  DECLARE v_cnt   INT DEFAULT 0;
  DECLARE v_avg   DECIMAL(4,2) DEFAULT 0;
  DECLARE v_bm    INT DEFAULT 0;
  SELECT view_count INTO v_views FROM contents WHERE content_id = p_content_id;
  SELECT COUNT(*), COALESCE(AVG(score), 0) INTO v_cnt, v_avg
    FROM content_ratings WHERE content_id = p_content_id;
  SELECT COUNT(*) INTO v_bm FROM bookmarks WHERE content_id = p_content_id;
  RETURN COALESCE(v_views, 0) + v_cnt * 5 + ROUND(v_avg * 10) + v_bm * 3;
END$$

DROP PROCEDURE IF EXISTS sp_log_activity$$
CREATE PROCEDURE sp_log_activity(
  IN p_user_id INT UNSIGNED, IN p_action VARCHAR(50),
  IN p_entity_type VARCHAR(30), IN p_entity_id INT UNSIGNED, IN p_details VARCHAR(255))
BEGIN
  INSERT INTO activity_logs (user_id, action, entity_type, entity_id, details)
  VALUES (p_user_id, p_action, p_entity_type, p_entity_id, p_details);
END$$

-- =====================================================================
-- A. USERS & AUTHENTICATION
-- =====================================================================

-- A1. Register (user row + activity log = one unit of work)
DROP PROCEDURE IF EXISTS sp_register_user$$
CREATE PROCEDURE sp_register_user(
  IN p_name VARCHAR(100), IN p_email VARCHAR(255), IN p_password_hash VARCHAR(255),
  OUT p_user_id INT UNSIGNED)
BEGIN
  DECLARE EXIT HANDLER FOR 1062
  BEGIN
    ROLLBACK;
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Email already registered';
  END;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_name IS NULL OR TRIM(p_name) = '' OR p_email IS NULL OR p_email NOT LIKE '%_@_%.__%' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid name or email';
  END IF;

  START TRANSACTION;
  INSERT INTO users (name, email, password_hash)
  VALUES (TRIM(p_name), LOWER(TRIM(p_email)), p_password_hash);
  SET p_user_id = LAST_INSERT_ID();
  CALL sp_log_activity(p_user_id, 'register', 'user', p_user_id, NULL);
  COMMIT;
END$$

-- A2. Login step 1: fetch the record; the APPLICATION verifies the hash
DROP PROCEDURE IF EXISTS sp_get_user_for_login$$
CREATE PROCEDURE sp_get_user_for_login(IN p_email VARCHAR(255))
BEGIN
  SELECT user_id, name, password_hash, role, is_active, email_verified_at
    FROM users WHERE email = LOWER(TRIM(p_email));
END$$

-- A3. Login step 2: after the hash matched
DROP PROCEDURE IF EXISTS sp_login_success$$
CREATE PROCEDURE sp_login_success(IN p_user_id INT UNSIGNED)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  SELECT user_id INTO v_id FROM users WHERE user_id = p_user_id AND is_active = TRUE FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'User not found or inactive';
  END IF;
  UPDATE users SET last_login_at = NOW() WHERE user_id = p_user_id;
  CALL sp_log_activity(p_user_id, 'login', 'user', p_user_id, NULL);
  COMMIT;
END$$

-- A4. Issue a reset / verification token (old unused ones are invalidated)
--     The app generates a random token, sends it by e-mail, stores only SHA-256 hash here.
DROP PROCEDURE IF EXISTS sp_create_user_token$$
CREATE PROCEDURE sp_create_user_token(
  IN p_user_id INT UNSIGNED, IN p_purpose VARCHAR(20),
  IN p_token_hash CHAR(64), IN p_ttl_minutes INT)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_purpose NOT IN ('password_reset', 'email_verify') OR p_ttl_minutes IS NULL OR p_ttl_minutes <= 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid token purpose or lifetime';
  END IF;

  START TRANSACTION;
  UPDATE user_tokens SET used_at = NOW()
   WHERE user_id = p_user_id AND purpose = p_purpose AND used_at IS NULL;
  INSERT INTO user_tokens (user_id, purpose, token_hash, expires_at)
  VALUES (p_user_id, p_purpose, p_token_hash, NOW() + INTERVAL p_ttl_minutes MINUTE);
  COMMIT;
END$$

-- A5. Reset password: lock token -> validate -> change password -> burn token(s)
DROP PROCEDURE IF EXISTS sp_reset_password$$
CREATE PROCEDURE sp_reset_password(IN p_token_hash CHAR(64), IN p_new_password_hash VARCHAR(255))
BEGIN
  DECLARE v_token_id INT UNSIGNED DEFAULT NULL;
  DECLARE v_user_id  INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  SELECT token_id, user_id INTO v_token_id, v_user_id
    FROM user_tokens
   WHERE token_hash = p_token_hash AND purpose = 'password_reset'
     AND used_at IS NULL AND expires_at > NOW()
     FOR UPDATE;
  IF v_token_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid or expired token';
  END IF;

  UPDATE users SET password_hash = p_new_password_hash WHERE user_id = v_user_id;
  UPDATE user_tokens SET used_at = NOW()
   WHERE user_id = v_user_id AND purpose = 'password_reset' AND used_at IS NULL;
  CALL sp_log_activity(v_user_id, 'password_reset', 'user', v_user_id, NULL);
  COMMIT;
END$$

-- A6. Verify e-mail
DROP PROCEDURE IF EXISTS sp_verify_email$$
CREATE PROCEDURE sp_verify_email(IN p_token_hash CHAR(64))
BEGIN
  DECLARE v_token_id INT UNSIGNED DEFAULT NULL;
  DECLARE v_user_id  INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  SELECT token_id, user_id INTO v_token_id, v_user_id
    FROM user_tokens
   WHERE token_hash = p_token_hash AND purpose = 'email_verify'
     AND used_at IS NULL AND expires_at > NOW()
     FOR UPDATE;
  IF v_token_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid or expired token';
  END IF;

  UPDATE users SET email_verified_at = NOW() WHERE user_id = v_user_id;
  UPDATE user_tokens SET used_at = NOW() WHERE token_id = v_token_id;
  CALL sp_log_activity(v_user_id, 'email_verified', 'user', v_user_id, NULL);
  COMMIT;
END$$

-- A7. Replace favourite categories / fandoms atomically.
--     NULL = leave unchanged, [] = clear, [1,2,3] = replace with these ids.
--     If any id is invalid the FK fails and the OLD favourites are kept.
DROP PROCEDURE IF EXISTS sp_set_user_favorites$$
CREATE PROCEDURE sp_set_user_favorites(
  IN p_user_id INT UNSIGNED, IN p_category_ids JSON, IN p_fandom_ids JSON)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  IF p_category_ids IS NOT NULL THEN
    DELETE FROM user_categories WHERE user_id = p_user_id;
    INSERT INTO user_categories (user_id, category_id)
    SELECT DISTINCT p_user_id, jt.id
      FROM JSON_TABLE(p_category_ids, '$[*]' COLUMNS (id INT UNSIGNED PATH '$')) AS jt;
  END IF;
  IF p_fandom_ids IS NOT NULL THEN
    DELETE FROM user_fandoms WHERE user_id = p_user_id;
    INSERT INTO user_fandoms (user_id, fandom_id)
    SELECT DISTINCT p_user_id, jt.id
      FROM JSON_TABLE(p_fandom_ids, '$[*]' COLUMNS (id INT UNSIGNED PATH '$')) AS jt;
  END IF;
  CALL sp_log_activity(p_user_id, 'update_favorites', 'user', p_user_id, NULL);
  COMMIT;
END$$

-- A8. Personalised dashboard (5 result sets)
DROP PROCEDURE IF EXISTS sp_get_dashboard$$
CREATE PROCEDURE sp_get_dashboard(IN p_user_id INT UNSIGNED)
BEGIN
  -- 1) profile (the app builds the greeting from name / time of day)
  SELECT user_id, name, avatar_url, theme, font_size, last_login_at
    FROM users WHERE user_id = p_user_id;
  -- 2) favourite categories
  SELECT c.category_id, c.name, c.slug
    FROM user_categories uc JOIN categories c ON c.category_id = uc.category_id
   WHERE uc.user_id = p_user_id ORDER BY c.name;
  -- 3) favourite fandoms
  SELECT f.fandom_id, f.name, f.slug, f.cover_url
    FROM user_fandoms uf JOIN fandoms f ON f.fandom_id = uf.fandom_id
   WHERE uf.user_id = p_user_id ORDER BY f.name;
  -- 4) bookmarks (content + characters + merchandise)
  SELECT * FROM (
    SELECT b.bookmark_id, 'content' AS item_type, c.content_id AS item_id,
           c.title AS title, c.thumbnail_url AS image_url, b.note, b.created_at
      FROM bookmarks b JOIN contents c ON c.content_id = b.content_id
     WHERE b.user_id = p_user_id
    UNION ALL
    SELECT b.bookmark_id, 'character', ch.character_id, ch.name, ch.image_url, b.note, b.created_at
      FROM bookmarks b JOIN character_profiles ch ON ch.character_id = b.character_id
     WHERE b.user_id = p_user_id
    UNION ALL
    SELECT b.bookmark_id, 'merchandise', m.item_id, m.name, m.image_url, b.note, b.created_at
      FROM bookmarks b JOIN merchandise_items m ON m.item_id = b.merchandise_id
     WHERE b.user_id = p_user_id
  ) x ORDER BY created_at DESC;
  -- 5) recent activity
  SELECT action, entity_type, entity_id, details, created_at
    FROM activity_logs WHERE user_id = p_user_id
   ORDER BY created_at DESC, log_id DESC LIMIT 10;
END$$

-- =====================================================================
-- B. CONTENT EXPLORER
-- =====================================================================

-- B1. Multi-level search / filter / sort with pagination.
--     Any parameter may be NULL (= no filter).  p_sort: latest | popular | alpha
--     total_count is the number of matches BEFORE LIMIT (for page numbers).
DROP PROCEDURE IF EXISTS sp_search_contents$$
CREATE PROCEDURE sp_search_contents(
  IN p_query VARCHAR(100), IN p_category_id INT UNSIGNED, IN p_fandom_id INT UNSIGNED,
  IN p_genre_id INT UNSIGNED, IN p_type VARCHAR(20), IN p_year SMALLINT,
  IN p_sort VARCHAR(20), IN p_limit INT, IN p_offset INT)
BEGIN
  SET p_limit  = LEAST(GREATEST(COALESCE(p_limit, 12), 1), 100);
  SET p_offset = GREATEST(COALESCE(p_offset, 0), 0);
  SET p_sort   = COALESCE(p_sort, 'latest');

  SELECT c.content_id, c.title, c.slug, c.type, c.summary, c.thumbnail_url,
         c.category_id, cat.name AS category_name, c.fandom_id, c.release_date,
         c.popularity_score, c.view_count,
         COALESCE(rs.avg_score, 0) AS avg_score, COALESCE(rs.rating_count, 0) AS rating_count,
         COUNT(*) OVER () AS total_count
    FROM contents c
    JOIN categories cat ON cat.category_id = c.category_id
    LEFT JOIN (SELECT content_id, ROUND(AVG(score), 2) AS avg_score, COUNT(*) AS rating_count
                 FROM content_ratings GROUP BY content_id) rs ON rs.content_id = c.content_id
   WHERE c.status = 'published'
     AND (p_category_id IS NULL OR c.category_id = p_category_id)
     AND (p_fandom_id   IS NULL OR c.fandom_id   = p_fandom_id)
     AND (p_type        IS NULL OR c.type        = p_type)
     AND (p_year IS NULL OR (c.release_date >= MAKEDATE(p_year, 1) AND c.release_date < MAKEDATE(p_year + 1, 1)))
     AND (p_genre_id IS NULL OR EXISTS (SELECT 1 FROM content_genres cg
                                         WHERE cg.content_id = c.content_id AND cg.genre_id = p_genre_id))
     AND (p_query IS NULL OR p_query = ''
          OR c.title LIKE CONCAT('%', p_query, '%') OR c.description LIKE CONCAT('%', p_query, '%'))
   ORDER BY CASE WHEN p_sort = 'popular' THEN c.popularity_score END DESC,
            CASE WHEN p_sort = 'alpha'   THEN c.title END ASC,
            COALESCE(c.release_date, DATE(c.created_at)) DESC, c.content_id DESC
   LIMIT p_limit OFFSET p_offset;
END$$

-- B2. Open a content page: count the view + refresh popularity (transaction),
--     then return 6 result sets.
DROP PROCEDURE IF EXISTS sp_get_content_detail$$
CREATE PROCEDURE sp_get_content_detail(IN p_content_id INT UNSIGNED, IN p_user_id INT UNSIGNED)
BEGIN
  DECLARE v_pop INT UNSIGNED DEFAULT 0;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  UPDATE contents SET view_count = view_count + 1        -- atomic, no lost update
   WHERE content_id = p_content_id AND status = 'published';
  IF ROW_COUNT() = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Content not found';
  END IF;
  SET v_pop = fn_popularity_score(p_content_id);
  UPDATE contents SET popularity_score = v_pop WHERE content_id = p_content_id;
  IF p_user_id IS NOT NULL THEN
    CALL sp_log_activity(p_user_id, 'view', 'content', p_content_id, NULL);
  END IF;
  COMMIT;

  -- 1) content
  SELECT c.*, cat.name AS category_name, f.name AS fandom_name,
         (SELECT ROUND(AVG(score), 2) FROM content_ratings WHERE content_id = c.content_id) AS avg_score,
         (SELECT COUNT(*)             FROM content_ratings WHERE content_id = c.content_id) AS rating_count
    FROM contents c
    JOIN categories cat ON cat.category_id = c.category_id
    LEFT JOIN fandoms f ON f.fandom_id = c.fandom_id
   WHERE c.content_id = p_content_id;
  -- 2) genres   3) tags   4) gallery   5) timeline
  SELECT g.genre_id, g.name FROM content_genres cg JOIN genres g ON g.genre_id = cg.genre_id
   WHERE cg.content_id = p_content_id;
  SELECT t.tag_id, t.name FROM content_tags ct JOIN tags t ON t.tag_id = ct.tag_id
   WHERE ct.content_id = p_content_id;
  SELECT image_id, image_url, caption FROM content_images
   WHERE content_id = p_content_id ORDER BY sort_order, image_id;
  SELECT entry_id, entry_date, title, description, image_url FROM content_timeline_entries
   WHERE content_id = p_content_id ORDER BY sort_order, entry_date;
  -- 6) state of the logged-in user (NULL / 0 for visitors)
  SELECT (SELECT score FROM content_ratings WHERE user_id = p_user_id AND content_id = p_content_id) AS my_rating,
         EXISTS (SELECT 1 FROM bookmarks WHERE user_id = p_user_id AND content_id = p_content_id) AS is_bookmarked;
END$$

-- B3. Merchandise page: count the view, return item + tags + gallery
DROP PROCEDURE IF EXISTS sp_view_merchandise$$
CREATE PROCEDURE sp_view_merchandise(IN p_item_id INT UNSIGNED)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  UPDATE merchandise_items SET view_count = view_count + 1 WHERE item_id = p_item_id;
  IF ROW_COUNT() = 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Merchandise item not found';
  END IF;
  COMMIT;

  SELECT m.*, cat.name AS category_name FROM merchandise_items m
    JOIN categories cat ON cat.category_id = m.category_id WHERE m.item_id = p_item_id;
  SELECT t.tag_id, t.name FROM merchandise_tags mt JOIN tags t ON t.tag_id = mt.tag_id
   WHERE mt.item_id = p_item_id;
  SELECT image_id, image_url, caption FROM merchandise_images
   WHERE item_id = p_item_id ORDER BY sort_order, image_id;
END$$

-- B4. Rate (insert or change) a content item
DROP PROCEDURE IF EXISTS sp_rate_content$$
CREATE PROCEDURE sp_rate_content(
  IN p_user_id INT UNSIGNED, IN p_content_id INT UNSIGNED, IN p_score TINYINT UNSIGNED)
BEGIN
  DECLARE v_lock INT UNSIGNED DEFAULT NULL;
  DECLARE v_pop  INT UNSIGNED DEFAULT 0;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_score IS NULL OR p_score NOT BETWEEN 1 AND 5 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Score must be between 1 and 5';
  END IF;

  START TRANSACTION;
  SELECT content_id INTO v_lock FROM contents WHERE content_id = p_content_id FOR UPDATE; -- lock first
  IF v_lock IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Content not found';
  END IF;
  INSERT INTO content_ratings (user_id, content_id, score)
  VALUES (p_user_id, p_content_id, p_score)
  ON DUPLICATE KEY UPDATE score = p_score;
  SET v_pop = fn_popularity_score(p_content_id);
  UPDATE contents SET popularity_score = v_pop WHERE content_id = p_content_id;
  CALL sp_log_activity(p_user_id, 'rate', 'content', p_content_id, CONCAT('score=', p_score));
  COMMIT;
END$$

-- =====================================================================
-- C. BOOKMARKS, NOTES, SHARING
-- =====================================================================

-- C1. Add a bookmark (or update its note if it already exists).
--     p_target_type: content | character | merchandise
DROP PROCEDURE IF EXISTS sp_add_bookmark$$
CREATE PROCEDURE sp_add_bookmark(
  IN p_user_id INT UNSIGNED, IN p_target_type VARCHAR(20), IN p_target_id INT UNSIGNED,
  IN p_note TEXT, OUT p_bookmark_id INT UNSIGNED)
BEGIN
  DECLARE v_lock INT UNSIGNED DEFAULT NULL;
  DECLARE v_pop  INT UNSIGNED DEFAULT 0;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_target_type NOT IN ('content', 'character', 'merchandise') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid bookmark target type';
  END IF;

  START TRANSACTION;
  IF p_target_type = 'content' THEN
    SELECT content_id INTO v_lock FROM contents WHERE content_id = p_target_id FOR UPDATE;
    IF v_lock IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Content not found'; END IF;
    INSERT INTO bookmarks (user_id, content_id, note) VALUES (p_user_id, p_target_id, p_note)
      ON DUPLICATE KEY UPDATE note = COALESCE(p_note, note);
    SELECT bookmark_id INTO p_bookmark_id FROM bookmarks WHERE user_id = p_user_id AND content_id = p_target_id;
    SET v_pop = fn_popularity_score(p_target_id);
    UPDATE contents SET popularity_score = v_pop WHERE content_id = p_target_id;
  ELSEIF p_target_type = 'character' THEN
    INSERT INTO bookmarks (user_id, character_id, note) VALUES (p_user_id, p_target_id, p_note)
      ON DUPLICATE KEY UPDATE note = COALESCE(p_note, note);
    SELECT bookmark_id INTO p_bookmark_id FROM bookmarks WHERE user_id = p_user_id AND character_id = p_target_id;
  ELSE
    INSERT INTO bookmarks (user_id, merchandise_id, note) VALUES (p_user_id, p_target_id, p_note)
      ON DUPLICATE KEY UPDATE note = COALESCE(p_note, note);
    SELECT bookmark_id INTO p_bookmark_id FROM bookmarks WHERE user_id = p_user_id AND merchandise_id = p_target_id;
  END IF;
  CALL sp_log_activity(p_user_id, 'bookmark_add', p_target_type, p_target_id, NULL);
  COMMIT;
END$$

-- C2. Edit the note of MY bookmark
DROP PROCEDURE IF EXISTS sp_update_bookmark_note$$
CREATE PROCEDURE sp_update_bookmark_note(
  IN p_user_id INT UNSIGNED, IN p_bookmark_id INT UNSIGNED, IN p_note TEXT)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  SELECT bookmark_id INTO v_id FROM bookmarks
   WHERE bookmark_id = p_bookmark_id AND user_id = p_user_id FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Bookmark not found';
  END IF;
  UPDATE bookmarks SET note = p_note WHERE bookmark_id = v_id;
  COMMIT;
END$$

-- C3. Remove MY bookmark (refresh popularity if it was a content bookmark)
DROP PROCEDURE IF EXISTS sp_remove_bookmark$$
CREATE PROCEDURE sp_remove_bookmark(IN p_user_id INT UNSIGNED, IN p_bookmark_id INT UNSIGNED)
BEGIN
  DECLARE v_content INT UNSIGNED DEFAULT NULL;
  DECLARE v_found   INT UNSIGNED DEFAULT NULL;
  DECLARE v_lock    INT UNSIGNED DEFAULT NULL;
  DECLARE v_pop     INT UNSIGNED DEFAULT 0;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  SELECT bookmark_id, content_id INTO v_found, v_content FROM bookmarks
   WHERE bookmark_id = p_bookmark_id AND user_id = p_user_id;
  IF v_found IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Bookmark not found';
  END IF;
  IF v_content IS NOT NULL THEN
    SELECT content_id INTO v_lock FROM contents WHERE content_id = v_content FOR UPDATE;
  END IF;
  DELETE FROM bookmarks WHERE bookmark_id = v_found;
  IF v_content IS NOT NULL THEN
    SET v_pop = fn_popularity_score(v_content);
    UPDATE contents SET popularity_score = v_pop WHERE content_id = v_content;
  END IF;
  CALL sp_log_activity(p_user_id, 'bookmark_remove', 'bookmark', p_bookmark_id, NULL);
  COMMIT;
END$$

-- C4. Create (or return the existing) public share token for MY bookmark.
--     Token is derived from UUID+RAND; a production app should prefer a
--     cryptographically random token generated in application code.
DROP PROCEDURE IF EXISTS sp_create_share_link$$
CREATE PROCEDURE sp_create_share_link(
  IN p_user_id INT UNSIGNED, IN p_bookmark_id INT UNSIGNED, OUT p_share_token CHAR(32))
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  SELECT bookmark_id, share_token INTO v_id, p_share_token FROM bookmarks
   WHERE bookmark_id = p_bookmark_id AND user_id = p_user_id FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Bookmark not found';
  END IF;
  IF p_share_token IS NULL THEN
    SET p_share_token = LEFT(SHA2(CONCAT(UUID(), RAND(), p_bookmark_id), 256), 32);
    UPDATE bookmarks SET share_token = p_share_token WHERE bookmark_id = v_id;
  END IF;
  COMMIT;
END$$

-- =====================================================================
-- D. FAN SUBMISSIONS, FEEDBACK
-- =====================================================================

DROP PROCEDURE IF EXISTS sp_submit_fan_content$$
CREATE PROCEDURE sp_submit_fan_content(
  IN p_user_id INT UNSIGNED, IN p_category_id INT UNSIGNED, IN p_title VARCHAR(255),
  IN p_body LONGTEXT, IN p_cover_image_url VARCHAR(500), OUT p_submission_id INT UNSIGNED)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_title IS NULL OR TRIM(p_title) = '' OR p_body IS NULL OR TRIM(p_body) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Title and body are required';
  END IF;

  START TRANSACTION;
  INSERT INTO fan_submissions (user_id, category_id, title, body, cover_image_url)
  VALUES (p_user_id, p_category_id, TRIM(p_title), p_body, p_cover_image_url);
  SET p_submission_id = LAST_INSERT_ID();
  CALL sp_log_activity(p_user_id, 'submit_content', 'submission', p_submission_id, NULL);
  COMMIT;
END$$

-- D2. Admin approves / rejects. Approve = publish as content + mark submission,
--     all-or-nothing.  p_decision: approved | rejected
DROP PROCEDURE IF EXISTS sp_review_submission$$
CREATE PROCEDURE sp_review_submission(
  IN p_submission_id INT UNSIGNED, IN p_admin_id INT UNSIGNED,
  IN p_decision VARCHAR(10), IN p_reason VARCHAR(500), OUT p_content_id INT UNSIGNED)
BEGIN
  DECLARE v_status VARCHAR(10) DEFAULT NULL;
  DECLARE v_user   INT UNSIGNED DEFAULT NULL;
  DECLARE v_cat    INT UNSIGNED DEFAULT NULL;
  DECLARE v_title  VARCHAR(255) DEFAULT NULL;
  DECLARE v_body   LONGTEXT DEFAULT NULL;
  DECLARE v_cover  VARCHAR(500) DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_decision NOT IN ('approved', 'rejected') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Decision must be approved or rejected';
  END IF;
  IF p_decision = 'rejected' AND (p_reason IS NULL OR TRIM(p_reason) = '') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'A reason is required when rejecting';
  END IF;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can review submissions';
  END IF;

  SELECT status, user_id, category_id, title, body, cover_image_url
    INTO v_status, v_user, v_cat, v_title, v_body, v_cover
    FROM fan_submissions WHERE submission_id = p_submission_id FOR UPDATE; -- two admins cannot both review
  IF v_status IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Submission not found';
  END IF;
  IF v_status <> 'pending' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Submission was already reviewed';
  END IF;

  IF p_decision = 'approved' THEN
    INSERT INTO contents (category_id, title, slug, type, body, thumbnail_url, status, created_by)
    VALUES (v_cat, v_title,
            CONCAT(LEFT(TRIM(BOTH '-' FROM REGEXP_REPLACE(LOWER(v_title), '[^a-z0-9]+', '-')), 200),
                   '-s', p_submission_id),
            'article', v_body, v_cover, 'published', v_user);
    SET p_content_id = LAST_INSERT_ID();
  ELSE
    SET p_content_id = NULL;
  END IF;

  UPDATE fan_submissions
     SET status = p_decision, reviewed_by = p_admin_id, reviewed_at = NOW(),
         reject_reason = IF(p_decision = 'rejected', p_reason, NULL),
         published_content_id = p_content_id
   WHERE submission_id = p_submission_id;
  CALL sp_log_activity(p_admin_id, CONCAT('submission_', p_decision), 'submission', p_submission_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_submit_feedback$$
CREATE PROCEDURE sp_submit_feedback(
  IN p_user_id INT UNSIGNED, IN p_contact_email VARCHAR(255), IN p_type VARCHAR(20),
  IN p_subject VARCHAR(200), IN p_message TEXT, OUT p_feedback_id INT UNSIGNED)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_type NOT IN ('bug', 'suggestion', 'query') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Type must be bug, suggestion or query';
  END IF;
  IF p_subject IS NULL OR TRIM(p_subject) = '' OR p_message IS NULL OR TRIM(p_message) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Subject and message are required';
  END IF;
  IF p_user_id IS NULL AND p_contact_email IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Visitors must provide a contact e-mail';
  END IF;

  START TRANSACTION;
  INSERT INTO feedbacks (user_id, contact_email, type, subject, message)
  VALUES (p_user_id, p_contact_email, p_type, TRIM(p_subject), p_message);
  SET p_feedback_id = LAST_INSERT_ID();
  IF p_user_id IS NOT NULL THEN
    CALL sp_log_activity(p_user_id, 'submit_feedback', 'feedback', p_feedback_id, p_type);
  END IF;
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_resolve_feedback$$
CREATE PROCEDURE sp_resolve_feedback(
  IN p_feedback_id INT UNSIGNED, IN p_admin_id INT UNSIGNED,
  IN p_status VARCHAR(20), IN p_response TEXT)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_status NOT IN ('new', 'in_progress', 'resolved', 'closed') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid feedback status';
  END IF;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can handle feedback';
  END IF;
  SELECT feedback_id INTO v_id FROM feedbacks WHERE feedback_id = p_feedback_id FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Feedback not found';
  END IF;
  UPDATE feedbacks
     SET status = p_status, admin_response = COALESCE(p_response, admin_response),
         handled_by = p_admin_id,
         resolved_at = IF(p_status IN ('resolved', 'closed'), NOW(), NULL)
   WHERE feedback_id = v_id;
  CALL sp_log_activity(p_admin_id, 'feedback_update', 'feedback', v_id, p_status);
  COMMIT;
END$$

-- =====================================================================
-- E. CHATBOT
-- =====================================================================

DROP PROCEDURE IF EXISTS sp_chat_start_session$$
CREATE PROCEDURE sp_chat_start_session(
  IN p_user_id INT UNSIGNED, IN p_session_token CHAR(36), OUT p_session_id INT UNSIGNED)
BEGIN
  INSERT INTO chat_sessions (user_id, session_token) VALUES (p_user_id, p_session_token);
  SET p_session_id = LAST_INSERT_ID();
END$$

-- Best FAQ match for a message (FULLTEXT relevance); returns 0 or 1 row
DROP PROCEDURE IF EXISTS sp_chat_find_faq$$
CREATE PROCEDURE sp_chat_find_faq(IN p_message VARCHAR(500))
BEGIN
  SELECT faq_id, question, answer,
         MATCH(question, keywords) AGAINST(p_message) AS relevance
    FROM chatbot_faqs
   WHERE is_active = TRUE AND MATCH(question, keywords) AGAINST(p_message)
   ORDER BY relevance DESC LIMIT 1;
END$$

-- Store one exchange and advance the session state together
DROP PROCEDURE IF EXISTS sp_chat_log_message$$
CREATE PROCEDURE sp_chat_log_message(
  IN p_session_id INT UNSIGNED, IN p_user_id INT UNSIGNED, IN p_message TEXT,
  IN p_response TEXT, IN p_faq_id INT UNSIGNED, IN p_next_step TINYINT UNSIGNED,
  IN p_completed BOOLEAN)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  INSERT INTO chatbot_queries (session_id, user_id, message, response, matched_faq_id)
  VALUES (p_session_id, p_user_id, p_message, p_response, p_faq_id);
  UPDATE chat_sessions
     SET current_step = COALESCE(p_next_step, current_step),
         onboarding_completed = onboarding_completed OR COALESCE(p_completed, FALSE)
   WHERE session_id = p_session_id;
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_chat_get_history$$
CREATE PROCEDURE sp_chat_get_history(IN p_session_id INT UNSIGNED, IN p_limit INT)
BEGIN
  SET p_limit = LEAST(GREATEST(COALESCE(p_limit, 50), 1), 200);
  SELECT * FROM (
    SELECT query_id, message, response, created_at FROM chatbot_queries
     WHERE session_id = p_session_id ORDER BY query_id DESC LIMIT p_limit
  ) h ORDER BY query_id;
END$$

-- =====================================================================
-- F. EVENTS (calendar + "near me")
-- =====================================================================
-- All filters optional.  Give p_lat/p_lng (user GPS) to get distance_km and
-- sort by nearest; add p_radius_km to keep only events within that radius.
-- p_from defaults to NOW(); use p_from/p_to for a calendar month view.
DROP PROCEDURE IF EXISTS sp_search_events$$
CREATE PROCEDURE sp_search_events(
  IN p_city VARCHAR(100), IN p_category_id INT UNSIGNED, IN p_from DATETIME, IN p_to DATETIME,
  IN p_lat DECIMAL(9,6), IN p_lng DECIMAL(9,6), IN p_radius_km DECIMAL(8,2),
  IN p_limit INT, IN p_offset INT)
BEGIN
  SET p_limit  = LEAST(GREATEST(COALESCE(p_limit, 20), 1), 100);
  SET p_offset = GREATEST(COALESCE(p_offset, 0), 0);

  SELECT t.* FROM (
    SELECT e.event_id, e.title, e.event_type, e.venue, e.city, e.latitude, e.longitude,
           e.start_at, e.end_at, e.ticket_url, e.cover_url, e.category_id,
           CASE WHEN p_lat IS NULL OR p_lng IS NULL OR e.latitude IS NULL OR e.longitude IS NULL THEN NULL
                ELSE ROUND(6371 * ACOS(LEAST(1,
                       COS(RADIANS(p_lat)) * COS(RADIANS(e.latitude)) * COS(RADIANS(e.longitude) - RADIANS(p_lng))
                     + SIN(RADIANS(p_lat)) * SIN(RADIANS(e.latitude)))), 2)
           END AS distance_km
      FROM events e
     WHERE (p_city IS NULL OR e.city = p_city)
       AND (p_category_id IS NULL OR e.category_id = p_category_id)
       AND e.start_at >= COALESCE(p_from, NOW())
       AND (p_to IS NULL OR e.start_at <= p_to)
  ) t
  WHERE (p_radius_km IS NULL OR p_lat IS NULL OR p_lng IS NULL OR t.distance_km <= p_radius_km)
  ORDER BY (t.distance_km IS NULL), t.distance_km, t.start_at
  LIMIT p_limit OFFSET p_offset;
END$$

-- =====================================================================
-- G. ADMIN
-- =====================================================================

-- G1. Create content + genres + tags in one transaction.
--     Genre / tag ids are JSON arrays, e.g. '[1,4]'.
DROP PROCEDURE IF EXISTS sp_create_content$$
CREATE PROCEDURE sp_create_content(
  IN p_admin_id INT UNSIGNED, IN p_category_id INT UNSIGNED, IN p_fandom_id INT UNSIGNED,
  IN p_title VARCHAR(255), IN p_slug VARCHAR(280), IN p_type VARCHAR(20),
  IN p_summary VARCHAR(500), IN p_description TEXT, IN p_body LONGTEXT,
  IN p_media_url VARCHAR(500), IN p_embed_url VARCHAR(500), IN p_thumbnail_url VARCHAR(500),
  IN p_release_date DATE, IN p_is_featured BOOLEAN,
  IN p_genre_ids JSON, IN p_tag_ids JSON, OUT p_content_id INT UNSIGNED)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_title IS NULL OR TRIM(p_title) = '' OR p_slug IS NULL OR TRIM(p_slug) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Title and slug are required';
  END IF;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can create content';
  END IF;

  INSERT INTO contents (category_id, fandom_id, title, slug, type, summary, description, body,
                        media_url, embed_url, thumbnail_url, release_date, is_featured, created_by)
  VALUES (p_category_id, p_fandom_id, TRIM(p_title), TRIM(p_slug), p_type, p_summary, p_description, p_body,
          p_media_url, p_embed_url, p_thumbnail_url, p_release_date, COALESCE(p_is_featured, FALSE), p_admin_id);
  SET p_content_id = LAST_INSERT_ID();

  IF p_genre_ids IS NOT NULL THEN
    INSERT INTO content_genres (content_id, genre_id)
    SELECT DISTINCT p_content_id, jt.id
      FROM JSON_TABLE(p_genre_ids, '$[*]' COLUMNS (id INT UNSIGNED PATH '$')) AS jt;
  END IF;
  IF p_tag_ids IS NOT NULL THEN
    INSERT INTO content_tags (content_id, tag_id)
    SELECT DISTINCT p_content_id, jt.id
      FROM JSON_TABLE(p_tag_ids, '$[*]' COLUMNS (id INT UNSIGNED PATH '$')) AS jt;
  END IF;
  CALL sp_log_activity(p_admin_id, 'content_create', 'content', p_content_id, NULL);
  COMMIT;
END$$

-- G2. Statistics for the admin panel (5 result sets).  p_days = look-back window.
DROP PROCEDURE IF EXISTS sp_admin_dashboard_stats$$
CREATE PROCEDURE sp_admin_dashboard_stats(IN p_admin_id INT UNSIGNED, IN p_days INT)
BEGIN
  DECLARE v_since DATETIME;
  SET p_days = LEAST(GREATEST(COALESCE(p_days, 30), 1), 365);
  SET v_since = NOW() - INTERVAL p_days DAY;

  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view statistics';
  END IF;

  -- 1) headline numbers
  SELECT (SELECT COUNT(*) FROM users)                                        AS total_users,
         (SELECT COUNT(*) FROM users WHERE last_login_at >= v_since)         AS active_users,
         (SELECT COUNT(*) FROM users WHERE created_at    >= v_since)         AS new_users,
         (SELECT COUNT(*) FROM contents WHERE status = 'published')          AS published_contents,
         (SELECT COUNT(*) FROM fan_submissions WHERE status = 'pending')     AS pending_submissions,
         (SELECT COUNT(*) FROM feedbacks WHERE status IN ('new', 'in_progress')) AS open_feedback,
         (SELECT COUNT(*) FROM chatbot_queries WHERE created_at >= v_since)  AS chatbot_interactions;
  -- 2) popular categories
  SELECT * FROM v_category_popularity ORDER BY total_views DESC, content_count DESC LIMIT 8;
  -- 3) chatbot volume per day
  SELECT DATE(created_at) AS day, COUNT(*) AS interactions
    FROM chatbot_queries WHERE created_at >= v_since
   GROUP BY DATE(created_at) ORDER BY day;
  -- 4) top content
  SELECT content_id, title, view_count, popularity_score
    FROM contents WHERE status = 'published'
   ORDER BY popularity_score DESC, view_count DESC LIMIT 10;
  -- 5) top merchandise
  SELECT item_id, name, view_count FROM merchandise_items ORDER BY view_count DESC LIMIT 10;
END$$

-- =====================================================================
-- H. MAINTENANCE
-- =====================================================================
DROP PROCEDURE IF EXISTS sp_purge_expired_tokens$$
CREATE PROCEDURE sp_purge_expired_tokens()
BEGIN
  DELETE FROM user_tokens WHERE expires_at < NOW() - INTERVAL 7 DAY OR used_at < NOW() - INTERVAL 7 DAY;
END$$

DELIMITER ;

-- Daily clean-up (needs:  SET GLOBAL event_scheduler = ON;)
DROP EVENT IF EXISTS ev_purge_tokens;
CREATE EVENT ev_purge_tokens ON SCHEDULE EVERY 1 DAY DO CALL sp_purge_expired_tokens();

-- ---------------------------------------------------------------------
-- OPTIONAL - least-privilege application account (recommended for security)
--   CREATE USER 'fanhub_app'@'localhost' IDENTIFIED BY 'change_me';
--   GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON fanhubplus.* TO 'fanhub_app'@'localhost';
-- ---------------------------------------------------------------------

-- =====================================================================
-- ACID NOTES (for the project report / viva)
--  Atomicity   : each procedure is START TRANSACTION..COMMIT; the EXIT HANDLER
--                rolls back everything on any error (e.g. review = insert
--                content + update submission + log; either all or none).
--  Consistency : PK/FK/UNIQUE/CHECK constraints + trigger + SIGNAL rules keep
--                data valid (one rating per user, score 1-5, one bookmark
--                target, admin-only actions, pending -> approved/rejected once).
--  Isolation   : InnoDB default REPEATABLE READ; SELECT ... FOR UPDATE on
--                rows that are read-then-changed (tokens, submissions,
--                content rows before popularity refresh); counters use
--                "col = col + 1"; fixed lock order; app retries on 1213.
--  Durability  : InnoDB redo log. For full durability keep
--                innodb_flush_log_at_trx_commit = 1 (default) and, if binary
--                logging is enabled, sync_binlog = 1. Take regular backups
--                (mysqldump --single-transaction --routines --events).
-- =====================================================================

-- =====================================================================
-- SUPPLEMENT 1: ADMIN CRUD PROCEDURES
-- =====================================================================
-- =====================================================================
-- FAN HUB PLUS - ADDITIONAL ADMIN CRUD PROCEDURES
-- Target: MySQL 8.0.16+ / MariaDB 10.6+
-- Run AFTER fanhubplus_full.sql.
--
-- This file adds create/update/delete procedures for the entities that
-- were not fully covered by the base design: characters, merchandise,
-- events and users, plus update/delete procedures for contents.
-- All administrative procedures verify fn_is_admin(), use transactions,
-- and write to activity_logs.
-- =====================================================================

USE fanhubplus;

DELIMITER $$

-- ---------------------------------------------------------------------
-- CONTENT: UPDATE
-- Replaces genre/tag links only when the corresponding JSON parameter is
-- not NULL. Pass [] to clear all links.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_update_content$$
CREATE PROCEDURE sp_update_content(
  IN p_admin_id INT UNSIGNED,
  IN p_content_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_fandom_id INT UNSIGNED,
  IN p_title VARCHAR(255),
  IN p_slug VARCHAR(280),
  IN p_type VARCHAR(20),
  IN p_summary VARCHAR(500),
  IN p_description TEXT,
  IN p_body LONGTEXT,
  IN p_media_url VARCHAR(500),
  IN p_embed_url VARCHAR(500),
  IN p_thumbnail_url VARCHAR(500),
  IN p_release_date DATE,
  IN p_is_featured BOOLEAN,
  IN p_status VARCHAR(20),
  IN p_genre_ids JSON,
  IN p_tag_ids JSON
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE v_fandom_category INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_title IS NULL OR TRIM(p_title) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Title is required';
  END IF;
  IF p_slug IS NULL OR TRIM(p_slug) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Slug is required';
  END IF;
  IF p_status NOT IN ('draft', 'published', 'archived') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid content status';
  END IF;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can update content';
  END IF;

  SELECT content_id INTO v_id
    FROM contents
   WHERE content_id = p_content_id
   FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Content not found';
  END IF;

  IF p_fandom_id IS NOT NULL THEN
    SELECT category_id INTO v_fandom_category
      FROM fandoms
     WHERE fandom_id = p_fandom_id;
    IF v_fandom_category IS NULL THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fandom not found';
    END IF;
    IF v_fandom_category <> p_category_id THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fandom does not belong to the selected category';
    END IF;
  END IF;

  UPDATE contents
     SET category_id = p_category_id,
         fandom_id = p_fandom_id,
         title = TRIM(p_title),
         slug = TRIM(p_slug),
         type = p_type,
         summary = p_summary,
         description = p_description,
         body = p_body,
         media_url = p_media_url,
         embed_url = p_embed_url,
         thumbnail_url = p_thumbnail_url,
         release_date = p_release_date,
         is_featured = COALESCE(p_is_featured, FALSE),
         status = p_status
   WHERE content_id = p_content_id;

  IF p_genre_ids IS NOT NULL THEN
    DELETE FROM content_genres WHERE content_id = p_content_id;
    INSERT INTO content_genres (content_id, genre_id)
    SELECT DISTINCT p_content_id, jt.id
      FROM JSON_TABLE(p_genre_ids, '$[*]' COLUMNS (id INT UNSIGNED PATH '$')) AS jt;
  END IF;

  IF p_tag_ids IS NOT NULL THEN
    DELETE FROM content_tags WHERE content_id = p_content_id;
    INSERT INTO content_tags (content_id, tag_id)
    SELECT DISTINCT p_content_id, jt.id
      FROM JSON_TABLE(p_tag_ids, '$[*]' COLUMNS (id INT UNSIGNED PATH '$')) AS jt;
  END IF;

  CALL sp_log_activity(p_admin_id, 'content_update', 'content', p_content_id, NULL);
  COMMIT;
END$$

-- CONTENT: DELETE
DROP PROCEDURE IF EXISTS sp_delete_content$$
CREATE PROCEDURE sp_delete_content(
  IN p_admin_id INT UNSIGNED,
  IN p_content_id INT UNSIGNED
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can delete content';
  END IF;

  SELECT content_id INTO v_id
    FROM contents
   WHERE content_id = p_content_id
   FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Content not found';
  END IF;

  CALL sp_log_activity(p_admin_id, 'content_delete', 'content', p_content_id, NULL);
  DELETE FROM contents WHERE content_id = p_content_id;
  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- CHARACTER PROFILES: CREATE, UPDATE, DELETE
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_create_character$$
CREATE PROCEDURE sp_create_character(
  IN p_admin_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_fandom_id INT UNSIGNED,
  IN p_name VARCHAR(150),
  IN p_alias VARCHAR(150),
  IN p_bio TEXT,
  IN p_image_url VARCHAR(500),
  OUT p_character_id INT UNSIGNED
)
BEGIN
  DECLARE v_fandom_category INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_name IS NULL OR TRIM(p_name) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Character name is required';
  END IF;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can create characters';
  END IF;
  IF p_fandom_id IS NOT NULL THEN
    SELECT category_id INTO v_fandom_category FROM fandoms WHERE fandom_id = p_fandom_id;
    IF v_fandom_category IS NULL OR v_fandom_category <> p_category_id THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fandom does not belong to the selected category';
    END IF;
  END IF;

  INSERT INTO character_profiles (category_id, fandom_id, name, alias, bio, image_url)
  VALUES (p_category_id, p_fandom_id, TRIM(p_name), p_alias, p_bio, p_image_url);
  SET p_character_id = LAST_INSERT_ID();
  CALL sp_log_activity(p_admin_id, 'character_create', 'character', p_character_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_update_character$$
CREATE PROCEDURE sp_update_character(
  IN p_admin_id INT UNSIGNED,
  IN p_character_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_fandom_id INT UNSIGNED,
  IN p_name VARCHAR(150),
  IN p_alias VARCHAR(150),
  IN p_bio TEXT,
  IN p_image_url VARCHAR(500)
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE v_fandom_category INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_name IS NULL OR TRIM(p_name) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Character name is required';
  END IF;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can update characters';
  END IF;
  SELECT character_id INTO v_id FROM character_profiles WHERE character_id = p_character_id FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Character not found';
  END IF;
  IF p_fandom_id IS NOT NULL THEN
    SELECT category_id INTO v_fandom_category FROM fandoms WHERE fandom_id = p_fandom_id;
    IF v_fandom_category IS NULL OR v_fandom_category <> p_category_id THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fandom does not belong to the selected category';
    END IF;
  END IF;

  UPDATE character_profiles
     SET category_id = p_category_id, fandom_id = p_fandom_id,
         name = TRIM(p_name), alias = p_alias, bio = p_bio, image_url = p_image_url
   WHERE character_id = p_character_id;
  CALL sp_log_activity(p_admin_id, 'character_update', 'character', p_character_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_delete_character$$
CREATE PROCEDURE sp_delete_character(
  IN p_admin_id INT UNSIGNED,
  IN p_character_id INT UNSIGNED
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can delete characters';
  END IF;
  SELECT character_id INTO v_id FROM character_profiles WHERE character_id = p_character_id FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Character not found';
  END IF;
  CALL sp_log_activity(p_admin_id, 'character_delete', 'character', p_character_id, NULL);
  DELETE FROM character_profiles WHERE character_id = p_character_id;
  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- MERCHANDISE: CREATE, UPDATE, DELETE
-- Tag links are replaced only when p_tag_ids is not NULL; [] clears tags.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_create_merchandise$$
CREATE PROCEDURE sp_create_merchandise(
  IN p_admin_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_fandom_id INT UNSIGNED,
  IN p_name VARCHAR(200),
  IN p_description TEXT,
  IN p_image_url VARCHAR(500),
  IN p_reference_url VARCHAR(500),
  IN p_release_date DATE,
  IN p_is_upcoming BOOLEAN,
  IN p_tag_ids JSON,
  OUT p_item_id INT UNSIGNED
)
BEGIN
  DECLARE v_fandom_category INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_name IS NULL OR TRIM(p_name) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Merchandise name is required';
  END IF;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can create merchandise';
  END IF;
  IF p_fandom_id IS NOT NULL THEN
    SELECT category_id INTO v_fandom_category FROM fandoms WHERE fandom_id = p_fandom_id;
    IF v_fandom_category IS NULL OR v_fandom_category <> p_category_id THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fandom does not belong to the selected category';
    END IF;
  END IF;

  INSERT INTO merchandise_items
    (category_id, fandom_id, name, description, image_url, reference_url, release_date, is_upcoming)
  VALUES
    (p_category_id, p_fandom_id, TRIM(p_name), p_description, p_image_url, p_reference_url,
     p_release_date, COALESCE(p_is_upcoming, FALSE));
  SET p_item_id = LAST_INSERT_ID();

  IF p_tag_ids IS NOT NULL THEN
    INSERT INTO merchandise_tags (item_id, tag_id)
    SELECT DISTINCT p_item_id, jt.id
      FROM JSON_TABLE(p_tag_ids, '$[*]' COLUMNS (id INT UNSIGNED PATH '$')) AS jt;
  END IF;
  CALL sp_log_activity(p_admin_id, 'merchandise_create', 'merchandise', p_item_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_update_merchandise$$
CREATE PROCEDURE sp_update_merchandise(
  IN p_admin_id INT UNSIGNED,
  IN p_item_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_fandom_id INT UNSIGNED,
  IN p_name VARCHAR(200),
  IN p_description TEXT,
  IN p_image_url VARCHAR(500),
  IN p_reference_url VARCHAR(500),
  IN p_release_date DATE,
  IN p_is_upcoming BOOLEAN,
  IN p_tag_ids JSON
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE v_fandom_category INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_name IS NULL OR TRIM(p_name) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Merchandise name is required';
  END IF;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can update merchandise';
  END IF;
  SELECT item_id INTO v_id FROM merchandise_items WHERE item_id = p_item_id FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Merchandise item not found';
  END IF;
  IF p_fandom_id IS NOT NULL THEN
    SELECT category_id INTO v_fandom_category FROM fandoms WHERE fandom_id = p_fandom_id;
    IF v_fandom_category IS NULL OR v_fandom_category <> p_category_id THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fandom does not belong to the selected category';
    END IF;
  END IF;

  UPDATE merchandise_items
     SET category_id = p_category_id, fandom_id = p_fandom_id, name = TRIM(p_name),
         description = p_description, image_url = p_image_url, reference_url = p_reference_url,
         release_date = p_release_date, is_upcoming = COALESCE(p_is_upcoming, FALSE)
   WHERE item_id = p_item_id;

  IF p_tag_ids IS NOT NULL THEN
    DELETE FROM merchandise_tags WHERE item_id = p_item_id;
    INSERT INTO merchandise_tags (item_id, tag_id)
    SELECT DISTINCT p_item_id, jt.id
      FROM JSON_TABLE(p_tag_ids, '$[*]' COLUMNS (id INT UNSIGNED PATH '$')) AS jt;
  END IF;
  CALL sp_log_activity(p_admin_id, 'merchandise_update', 'merchandise', p_item_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_delete_merchandise$$
CREATE PROCEDURE sp_delete_merchandise(
  IN p_admin_id INT UNSIGNED,
  IN p_item_id INT UNSIGNED
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can delete merchandise';
  END IF;
  SELECT item_id INTO v_id FROM merchandise_items WHERE item_id = p_item_id FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Merchandise item not found';
  END IF;
  CALL sp_log_activity(p_admin_id, 'merchandise_delete', 'merchandise', p_item_id, NULL);
  DELETE FROM merchandise_items WHERE item_id = p_item_id;
  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- EVENTS: CREATE, UPDATE, DELETE
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_create_event$$
CREATE PROCEDURE sp_create_event(
  IN p_admin_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_fandom_id INT UNSIGNED,
  IN p_title VARCHAR(255),
  IN p_description TEXT,
  IN p_event_type VARCHAR(30),
  IN p_venue VARCHAR(255),
  IN p_address VARCHAR(255),
  IN p_city VARCHAR(100),
  IN p_country VARCHAR(100),
  IN p_latitude DECIMAL(9,6),
  IN p_longitude DECIMAL(9,6),
  IN p_start_at DATETIME,
  IN p_end_at DATETIME,
  IN p_ticket_url VARCHAR(500),
  IN p_cover_url VARCHAR(500),
  OUT p_event_id INT UNSIGNED
)
BEGIN
  DECLARE v_fandom_category INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_title IS NULL OR TRIM(p_title) = '' OR p_city IS NULL OR TRIM(p_city) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Event title and city are required';
  END IF;
  IF p_end_at IS NOT NULL AND p_end_at < p_start_at THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Event end must not precede event start';
  END IF;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can create events';
  END IF;
  IF p_fandom_id IS NOT NULL THEN
    SELECT category_id INTO v_fandom_category FROM fandoms WHERE fandom_id = p_fandom_id;
    IF v_fandom_category IS NULL OR (p_category_id IS NOT NULL AND v_fandom_category <> p_category_id) THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fandom does not belong to the selected category';
    END IF;
  END IF;

  INSERT INTO events
    (category_id, fandom_id, title, description, event_type, venue, address, city, country,
     latitude, longitude, start_at, end_at, ticket_url, cover_url, created_by)
  VALUES
    (p_category_id, p_fandom_id, TRIM(p_title), p_description, p_event_type, p_venue, p_address,
     TRIM(p_city), p_country, p_latitude, p_longitude, p_start_at, p_end_at, p_ticket_url,
     p_cover_url, p_admin_id);
  SET p_event_id = LAST_INSERT_ID();
  CALL sp_log_activity(p_admin_id, 'event_create', 'event', p_event_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_update_event$$
CREATE PROCEDURE sp_update_event(
  IN p_admin_id INT UNSIGNED,
  IN p_event_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_fandom_id INT UNSIGNED,
  IN p_title VARCHAR(255),
  IN p_description TEXT,
  IN p_event_type VARCHAR(30),
  IN p_venue VARCHAR(255),
  IN p_address VARCHAR(255),
  IN p_city VARCHAR(100),
  IN p_country VARCHAR(100),
  IN p_latitude DECIMAL(9,6),
  IN p_longitude DECIMAL(9,6),
  IN p_start_at DATETIME,
  IN p_end_at DATETIME,
  IN p_ticket_url VARCHAR(500),
  IN p_cover_url VARCHAR(500)
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE v_fandom_category INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_title IS NULL OR TRIM(p_title) = '' OR p_city IS NULL OR TRIM(p_city) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Event title and city are required';
  END IF;
  IF p_end_at IS NOT NULL AND p_end_at < p_start_at THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Event end must not precede event start';
  END IF;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can update events';
  END IF;
  SELECT event_id INTO v_id FROM events WHERE event_id = p_event_id FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Event not found';
  END IF;
  IF p_fandom_id IS NOT NULL THEN
    SELECT category_id INTO v_fandom_category FROM fandoms WHERE fandom_id = p_fandom_id;
    IF v_fandom_category IS NULL OR (p_category_id IS NOT NULL AND v_fandom_category <> p_category_id) THEN
      SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fandom does not belong to the selected category';
    END IF;
  END IF;

  UPDATE events
     SET category_id = p_category_id, fandom_id = p_fandom_id, title = TRIM(p_title),
         description = p_description, event_type = p_event_type, venue = p_venue,
         address = p_address, city = TRIM(p_city), country = p_country,
         latitude = p_latitude, longitude = p_longitude, start_at = p_start_at,
         end_at = p_end_at, ticket_url = p_ticket_url, cover_url = p_cover_url
   WHERE event_id = p_event_id;
  CALL sp_log_activity(p_admin_id, 'event_update', 'event', p_event_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_delete_event$$
CREATE PROCEDURE sp_delete_event(
  IN p_admin_id INT UNSIGNED,
  IN p_event_id INT UNSIGNED
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can delete events';
  END IF;
  SELECT event_id INTO v_id FROM events WHERE event_id = p_event_id FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Event not found';
  END IF;
  CALL sp_log_activity(p_admin_id, 'event_delete', 'event', p_event_id, NULL);
  DELETE FROM events WHERE event_id = p_event_id;
  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- USERS: UPDATE PROFILE/ROLE/STATUS and DELETE
-- Password changes should continue to use the password-reset procedure,
-- so this procedure never accepts a raw password.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_admin_update_user$$
CREATE PROCEDURE sp_admin_update_user(
  IN p_admin_id INT UNSIGNED,
  IN p_user_id INT UNSIGNED,
  IN p_name VARCHAR(100),
  IN p_email VARCHAR(255),
  IN p_role VARCHAR(10),
  IN p_is_active BOOLEAN,
  IN p_avatar_url VARCHAR(500),
  IN p_bio VARCHAR(500)
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_name IS NULL OR TRIM(p_name) = '' OR p_email IS NULL OR p_email NOT LIKE '%_@_%.__%' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid name or email';
  END IF;
  IF p_role NOT IN ('user', 'admin') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid user role';
  END IF;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can update users';
  END IF;
  SELECT user_id INTO v_id FROM users WHERE user_id = p_user_id FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'User not found';
  END IF;

  UPDATE users
     SET name = TRIM(p_name), email = LOWER(TRIM(p_email)), role = p_role,
         is_active = COALESCE(p_is_active, TRUE), avatar_url = p_avatar_url, bio = p_bio
   WHERE user_id = p_user_id;
  CALL sp_log_activity(p_admin_id, 'user_update', 'user', p_user_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_admin_delete_user$$
CREATE PROCEDURE sp_admin_delete_user(
  IN p_admin_id INT UNSIGNED,
  IN p_user_id INT UNSIGNED
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_admin_id = p_user_id THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'An administrator cannot delete their own account';
  END IF;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can delete users';
  END IF;
  SELECT user_id INTO v_id FROM users WHERE user_id = p_user_id FOR UPDATE;
  IF v_id IS NULL THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'User not found';
  END IF;

  CALL sp_log_activity(p_admin_id, 'user_delete', 'user', p_user_id, NULL);
  DELETE FROM users WHERE user_id = p_user_id;
  COMMIT;
END$$

DELIMITER ;

-- Optional hardening: the original base script validates bookmark targets
-- only on INSERT. This trigger also validates UPDATE operations.
DROP TRIGGER IF EXISTS trg_bookmarks_one_target_update;
DELIMITER $$
CREATE TRIGGER trg_bookmarks_one_target_update
BEFORE UPDATE ON bookmarks
FOR EACH ROW
BEGIN
  IF (NEW.content_id IS NOT NULL) + (NEW.character_id IS NOT NULL) +
     (NEW.merchandise_id IS NOT NULL) <> 1 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'A bookmark must reference exactly one of content, character or merchandise';
  END IF;
END$$
DELIMITER ;

-- Example calls (do not run automatically):
-- CALL sp_update_content(1, 10, 1, NULL, 'Updated title', 'updated-title',
--   'article', 'Summary', 'Description', '<p>Body</p>', NULL, NULL, NULL,
--   '2026-12-01', TRUE, 'published', JSON_ARRAY(1, 4), JSON_ARRAY(1, 3));
-- CALL sp_delete_content(1, 10);
-- CALL sp_create_character(1, 1, NULL, 'Character name', NULL, 'Bio', NULL, @character_id);
-- CALL sp_create_merchandise(1, 1, NULL, 'Collector item', 'Description', NULL, NULL,
--   '2026-12-01', TRUE, JSON_ARRAY(1), @item_id);
-- CALL sp_create_event(1, 1, NULL, 'Fan convention', NULL, 'convention', NULL, NULL,
--   'Hanoi', 'Vietnam', 21.028511, 105.804817, '2026-12-20 09:00:00',
--   '2026-12-20 18:00:00', NULL, NULL, @event_id);
-- CALL sp_admin_update_user(1, 2, 'Updated name', 'user@example.com', 'user', TRUE, NULL, NULL);
-- CALL sp_admin_delete_user(1, 2);
-- =====================================================================


-- =====================================================================
-- SUPPLEMENT 2: REPORTING PROCEDURES
-- =====================================================================
-- =====================================================================
-- FAN HUB PLUS - REPORTING AND ANALYTICS STORED PROCEDURES
-- Target: MySQL 8.0.16+ / MariaDB 10.6+
-- Run AFTER fanhubplus_full.sql and fanhubplus_crud_additions.sql.
--
-- All procedures return one or more result sets and are restricted to
-- active administrators through fn_is_admin().
-- Date parameters are inclusive at the start and exclusive at the end
-- where practical: created_at >= p_from AND created_at < p_to.
-- Pass NULL for p_from/p_to to use the last 30 days through NOW().
-- =====================================================================

USE fanhubplus;

DELIMITER $$

-- ---------------------------------------------------------------------
-- 1. SYSTEM OVERVIEW
-- Returns headline KPIs and daily activity for an admin dashboard/report.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_report_system_overview$$
CREATE PROCEDURE sp_report_system_overview(
  IN p_admin_id INT UNSIGNED,
  IN p_from DATETIME,
  IN p_to DATETIME
)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  SET p_from = COALESCE(p_from, NOW() - INTERVAL 30 DAY);
  SET p_to = COALESCE(p_to, NOW());

  IF p_to <= p_from THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Report end must be after report start';
  END IF;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view reports';
  END IF;

  START TRANSACTION READ ONLY;

  -- 1) Headline KPIs for the selected period and current totals.
  SELECT
    p_from AS report_from,
    p_to AS report_to,
    (SELECT COUNT(*) FROM users WHERE created_at >= p_from AND created_at < p_to) AS new_users,
    (SELECT COUNT(*) FROM users WHERE last_login_at >= p_from AND last_login_at < p_to) AS active_users,
    (SELECT COUNT(*) FROM contents WHERE created_at >= p_from AND created_at < p_to) AS new_contents,
    (SELECT COUNT(*) FROM contents WHERE status = 'published') AS published_contents_total,
    (SELECT COUNT(*) FROM bookmarks WHERE created_at >= p_from AND created_at < p_to) AS bookmarks_created,
    (SELECT COUNT(*) FROM content_ratings WHERE created_at >= p_from AND created_at < p_to) AS ratings_created,
    (SELECT COUNT(*) FROM fan_submissions WHERE created_at >= p_from AND created_at < p_to) AS submissions_created,
    (SELECT COUNT(*) FROM feedbacks WHERE created_at >= p_from AND created_at < p_to) AS feedback_created,
    (SELECT COUNT(*) FROM chatbot_queries WHERE created_at >= p_from AND created_at < p_to) AS chatbot_queries,
    (SELECT COUNT(*) FROM events WHERE start_at >= p_from AND start_at < p_to) AS events_starting;

  -- 2) Daily activity from the immutable activity log.
  SELECT DATE(created_at) AS activity_day,
         COUNT(*) AS total_actions,
         COUNT(DISTINCT user_id) AS active_users,
         SUM(action = 'login') AS logins,
         SUM(action = 'view') AS content_views,
         SUM(action = 'bookmark_add') AS bookmarks_added,
         SUM(action = 'rate') AS ratings_added
    FROM activity_logs
   WHERE created_at >= p_from AND created_at < p_to
   GROUP BY DATE(created_at)
   ORDER BY activity_day;

  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- 2. USER GROWTH AND RETENTION SNAPSHOT
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_report_user_growth$$
CREATE PROCEDURE sp_report_user_growth(
  IN p_admin_id INT UNSIGNED,
  IN p_from DATETIME,
  IN p_to DATETIME
)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  SET p_from = COALESCE(p_from, NOW() - INTERVAL 30 DAY);
  SET p_to = COALESCE(p_to, NOW());

  IF p_to <= p_from THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Report end must be after report start';
  END IF;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view reports';
  END IF;

  START TRANSACTION READ ONLY;

  -- 1) Daily registrations and logins.
  SELECT d.report_day,
         COALESCE(r.registrations, 0) AS registrations,
         COALESCE(l.logins, 0) AS logins,
         COALESCE(l.unique_logged_in_users, 0) AS unique_logged_in_users
    FROM (
      SELECT DATE(created_at) AS report_day FROM users
       WHERE created_at >= p_from AND created_at < p_to
      UNION
      SELECT DATE(created_at) FROM activity_logs
       WHERE action = 'login' AND created_at >= p_from AND created_at < p_to
    ) d
    LEFT JOIN (
      SELECT DATE(created_at) AS report_day, COUNT(*) AS registrations
        FROM users WHERE created_at >= p_from AND created_at < p_to
       GROUP BY DATE(created_at)
    ) r ON r.report_day = d.report_day
    LEFT JOIN (
      SELECT DATE(created_at) AS report_day, COUNT(*) AS logins,
             COUNT(DISTINCT user_id) AS unique_logged_in_users
        FROM activity_logs
       WHERE action = 'login' AND created_at >= p_from AND created_at < p_to
       GROUP BY DATE(created_at)
    ) l ON l.report_day = d.report_day
   ORDER BY d.report_day;

  -- 2) Users by role and current status.
  SELECT role, is_active, COUNT(*) AS user_count
    FROM users
   GROUP BY role, is_active
   ORDER BY role, is_active DESC;

  -- 3) Users with most recorded actions in the period.
  SELECT u.user_id, u.name, u.email, u.role,
         COUNT(a.log_id) AS action_count,
         MAX(a.created_at) AS last_recorded_action
    FROM users u
    JOIN activity_logs a ON a.user_id = u.user_id
   WHERE a.created_at >= p_from AND a.created_at < p_to
   GROUP BY u.user_id, u.name, u.email, u.role
   ORDER BY action_count DESC, last_recorded_action DESC
   LIMIT 20;

  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- 3. CONTENT PERFORMANCE
-- Includes views, ratings, bookmarks and lifetime popularity.
-- p_category_id = NULL means all categories.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_report_content_performance$$
CREATE PROCEDURE sp_report_content_performance(
  IN p_admin_id INT UNSIGNED,
  IN p_from DATETIME,
  IN p_to DATETIME,
  IN p_category_id INT UNSIGNED,
  IN p_limit INT
)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  SET p_from = COALESCE(p_from, NOW() - INTERVAL 30 DAY);
  SET p_to = COALESCE(p_to, NOW());
  SET p_limit = LEAST(GREATEST(COALESCE(p_limit, 50), 1), 200);

  IF p_to <= p_from THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Report end must be after report start';
  END IF;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view reports';
  END IF;

  START TRANSACTION READ ONLY;

  SELECT c.content_id, c.title, c.type, c.status,
         cat.name AS category_name,
         c.created_at, c.release_date,
         c.view_count, c.popularity_score,
         COALESCE(rs.avg_score, 0) AS average_rating,
         COALESCE(rs.rating_count, 0) AS rating_count,
         COALESCE(bm.bookmark_count, 0) AS bookmark_count,
         COALESCE(pr.period_ratings, 0) AS period_ratings,
         COALESCE(pb.period_bookmarks, 0) AS period_bookmarks,
         COALESCE(pa.period_views, 0) AS period_views
    FROM contents c
    JOIN categories cat ON cat.category_id = c.category_id
    LEFT JOIN v_content_rating_stats rs ON rs.content_id = c.content_id
    LEFT JOIN (
      SELECT content_id, COUNT(*) AS bookmark_count
        FROM bookmarks WHERE content_id IS NOT NULL GROUP BY content_id
    ) bm ON bm.content_id = c.content_id
    LEFT JOIN (
      SELECT content_id, COUNT(*) AS period_ratings
        FROM content_ratings WHERE created_at >= p_from AND created_at < p_to
       GROUP BY content_id
    ) pr ON pr.content_id = c.content_id
    LEFT JOIN (
      SELECT content_id, COUNT(*) AS period_bookmarks
        FROM bookmarks WHERE content_id IS NOT NULL
         AND created_at >= p_from AND created_at < p_to
       GROUP BY content_id
    ) pb ON pb.content_id = c.content_id
    LEFT JOIN (
      SELECT entity_id AS content_id, COUNT(*) AS period_views
        FROM activity_logs
       WHERE action = 'view' AND entity_type = 'content'
         AND created_at >= p_from AND created_at < p_to
       GROUP BY entity_id
    ) pa ON pa.content_id = c.content_id
   WHERE (p_category_id IS NULL OR c.category_id = p_category_id)
   ORDER BY period_views DESC, c.popularity_score DESC, c.view_count DESC
   LIMIT p_limit;

  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- 4. CATEGORY AND CONTENT-TYPE PERFORMANCE
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_report_category_performance$$
CREATE PROCEDURE sp_report_category_performance(
  IN p_admin_id INT UNSIGNED,
  IN p_from DATETIME,
  IN p_to DATETIME
)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  SET p_from = COALESCE(p_from, NOW() - INTERVAL 30 DAY);
  SET p_to = COALESCE(p_to, NOW());

  IF p_to <= p_from THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Report end must be after report start';
  END IF;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view reports';
  END IF;

  START TRANSACTION READ ONLY;

  SELECT cat.category_id, cat.name,
         COUNT(DISTINCT c.content_id) AS total_contents,
         COUNT(DISTINCT CASE WHEN c.status = 'published' THEN c.content_id END) AS published_contents,
         COALESCE(SUM(c.view_count), 0) AS lifetime_views,
         COALESCE(SUM(c.popularity_score), 0) AS popularity_total,
         COUNT(DISTINCT CASE WHEN c.created_at >= p_from AND c.created_at < p_to THEN c.content_id END) AS new_contents,
         COALESCE(SUM(CASE WHEN c.created_at >= p_from AND c.created_at < p_to THEN c.view_count ELSE 0 END), 0) AS views_on_new_content
    FROM categories cat
    LEFT JOIN contents c ON c.category_id = cat.category_id
   GROUP BY cat.category_id, cat.name
   ORDER BY lifetime_views DESC, published_contents DESC;

  SELECT cat.name AS category_name, c.type, COUNT(*) AS content_count,
         COALESCE(SUM(c.view_count), 0) AS total_views
    FROM categories cat
    JOIN contents c ON c.category_id = cat.category_id
   WHERE c.status = 'published'
   GROUP BY cat.category_id, cat.name, c.type
   ORDER BY cat.name, total_views DESC;

  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- 5. ENGAGEMENT REPORT
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_report_engagement$$
CREATE PROCEDURE sp_report_engagement(
  IN p_admin_id INT UNSIGNED,
  IN p_from DATETIME,
  IN p_to DATETIME
)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  SET p_from = COALESCE(p_from, NOW() - INTERVAL 30 DAY);
  SET p_to = COALESCE(p_to, NOW());

  IF p_to <= p_from THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Report end must be after report start';
  END IF;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view reports';
  END IF;

  START TRANSACTION READ ONLY;

  -- 1) Action distribution.
  SELECT action, entity_type, COUNT(*) AS action_count,
         COUNT(DISTINCT user_id) AS unique_users
    FROM activity_logs
   WHERE created_at >= p_from AND created_at < p_to
   GROUP BY action, entity_type
   ORDER BY action_count DESC;

  -- 2) Daily engagement trend.
  SELECT DATE(created_at) AS report_day,
         COUNT(*) AS total_actions,
         COUNT(DISTINCT user_id) AS unique_users,
         SUM(action = 'view') AS views,
         SUM(action = 'bookmark_add') AS bookmarks_added,
         SUM(action = 'bookmark_remove') AS bookmarks_removed,
         SUM(action = 'rate') AS ratings,
         SUM(action = 'submit_content') AS fan_submissions,
         SUM(action = 'submit_feedback') AS feedback_submissions
    FROM activity_logs
   WHERE created_at >= p_from AND created_at < p_to
   GROUP BY DATE(created_at)
   ORDER BY report_day;

  -- 3) Most active registered users.
  SELECT u.user_id, u.name, u.email,
         COUNT(a.log_id) AS total_actions,
         SUM(a.action = 'view') AS views,
         SUM(a.action = 'bookmark_add') AS bookmarks_added,
         SUM(a.action = 'rate') AS ratings
    FROM users u
    JOIN activity_logs a ON a.user_id = u.user_id
   WHERE a.created_at >= p_from AND a.created_at < p_to
   GROUP BY u.user_id, u.name, u.email
   ORDER BY total_actions DESC
   LIMIT 20;

  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- 6. BOOKMARK AND RATING REPORT
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_report_bookmarks_and_ratings$$
CREATE PROCEDURE sp_report_bookmarks_and_ratings(
  IN p_admin_id INT UNSIGNED,
  IN p_from DATETIME,
  IN p_to DATETIME
)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  SET p_from = COALESCE(p_from, NOW() - INTERVAL 30 DAY);
  SET p_to = COALESCE(p_to, NOW());

  IF p_to <= p_from THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Report end must be after report start';
  END IF;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view reports';
  END IF;

  START TRANSACTION READ ONLY;

  -- 1) Bookmark targets by type.
  SELECT 'content' AS target_type, COUNT(*) AS total_bookmarks,
         SUM(created_at >= p_from AND created_at < p_to) AS period_bookmarks,
         COUNT(DISTINCT user_id) AS unique_users
    FROM bookmarks WHERE content_id IS NOT NULL
  UNION ALL
  SELECT 'character', COUNT(*), SUM(created_at >= p_from AND created_at < p_to), COUNT(DISTINCT user_id)
    FROM bookmarks WHERE character_id IS NOT NULL
  UNION ALL
  SELECT 'merchandise', COUNT(*), SUM(created_at >= p_from AND created_at < p_to), COUNT(DISTINCT user_id)
    FROM bookmarks WHERE merchandise_id IS NOT NULL;

  -- 2) Rating distribution and averages.
  SELECT score, COUNT(*) AS total_ratings,
         SUM(created_at >= p_from AND created_at < p_to) AS period_ratings
    FROM content_ratings
   GROUP BY score
   ORDER BY score;

  -- 3) Content with the most bookmarks in the period.
  SELECT c.content_id, c.title, cat.name AS category_name,
         COUNT(b.bookmark_id) AS period_bookmarks
    FROM bookmarks b
    JOIN contents c ON c.content_id = b.content_id
    JOIN categories cat ON cat.category_id = c.category_id
   WHERE b.created_at >= p_from AND b.created_at < p_to
   GROUP BY c.content_id, c.title, cat.name
   ORDER BY period_bookmarks DESC
   LIMIT 20;

  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- 7. FAN SUBMISSIONS AND FEEDBACK REPORT
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_report_submissions_feedback$$
CREATE PROCEDURE sp_report_submissions_feedback(
  IN p_admin_id INT UNSIGNED,
  IN p_from DATETIME,
  IN p_to DATETIME
)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  SET p_from = COALESCE(p_from, NOW() - INTERVAL 30 DAY);
  SET p_to = COALESCE(p_to, NOW());

  IF p_to <= p_from THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Report end must be after report start';
  END IF;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view reports';
  END IF;

  START TRANSACTION READ ONLY;

  -- 1) Submission status summary.
  SELECT status, COUNT(*) AS total_submissions,
         SUM(created_at >= p_from AND created_at < p_to) AS period_submissions
    FROM fan_submissions
   GROUP BY status
   ORDER BY FIELD(status, 'pending', 'approved', 'rejected');

  -- 2) Submissions by category.
  SELECT cat.name AS category_name, fs.status, COUNT(*) AS submission_count
    FROM fan_submissions fs
    JOIN categories cat ON cat.category_id = fs.category_id
   WHERE fs.created_at >= p_from AND fs.created_at < p_to
   GROUP BY cat.category_id, cat.name, fs.status
   ORDER BY cat.name, fs.status;

  -- 3) Feedback by type and status.
  SELECT type, status, COUNT(*) AS feedback_count,
         AVG(TIMESTAMPDIFF(HOUR, created_at, COALESCE(resolved_at, p_to))) AS average_age_hours
    FROM feedbacks
   WHERE created_at >= p_from AND created_at < p_to
   GROUP BY type, status
   ORDER BY type, status;

  -- 4) Daily feedback volume.
  SELECT DATE(created_at) AS report_day, type, COUNT(*) AS feedback_count
    FROM feedbacks
   WHERE created_at >= p_from AND created_at < p_to
   GROUP BY DATE(created_at), type
   ORDER BY report_day, type;

  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- 8. EVENTS REPORT
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_report_events$$
CREATE PROCEDURE sp_report_events(
  IN p_admin_id INT UNSIGNED,
  IN p_from DATETIME,
  IN p_to DATETIME
)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  SET p_from = COALESCE(p_from, NOW() - INTERVAL 30 DAY);
  SET p_to = COALESCE(p_to, NOW());

  IF p_to <= p_from THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Report end must be after report start';
  END IF;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view reports';
  END IF;

  START TRANSACTION READ ONLY;

  SELECT city, country, event_type, COUNT(*) AS event_count,
         MIN(start_at) AS first_event, MAX(start_at) AS last_event
    FROM events
   WHERE start_at >= p_from AND start_at < p_to
   GROUP BY city, country, event_type
   ORDER BY event_count DESC, city;

  SELECT e.event_id, e.title, e.event_type, e.city, e.start_at, e.end_at,
         cat.name AS category_name, f.name AS fandom_name,
         e.ticket_url
    FROM events e
    LEFT JOIN categories cat ON cat.category_id = e.category_id
    LEFT JOIN fandoms f ON f.fandom_id = e.fandom_id
   WHERE e.start_at >= p_from AND e.start_at < p_to
   ORDER BY e.start_at;

  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- 9. CHATBOT REPORT
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_report_chatbot_usage$$
CREATE PROCEDURE sp_report_chatbot_usage(
  IN p_admin_id INT UNSIGNED,
  IN p_from DATETIME,
  IN p_to DATETIME
)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  SET p_from = COALESCE(p_from, NOW() - INTERVAL 30 DAY);
  SET p_to = COALESCE(p_to, NOW());

  IF p_to <= p_from THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Report end must be after report start';
  END IF;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view reports';
  END IF;

  START TRANSACTION READ ONLY;

  SELECT COUNT(*) AS total_queries,
         COUNT(DISTINCT session_id) AS sessions,
         COUNT(DISTINCT user_id) AS registered_users,
         SUM(user_id IS NULL) AS visitor_queries,
         SUM(response IS NOT NULL) AS answered_queries,
         SUM(matched_faq_id IS NOT NULL) AS faq_matched_queries,
         AVG(CHAR_LENGTH(message)) AS average_message_length
    FROM chatbot_queries
   WHERE created_at >= p_from AND created_at < p_to;

  SELECT DATE(cq.created_at) AS report_day,
         COUNT(*) AS queries,
         COUNT(DISTINCT cq.session_id) AS sessions,
         SUM(cq.matched_faq_id IS NOT NULL) AS faq_matches
    FROM chatbot_queries cq
   WHERE cq.created_at >= p_from AND cq.created_at < p_to
   GROUP BY DATE(cq.created_at)
   ORDER BY report_day;

  SELECT f.faq_id, f.question, COUNT(cq.query_id) AS match_count
    FROM chatbot_faqs f
    JOIN chatbot_queries cq ON cq.matched_faq_id = f.faq_id
   WHERE cq.created_at >= p_from AND cq.created_at < p_to
   GROUP BY f.faq_id, f.question
   ORDER BY match_count DESC;

  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- 10. MERCHANDISE AND MEDIA REPORT
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_report_merchandise_media$$
CREATE PROCEDURE sp_report_merchandise_media(
  IN p_admin_id INT UNSIGNED,
  IN p_from DATETIME,
  IN p_to DATETIME,
  IN p_limit INT
)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  SET p_from = COALESCE(p_from, NOW() - INTERVAL 30 DAY);
  SET p_to = COALESCE(p_to, NOW());
  SET p_limit = LEAST(GREATEST(COALESCE(p_limit, 50), 1), 200);

  IF p_to <= p_from THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Report end must be after report start';
  END IF;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view reports';
  END IF;

  START TRANSACTION READ ONLY;

  SELECT m.item_id, m.name, cat.name AS category_name, m.is_upcoming,
         m.release_date, m.view_count,
         COALESCE(b.period_bookmarks, 0) AS period_bookmarks,
         COALESCE(v.period_views, 0) AS period_views
    FROM merchandise_items m
    JOIN categories cat ON cat.category_id = m.category_id
    LEFT JOIN (
      SELECT merchandise_id, COUNT(*) AS period_bookmarks
        FROM bookmarks
       WHERE merchandise_id IS NOT NULL
         AND created_at >= p_from AND created_at < p_to
       GROUP BY merchandise_id
    ) b ON b.merchandise_id = m.item_id
    LEFT JOIN (
      SELECT entity_id AS merchandise_id, COUNT(*) AS period_views
        FROM activity_logs
       WHERE entity_type = 'merchandise' AND action = 'view'
         AND created_at >= p_from AND created_at < p_to
       GROUP BY entity_id
    ) v ON v.merchandise_id = m.item_id
   ORDER BY period_views DESC, m.view_count DESC
   LIMIT p_limit;

  SELECT type AS content_type, COUNT(*) AS content_count,
         SUM(status = 'published') AS published_count,
         SUM(media_url IS NOT NULL) AS uploaded_media_count,
         SUM(embed_url IS NOT NULL) AS embedded_media_count,
         SUM(release_date IS NOT NULL AND release_date > CURDATE()) AS future_releases
    FROM contents
   GROUP BY type
   ORDER BY content_count DESC;

  COMMIT;
END$$

DELIMITER ;

-- Example calls (do not run automatically):
-- CALL sp_report_system_overview(1, '2026-09-01', '2026-10-01');
-- CALL sp_report_user_growth(1, NULL, NULL);
-- CALL sp_report_content_performance(1, NULL, NULL, NULL, 50);
-- CALL sp_report_category_performance(1, NULL, NULL);
-- CALL sp_report_engagement(1, NULL, NULL);
-- CALL sp_report_bookmarks_and_ratings(1, NULL, NULL);
-- CALL sp_report_submissions_feedback(1, NULL, NULL);
-- CALL sp_report_events(1, NULL, NULL);
-- CALL sp_report_chatbot_usage(1, NULL, NULL);
-- CALL sp_report_merchandise_media(1, NULL, NULL, 50);
-- =====================================================================


-- =====================================================================
-- SUPPLEMENT 3: USE CASE ALIGNMENT PROCEDURES
-- =====================================================================
-- =====================================================================
-- FAN HUB PLUS - USE CASE ALIGNMENT PROCEDURES
-- Based on FanHubPlus_DacTa_UseCase.docx, UC-22 to UC-28.
-- Run AFTER fanhubplus_full.sql and fanhubplus_crud_additions.sql.
-- Target: MySQL 8.0.16+ / MariaDB 10.6+
-- =====================================================================

USE fanhubplus;

-- UC-24 requires a moderation history. The original schema only kept the
-- latest decision on fan_submissions, so this table preserves the audit log.
CREATE TABLE IF NOT EXISTS moderation_logs (
  log_id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  submission_id   INT UNSIGNED NOT NULL,
  admin_id        INT UNSIGNED NOT NULL,
  action          ENUM('approved','rejected','resubmitted') NOT NULL,
  reason          VARCHAR(500) NULL,
  created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (log_id),
  KEY idx_ml_submission (submission_id, created_at),
  KEY idx_ml_admin (admin_id, created_at),
  CONSTRAINT fk_ml_submission FOREIGN KEY (submission_id)
    REFERENCES fan_submissions (submission_id) ON DELETE CASCADE,
  CONSTRAINT fk_ml_admin FOREIGN KEY (admin_id)
    REFERENCES users (user_id) ON DELETE RESTRICT
) ENGINE=InnoDB;

DELIMITER $$

-- ---------------------------------------------------------------------
-- UC-22: CATEGORY AND FANDOM MANAGEMENT
-- The eight categories are reference records and are not hard-deleted.
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_update_category$$
CREATE PROCEDURE sp_update_category(
  IN p_admin_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_name VARCHAR(50),
  IN p_slug VARCHAR(60),
  IN p_description TEXT,
  IN p_cover_url VARCHAR(500)
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_name IS NULL OR TRIM(p_name) = '' OR p_slug IS NULL OR TRIM(p_slug) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Category name and slug are required';
  END IF;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can update categories';
  END IF;
  SELECT category_id INTO v_id FROM categories WHERE category_id = p_category_id FOR UPDATE;
  IF v_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Category not found'; END IF;

  UPDATE categories
     SET name = TRIM(p_name), slug = TRIM(p_slug), description = p_description, cover_url = p_cover_url
   WHERE category_id = p_category_id;
  CALL sp_log_activity(p_admin_id, 'category_update', 'category', p_category_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_create_fandom$$
CREATE PROCEDURE sp_create_fandom(
  IN p_admin_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_name VARCHAR(120),
  IN p_slug VARCHAR(140),
  IN p_description TEXT,
  IN p_cover_url VARCHAR(500),
  OUT p_fandom_id INT UNSIGNED
)
BEGIN
  DECLARE v_category INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_name IS NULL OR TRIM(p_name) = '' OR p_slug IS NULL OR TRIM(p_slug) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fandom name and slug are required';
  END IF;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can create fandoms';
  END IF;
  SELECT category_id INTO v_category FROM categories WHERE category_id = p_category_id;
  IF v_category IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Category not found'; END IF;

  INSERT INTO fandoms (category_id, name, slug, description, cover_url)
  VALUES (p_category_id, TRIM(p_name), TRIM(p_slug), p_description, p_cover_url);
  SET p_fandom_id = LAST_INSERT_ID();
  CALL sp_log_activity(p_admin_id, 'fandom_create', 'fandom', p_fandom_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_update_fandom$$
CREATE PROCEDURE sp_update_fandom(
  IN p_admin_id INT UNSIGNED,
  IN p_fandom_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_name VARCHAR(120),
  IN p_slug VARCHAR(140),
  IN p_description TEXT,
  IN p_cover_url VARCHAR(500)
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE v_category INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_name IS NULL OR TRIM(p_name) = '' OR p_slug IS NULL OR TRIM(p_slug) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fandom name and slug are required';
  END IF;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can update fandoms';
  END IF;
  SELECT fandom_id INTO v_id FROM fandoms WHERE fandom_id = p_fandom_id FOR UPDATE;
  IF v_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fandom not found'; END IF;
  SELECT category_id INTO v_category FROM categories WHERE category_id = p_category_id;
  IF v_category IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Category not found'; END IF;

  UPDATE fandoms
     SET category_id = p_category_id, name = TRIM(p_name), slug = TRIM(p_slug),
         description = p_description, cover_url = p_cover_url
   WHERE fandom_id = p_fandom_id;
  CALL sp_log_activity(p_admin_id, 'fandom_update', 'fandom', p_fandom_id, NULL);
  COMMIT;
END$$

-- Hard deletion is allowed only when the fandom is not referenced. This
-- implements UC-22 A1 without silently orphaning or reassigning content.
DROP PROCEDURE IF EXISTS sp_delete_fandom$$
CREATE PROCEDURE sp_delete_fandom(
  IN p_admin_id INT UNSIGNED,
  IN p_fandom_id INT UNSIGNED
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE v_refs INT DEFAULT 0;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can delete fandoms';
  END IF;
  SELECT fandom_id INTO v_id FROM fandoms WHERE fandom_id = p_fandom_id FOR UPDATE;
  IF v_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fandom not found'; END IF;

  SELECT
    (SELECT COUNT(*) FROM contents WHERE fandom_id = p_fandom_id) +
    (SELECT COUNT(*) FROM character_profiles WHERE fandom_id = p_fandom_id) +
    (SELECT COUNT(*) FROM merchandise_items WHERE fandom_id = p_fandom_id) +
    (SELECT COUNT(*) FROM events WHERE fandom_id = p_fandom_id) +
    (SELECT COUNT(*) FROM user_fandoms WHERE fandom_id = p_fandom_id)
    INTO v_refs;
  IF v_refs > 0 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Fandom is in use; move or remove related records before deleting it';
  END IF;

  CALL sp_log_activity(p_admin_id, 'fandom_delete', 'fandom', p_fandom_id, NULL);
  DELETE FROM fandoms WHERE fandom_id = p_fandom_id;
  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- UC-23: ADMIN TAG MANAGEMENT
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_create_tag$$
CREATE PROCEDURE sp_create_tag(
  IN p_admin_id INT UNSIGNED,
  IN p_name VARCHAR(60),
  OUT p_tag_id INT UNSIGNED
)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  IF p_name IS NULL OR TRIM(p_name) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Tag name is required';
  END IF;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can create tags';
  END IF;
  INSERT INTO tags (name) VALUES (TRIM(p_name));
  SET p_tag_id = LAST_INSERT_ID();
  CALL sp_log_activity(p_admin_id, 'tag_create', 'tag', p_tag_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_update_tag$$
CREATE PROCEDURE sp_update_tag(
  IN p_admin_id INT UNSIGNED,
  IN p_tag_id INT UNSIGNED,
  IN p_name VARCHAR(60)
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  IF p_name IS NULL OR TRIM(p_name) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Tag name is required';
  END IF;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can update tags';
  END IF;
  SELECT tag_id INTO v_id FROM tags WHERE tag_id = p_tag_id FOR UPDATE;
  IF v_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Tag not found'; END IF;
  UPDATE tags SET name = TRIM(p_name) WHERE tag_id = p_tag_id;
  CALL sp_log_activity(p_admin_id, 'tag_update', 'tag', p_tag_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_delete_tag$$
CREATE PROCEDURE sp_delete_tag(
  IN p_admin_id INT UNSIGNED,
  IN p_tag_id INT UNSIGNED
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE v_refs INT DEFAULT 0;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can delete tags';
  END IF;
  SELECT tag_id INTO v_id FROM tags WHERE tag_id = p_tag_id FOR UPDATE;
  IF v_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Tag not found'; END IF;
  SELECT (SELECT COUNT(*) FROM content_tags WHERE tag_id = p_tag_id) +
         (SELECT COUNT(*) FROM merchandise_tags WHERE tag_id = p_tag_id) INTO v_refs;
  IF v_refs > 0 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Tag is in use; remove it from content first';
  END IF;
  CALL sp_log_activity(p_admin_id, 'tag_delete', 'tag', p_tag_id, NULL);
  DELETE FROM tags WHERE tag_id = p_tag_id;
  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- UC-27: FAQ / CHATBOT KNOWLEDGE-BASE MANAGEMENT (OPTIONAL)
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_create_chatbot_faq$$
CREATE PROCEDURE sp_create_chatbot_faq(
  IN p_admin_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_question TEXT,
  IN p_answer TEXT,
  IN p_keywords VARCHAR(500),
  IN p_is_active BOOLEAN,
  OUT p_faq_id INT UNSIGNED
)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  IF p_question IS NULL OR TRIM(p_question) = '' OR p_answer IS NULL OR TRIM(p_answer) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'FAQ question and answer are required';
  END IF;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can create FAQs';
  END IF;
  INSERT INTO chatbot_faqs (category_id, question, answer, keywords, is_active, created_by)
  VALUES (p_category_id, p_question, p_answer, p_keywords, COALESCE(p_is_active, TRUE), p_admin_id);
  SET p_faq_id = LAST_INSERT_ID();
  CALL sp_log_activity(p_admin_id, 'faq_create', 'faq', p_faq_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_update_chatbot_faq$$
CREATE PROCEDURE sp_update_chatbot_faq(
  IN p_admin_id INT UNSIGNED,
  IN p_faq_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_question TEXT,
  IN p_answer TEXT,
  IN p_keywords VARCHAR(500),
  IN p_is_active BOOLEAN
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  IF p_question IS NULL OR TRIM(p_question) = '' OR p_answer IS NULL OR TRIM(p_answer) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'FAQ question and answer are required';
  END IF;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can update FAQs';
  END IF;
  SELECT faq_id INTO v_id FROM chatbot_faqs WHERE faq_id = p_faq_id FOR UPDATE;
  IF v_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'FAQ not found'; END IF;
  UPDATE chatbot_faqs
     SET category_id = p_category_id, question = p_question, answer = p_answer,
         keywords = p_keywords, is_active = COALESCE(p_is_active, TRUE)
   WHERE faq_id = p_faq_id;
  CALL sp_log_activity(p_admin_id, 'faq_update', 'faq', p_faq_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_delete_chatbot_faq$$
CREATE PROCEDURE sp_delete_chatbot_faq(
  IN p_admin_id INT UNSIGNED,
  IN p_faq_id INT UNSIGNED
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can delete FAQs';
  END IF;
  SELECT faq_id INTO v_id FROM chatbot_faqs WHERE faq_id = p_faq_id FOR UPDATE;
  IF v_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'FAQ not found'; END IF;
  CALL sp_log_activity(p_admin_id, 'faq_delete', 'faq', p_faq_id, NULL);
  DELETE FROM chatbot_faqs WHERE faq_id = p_faq_id;
  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- UC-14 / UC-24: MODERATION QUEUE AND RESUBMISSION
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_get_moderation_queue$$
CREATE PROCEDURE sp_get_moderation_queue(IN p_admin_id INT UNSIGNED)
BEGIN
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view the moderation queue';
  END IF;
  SELECT fs.submission_id, fs.user_id, u.name AS submitter_name, u.email,
         fs.category_id, c.name AS category_name, fs.title, fs.body,
         fs.cover_image_url, fs.status, fs.created_at
    FROM fan_submissions fs
    JOIN users u ON u.user_id = fs.user_id
    JOIN categories c ON c.category_id = fs.category_id
   WHERE fs.status = 'pending'
   ORDER BY fs.created_at, fs.submission_id;
END$$

DROP PROCEDURE IF EXISTS sp_resubmit_fan_content$$
CREATE PROCEDURE sp_resubmit_fan_content(
  IN p_user_id INT UNSIGNED,
  IN p_submission_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_title VARCHAR(255),
  IN p_body LONGTEXT,
  IN p_cover_image_url VARCHAR(500)
)
BEGIN
  DECLARE v_owner INT UNSIGNED DEFAULT NULL;
  DECLARE v_status VARCHAR(10) DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_title IS NULL OR TRIM(p_title) = '' OR p_body IS NULL OR TRIM(p_body) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Title and body are required';
  END IF;
  START TRANSACTION;
  SELECT user_id, status INTO v_owner, v_status
    FROM fan_submissions WHERE submission_id = p_submission_id FOR UPDATE;
  IF v_owner IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Submission not found'; END IF;
  IF v_owner <> p_user_id THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'You can only edit your own submission'; END IF;
  IF v_status <> 'rejected' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only rejected submissions can be resubmitted';
  END IF;

  UPDATE fan_submissions
     SET category_id = p_category_id, title = TRIM(p_title), body = p_body,
         cover_image_url = p_cover_image_url, status = 'pending',
         reviewed_by = NULL, reviewed_at = NULL, reject_reason = NULL,
         published_content_id = NULL
   WHERE submission_id = p_submission_id;
  -- The submitter is a member, not an administrator. Keep this action in
  -- activity_logs; moderation_logs remains an administrator audit trail.
  CALL sp_log_activity(p_user_id, 'submission_resubmit', 'submission', p_submission_id, NULL);
  COMMIT;
END$$

-- Review variant that lets the administrator correct category and attach
-- tags before publishing, as required by UC-24 B3.
DROP PROCEDURE IF EXISTS sp_review_submission_with_metadata$$
CREATE PROCEDURE sp_review_submission_with_metadata(
  IN p_submission_id INT UNSIGNED,
  IN p_admin_id INT UNSIGNED,
  IN p_decision VARCHAR(10),
  IN p_category_id INT UNSIGNED,
  IN p_reason VARCHAR(500),
  IN p_tag_ids JSON,
  OUT p_content_id INT UNSIGNED
)
BEGIN
  DECLARE v_status VARCHAR(10) DEFAULT NULL;
  DECLARE v_user INT UNSIGNED DEFAULT NULL;
  DECLARE v_old_category INT UNSIGNED DEFAULT NULL;
  DECLARE v_title VARCHAR(255) DEFAULT NULL;
  DECLARE v_body LONGTEXT DEFAULT NULL;
  DECLARE v_cover VARCHAR(500) DEFAULT NULL;
  DECLARE v_category INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_decision NOT IN ('approved', 'rejected') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Decision must be approved or rejected';
  END IF;
  IF p_decision = 'rejected' AND (p_reason IS NULL OR TRIM(p_reason) = '') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'A reason is required when rejecting';
  END IF;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can review submissions';
  END IF;
  SELECT status, user_id, category_id, title, body, cover_image_url
    INTO v_status, v_user, v_old_category, v_title, v_body, v_cover
    FROM fan_submissions WHERE submission_id = p_submission_id FOR UPDATE;
  IF v_status IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Submission not found'; END IF;
  IF v_status <> 'pending' THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Submission was already reviewed'; END IF;

  SET v_category = COALESCE(p_category_id, v_old_category);
  SELECT category_id INTO v_category FROM categories WHERE category_id = v_category;
  IF v_category IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Category not found'; END IF;

  IF p_decision = 'approved' THEN
    INSERT INTO contents (category_id, title, slug, type, body, thumbnail_url, status, created_by)
    VALUES (v_category, v_title,
            CONCAT(LEFT(TRIM(BOTH '-' FROM REGEXP_REPLACE(LOWER(v_title), '[^a-z0-9]+', '-')), 200),
                   '-s', p_submission_id),
            'article', v_body, v_cover, 'published', v_user);
    SET p_content_id = LAST_INSERT_ID();

    IF p_tag_ids IS NOT NULL THEN
      INSERT INTO content_tags (content_id, tag_id)
      SELECT DISTINCT p_content_id, jt.id
        FROM JSON_TABLE(p_tag_ids, '$[*]' COLUMNS (id INT UNSIGNED PATH '$')) AS jt;
    END IF;
  ELSE
    SET p_content_id = NULL;
  END IF;

  UPDATE fan_submissions
     SET status = p_decision, category_id = v_category, reviewed_by = p_admin_id,
         reviewed_at = NOW(), reject_reason = IF(p_decision = 'rejected', p_reason, NULL),
         published_content_id = p_content_id
   WHERE submission_id = p_submission_id;
  INSERT INTO moderation_logs (submission_id, admin_id, action, reason)
  VALUES (p_submission_id, p_admin_id, p_decision, p_reason);
  CALL sp_log_activity(p_admin_id, CONCAT('submission_', p_decision), 'submission', p_submission_id, NULL);
  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- UC-25 / UC-26: ADMIN LISTS AND ACCOUNT CONTROL
-- ---------------------------------------------------------------------
DROP PROCEDURE IF EXISTS sp_admin_list_feedback$$
CREATE PROCEDURE sp_admin_list_feedback(
  IN p_admin_id INT UNSIGNED,
  IN p_status VARCHAR(20),
  IN p_type VARCHAR(20)
)
BEGIN
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view feedback';
  END IF;
  SELECT f.feedback_id, f.user_id, COALESCE(u.name, 'Visitor') AS sender_name,
         f.contact_email, f.type, f.subject, f.message, f.status,
         f.admin_response, f.handled_by, f.resolved_at, f.created_at,
         h.name AS handler_name
    FROM feedbacks f
    LEFT JOIN users u ON u.user_id = f.user_id
    LEFT JOIN users h ON h.user_id = f.handled_by
   WHERE (p_status IS NULL OR f.status = p_status)
     AND (p_type IS NULL OR f.type = p_type)
   ORDER BY FIELD(f.status, 'new', 'in_progress', 'resolved', 'closed'), f.created_at;
END$$

DROP PROCEDURE IF EXISTS sp_admin_list_users$$
CREATE PROCEDURE sp_admin_list_users(
  IN p_admin_id INT UNSIGNED,
  IN p_role VARCHAR(10),
  IN p_is_active BOOLEAN
)
BEGIN
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can view users';
  END IF;
  SELECT u.user_id, u.name, u.email, u.role, u.is_active, u.avatar_url,
         u.email_verified_at, u.last_login_at, u.created_at,
         (SELECT COUNT(*) FROM fan_submissions fs WHERE fs.user_id = u.user_id) AS submission_count,
         (SELECT COUNT(*) FROM bookmarks b WHERE b.user_id = u.user_id) AS bookmark_count
    FROM users u
   WHERE (p_role IS NULL OR u.role = p_role)
     AND (p_is_active IS NULL OR u.is_active = p_is_active)
   ORDER BY u.created_at DESC;
END$$

DROP PROCEDURE IF EXISTS sp_admin_deactivate_user$$
CREATE PROCEDURE sp_admin_deactivate_user(
  IN p_admin_id INT UNSIGNED,
  IN p_user_id INT UNSIGNED
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_admin_id = p_user_id THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'An administrator cannot deactivate their own account';
  END IF;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can deactivate users';
  END IF;
  SELECT user_id INTO v_id FROM users WHERE user_id = p_user_id FOR UPDATE;
  IF v_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'User not found'; END IF;
  UPDATE users SET is_active = FALSE WHERE user_id = p_user_id;
  CALL sp_log_activity(p_admin_id, 'user_deactivate', 'user', p_user_id, NULL);
  COMMIT;
END$$

DELIMITER ;

-- Example calls (do not run automatically):
-- CALL sp_update_category(1, 1, 'Anime', 'anime', 'Description', NULL);
-- CALL sp_create_fandom(1, 1, 'One Piece', 'one-piece', NULL, NULL, @fandom_id);
-- CALL sp_create_tag(1, 'Limited Edition', @tag_id);
-- CALL sp_create_chatbot_faq(1, NULL, 'Question?', 'Answer', 'keywords', TRUE, @faq_id);
-- CALL sp_get_moderation_queue(1);
-- CALL sp_resubmit_fan_content(2, 5, 1, 'Corrected title', 'Corrected body', NULL);
-- CALL sp_admin_list_feedback(1, 'new', NULL);
-- CALL sp_admin_list_users(1, 'user', FALSE);
-- =====================================================================


-- =====================================================================
-- SUPPLEMENT 4: USE CASE GAP FIXES
-- =====================================================================
-- =====================================================================
-- FAN HUB PLUS - USE CASE GAP FIXES
-- Fills the gaps identified in section 9 of FanHubPlus_DacTa_UseCase.docx.
-- Run AFTER:
--   1) fanhubplus_full.sql
--   2) fanhubplus_crud_additions.sql
--   3) fanhubplus_usecase_alignment.sql
--   4) fanhubplus_reporting_procedures.sql
-- Target: MySQL 8.0.16+ / MariaDB 10.6+
-- =====================================================================

USE fanhubplus;

-- ---------------------------------------------------------------------
-- 1. SCHEMA FIELDS
-- ---------------------------------------------------------------------

-- BR-07: legal source/licence information for published media.
ALTER TABLE contents
  ADD COLUMN IF NOT EXISTS source_name VARCHAR(150) NULL AFTER embed_url,
  ADD COLUMN IF NOT EXISTS source_url VARCHAR(500) NULL AFTER source_name,
  ADD COLUMN IF NOT EXISTS license_url VARCHAR(500) NULL AFTER source_url,
  ADD COLUMN IF NOT EXISTS rights_confirmed BOOLEAN NOT NULL DEFAULT FALSE AFTER license_url;

-- BR-07 and UC-14: fan-submitter rights confirmation and media metadata.
ALTER TABLE fan_submissions
  ADD COLUMN IF NOT EXISTS content_type ENUM('article','video','audio','image','trailer','explainer')
    NOT NULL DEFAULT 'article' AFTER category_id,
  ADD COLUMN IF NOT EXISTS media_url VARCHAR(500) NULL AFTER body,
  ADD COLUMN IF NOT EXISTS source_url VARCHAR(500) NULL AFTER media_url,
  ADD COLUMN IF NOT EXISTS rights_confirmed BOOLEAN NOT NULL DEFAULT FALSE AFTER source_url;

-- UC-15: dynamic bug-feedback fields. They remain NULL for suggestion/query.
ALTER TABLE feedbacks
  ADD COLUMN IF NOT EXISTS page_url VARCHAR(500) NULL AFTER subject,
  ADD COLUMN IF NOT EXISTS reproduction_steps TEXT NULL AFTER page_url,
  ADD COLUMN IF NOT EXISTS browser_info VARCHAR(500) NULL AFTER reproduction_steps,
  ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE AFTER status,
  ADD COLUMN IF NOT EXISTS deleted_by INT UNSIGNED NULL AFTER is_deleted,
  ADD COLUMN IF NOT EXISTS deleted_at DATETIME NULL AFTER deleted_by;

-- UC-22: hide a fandom instead of deleting a referenced fandom.
ALTER TABLE fandoms
  ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE AFTER cover_url;

-- BR-17: session revocation is represented by a per-user version.
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS session_version INT UNSIGNED NOT NULL DEFAULT 1 AFTER is_active;

-- UC-13 / BR-10: allow one bookmark to target an event as well.
ALTER TABLE bookmarks
  ADD COLUMN IF NOT EXISTS event_id INT UNSIGNED NULL AFTER merchandise_id,
  ADD UNIQUE KEY uq_bm_event (user_id, event_id),
  ADD KEY idx_bm_event (event_id),
  ADD CONSTRAINT fk_bm_event FOREIGN KEY (event_id)
    REFERENCES events (event_id) ON DELETE CASCADE;

-- UC-16 A2: optional dashboard block visibility and ordering per member.
CREATE TABLE IF NOT EXISTS user_dashboard_widgets (
  user_id       INT UNSIGNED NOT NULL,
  widget_key    ENUM('activity','favorites','bookmarks','recommendations','events') NOT NULL,
  is_visible    BOOLEAN NOT NULL DEFAULT TRUE,
  sort_order    TINYINT UNSIGNED NOT NULL DEFAULT 0,
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, widget_key),
  CONSTRAINT fk_udw_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. BOOKMARK TARGET INTEGRITY INCLUDING EVENTS
-- ---------------------------------------------------------------------

DROP TRIGGER IF EXISTS trg_bookmarks_one_target;
DROP TRIGGER IF EXISTS trg_bookmarks_one_target_update;

DELIMITER $$

CREATE TRIGGER trg_bookmarks_one_target
BEFORE INSERT ON bookmarks
FOR EACH ROW
BEGIN
  IF (NEW.content_id IS NOT NULL) + (NEW.character_id IS NOT NULL) +
     (NEW.merchandise_id IS NOT NULL) + (NEW.event_id IS NOT NULL) <> 1 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'A bookmark must reference exactly one target';
  END IF;
END$$

CREATE TRIGGER trg_bookmarks_one_target_update
BEFORE UPDATE ON bookmarks
FOR EACH ROW
BEGIN
  IF (NEW.content_id IS NOT NULL) + (NEW.character_id IS NOT NULL) +
     (NEW.merchandise_id IS NOT NULL) + (NEW.event_id IS NOT NULL) <> 1 THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'A bookmark must reference exactly one target';
  END IF;
END$$

DELIMITER ;

DELIMITER $$

-- ---------------------------------------------------------------------
-- 3. CONTENT / MEDIA RIGHTS PROCEDURES
-- ---------------------------------------------------------------------

-- Create or update the legal-source metadata of an existing content item.
-- Published media must have a source and explicit rights confirmation.
DROP PROCEDURE IF EXISTS sp_update_content_rights$$
CREATE PROCEDURE sp_update_content_rights(
  IN p_admin_id INT UNSIGNED,
  IN p_content_id INT UNSIGNED,
  IN p_source_name VARCHAR(150),
  IN p_source_url VARCHAR(500),
  IN p_license_url VARCHAR(500),
  IN p_rights_confirmed BOOLEAN
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE v_type VARCHAR(20) DEFAULT NULL;
  DECLARE v_status VARCHAR(20) DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can update media rights';
  END IF;
  SELECT content_id, type, status INTO v_id, v_type, v_status
    FROM contents WHERE content_id = p_content_id FOR UPDATE;
  IF v_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Content not found'; END IF;

  IF v_status = 'published' AND v_type IN ('video','audio','trailer','explainer')
     AND (p_source_url IS NULL OR TRIM(p_source_url) = '' OR COALESCE(p_rights_confirmed, FALSE) = FALSE) THEN
    SIGNAL SQLSTATE '45000'
      SET MESSAGE_TEXT = 'Published media requires a source URL and rights confirmation';
  END IF;

  UPDATE contents
     SET source_name = p_source_name, source_url = p_source_url,
         license_url = p_license_url, rights_confirmed = COALESCE(p_rights_confirmed, FALSE)
   WHERE content_id = p_content_id;
  CALL sp_log_activity(p_admin_id, 'content_rights_update', 'content', p_content_id, NULL);
  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- 4. FAN SUBMISSION RIGHTS AND RESUBMISSION
-- ---------------------------------------------------------------------

DROP PROCEDURE IF EXISTS sp_submit_fan_content_v2$$
CREATE PROCEDURE sp_submit_fan_content_v2(
  IN p_user_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_content_type VARCHAR(20),
  IN p_title VARCHAR(255),
  IN p_body LONGTEXT,
  IN p_media_url VARCHAR(500),
  IN p_source_url VARCHAR(500),
  IN p_cover_image_url VARCHAR(500),
  IN p_rights_confirmed BOOLEAN,
  OUT p_submission_id INT UNSIGNED
)
BEGIN
  DECLARE v_user INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_title IS NULL OR TRIM(p_title) = '' OR p_body IS NULL OR TRIM(p_body) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Title and body are required';
  END IF;
  IF p_content_type NOT IN ('article','video','audio','image','trailer','explainer') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid fan content type';
  END IF;
  IF COALESCE(p_rights_confirmed, FALSE) = FALSE THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'The submitter must confirm usage rights';
  END IF;

  START TRANSACTION;
  SELECT user_id INTO v_user FROM users
   WHERE user_id = p_user_id AND is_active = TRUE FOR UPDATE;
  IF v_user IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'User not found or inactive'; END IF;

  INSERT INTO fan_submissions
    (user_id, category_id, content_type, title, body, media_url, source_url,
     cover_image_url, rights_confirmed)
  VALUES
    (p_user_id, p_category_id, p_content_type, TRIM(p_title), p_body, p_media_url,
     p_source_url, p_cover_image_url, TRUE);
  SET p_submission_id = LAST_INSERT_ID();
  CALL sp_log_activity(p_user_id, 'submit_content', 'submission', p_submission_id, p_content_type);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_resubmit_fan_content_v2$$
CREATE PROCEDURE sp_resubmit_fan_content_v2(
  IN p_user_id INT UNSIGNED,
  IN p_submission_id INT UNSIGNED,
  IN p_category_id INT UNSIGNED,
  IN p_content_type VARCHAR(20),
  IN p_title VARCHAR(255),
  IN p_body LONGTEXT,
  IN p_media_url VARCHAR(500),
  IN p_source_url VARCHAR(500),
  IN p_cover_image_url VARCHAR(500),
  IN p_rights_confirmed BOOLEAN
)
BEGIN
  DECLARE v_owner INT UNSIGNED DEFAULT NULL;
  DECLARE v_status VARCHAR(10) DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  IF p_title IS NULL OR TRIM(p_title) = '' OR p_body IS NULL OR TRIM(p_body) = '' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Title and body are required';
  END IF;
  IF p_content_type NOT IN ('article','video','audio','image','trailer','explainer') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Invalid fan content type';
  END IF;
  IF COALESCE(p_rights_confirmed, FALSE) = FALSE THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'The submitter must confirm usage rights';
  END IF;

  START TRANSACTION;
  SELECT user_id, status INTO v_owner, v_status
    FROM fan_submissions WHERE submission_id = p_submission_id FOR UPDATE;
  IF v_owner IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Submission not found'; END IF;
  IF v_owner <> p_user_id THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'You can only edit your own submission'; END IF;
  IF v_status <> 'rejected' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only rejected submissions can be resubmitted';
  END IF;

  UPDATE fan_submissions
     SET category_id = p_category_id, content_type = p_content_type,
         title = TRIM(p_title), body = p_body, media_url = p_media_url,
         source_url = p_source_url, cover_image_url = p_cover_image_url,
         rights_confirmed = TRUE, status = 'pending', reviewed_by = NULL,
         reviewed_at = NULL, reject_reason = NULL, published_content_id = NULL
   WHERE submission_id = p_submission_id;
  CALL sp_log_activity(p_user_id, 'submission_resubmit', 'submission', p_submission_id, NULL);
  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- 5. EVENT BOOKMARKS AND DASHBOARD SUPPORT
-- ---------------------------------------------------------------------

DROP PROCEDURE IF EXISTS sp_add_event_bookmark$$
CREATE PROCEDURE sp_add_event_bookmark(
  IN p_user_id INT UNSIGNED,
  IN p_event_id INT UNSIGNED,
  IN p_note TEXT,
  OUT p_bookmark_id INT UNSIGNED
)
BEGIN
  DECLARE v_event INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  START TRANSACTION;
  SELECT event_id INTO v_event FROM events WHERE event_id = p_event_id FOR UPDATE;
  IF v_event IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Event not found'; END IF;

  INSERT INTO bookmarks (user_id, event_id, note)
  VALUES (p_user_id, p_event_id, p_note)
  ON DUPLICATE KEY UPDATE note = COALESCE(p_note, note);
  SELECT bookmark_id INTO p_bookmark_id
    FROM bookmarks WHERE user_id = p_user_id AND event_id = p_event_id;
  CALL sp_log_activity(p_user_id, 'bookmark_add', 'event', p_event_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_get_dashboard_layout$$
CREATE PROCEDURE sp_get_dashboard_layout(IN p_user_id INT UNSIGNED)
BEGIN
  SELECT widget_key, is_visible, sort_order
    FROM user_dashboard_widgets
   WHERE user_id = p_user_id
   ORDER BY sort_order, widget_key;
END$$

DROP PROCEDURE IF EXISTS sp_set_dashboard_layout$$
CREATE PROCEDURE sp_set_dashboard_layout(
  IN p_user_id INT UNSIGNED,
  IN p_layout JSON
)
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  IF p_layout IS NULL OR JSON_TYPE(p_layout) <> 'ARRAY' THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Dashboard layout must be a JSON array';
  END IF;

  START TRANSACTION;
  DELETE FROM user_dashboard_widgets WHERE user_id = p_user_id;
  INSERT INTO user_dashboard_widgets (user_id, widget_key, is_visible, sort_order)
  SELECT p_user_id, jt.widget_key, COALESCE(jt.is_visible, TRUE), COALESCE(jt.sort_order, 0)
    FROM JSON_TABLE(
      p_layout, '$[*]' COLUMNS (
        widget_key VARCHAR(30) PATH '$.widget_key',
        is_visible BOOLEAN PATH '$.is_visible' NULL ON EMPTY,
        sort_order TINYINT UNSIGNED PATH '$.sort_order' NULL ON EMPTY
      )
    ) AS jt;
  CALL sp_log_activity(p_user_id, 'dashboard_layout_update', 'user', p_user_id, NULL);
  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- 6. MERCHANDISE VIEW ANALYTICS
-- Keeps the old sp_view_merchandise signature intact and adds a user-aware
-- version that records period-specific activity for UC-28 reporting.
-- ---------------------------------------------------------------------

DROP PROCEDURE IF EXISTS sp_view_merchandise_with_activity$$
CREATE PROCEDURE sp_view_merchandise_with_activity(
  IN p_item_id INT UNSIGNED,
  IN p_user_id INT UNSIGNED
)
BEGIN
  DECLARE v_item INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

  START TRANSACTION;
  SELECT item_id INTO v_item FROM merchandise_items WHERE item_id = p_item_id FOR UPDATE;
  IF v_item IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Merchandise item not found'; END IF;
  UPDATE merchandise_items SET view_count = view_count + 1 WHERE item_id = p_item_id;
  CALL sp_log_activity(p_user_id, 'view', 'merchandise', p_item_id, NULL);
  COMMIT;

  SELECT m.*, cat.name AS category_name
    FROM merchandise_items m JOIN categories cat ON cat.category_id = m.category_id
   WHERE m.item_id = p_item_id;
  SELECT t.tag_id, t.name
    FROM merchandise_tags mt JOIN tags t ON t.tag_id = mt.tag_id
   WHERE mt.item_id = p_item_id;
  SELECT image_id, image_url, caption
    FROM merchandise_images WHERE item_id = p_item_id ORDER BY sort_order, image_id;
END$$

-- ---------------------------------------------------------------------
-- 7. FEEDBACK DELETE / SOFT DELETE
-- ---------------------------------------------------------------------

DROP PROCEDURE IF EXISTS sp_delete_feedback$$
CREATE PROCEDURE sp_delete_feedback(
  IN p_admin_id INT UNSIGNED,
  IN p_feedback_id INT UNSIGNED
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can delete feedback';
  END IF;
  SELECT feedback_id INTO v_id FROM feedbacks
   WHERE feedback_id = p_feedback_id AND is_deleted = FALSE FOR UPDATE;
  IF v_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Feedback not found'; END IF;

  UPDATE feedbacks
     SET is_deleted = TRUE, deleted_by = p_admin_id, deleted_at = NOW(), status = 'closed'
   WHERE feedback_id = p_feedback_id;
  CALL sp_log_activity(p_admin_id, 'feedback_delete', 'feedback', p_feedback_id, NULL);
  COMMIT;
END$$

-- ---------------------------------------------------------------------
-- 8. FANDOM VISIBILITY AND USER SESSION REVOCATION
-- ---------------------------------------------------------------------

DROP PROCEDURE IF EXISTS sp_set_fandom_visibility$$
CREATE PROCEDURE sp_set_fandom_visibility(
  IN p_admin_id INT UNSIGNED,
  IN p_fandom_id INT UNSIGNED,
  IN p_is_active BOOLEAN
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can change fandom visibility';
  END IF;
  SELECT fandom_id INTO v_id FROM fandoms WHERE fandom_id = p_fandom_id FOR UPDATE;
  IF v_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Fandom not found'; END IF;
  UPDATE fandoms SET is_active = COALESCE(p_is_active, FALSE) WHERE fandom_id = p_fandom_id;
  CALL sp_log_activity(p_admin_id, 'fandom_visibility_update', 'fandom', p_fandom_id, NULL);
  COMMIT;
END$$

DROP PROCEDURE IF EXISTS sp_revoke_user_sessions$$
CREATE PROCEDURE sp_revoke_user_sessions(
  IN p_admin_id INT UNSIGNED,
  IN p_user_id INT UNSIGNED
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can revoke sessions';
  END IF;
  SELECT user_id INTO v_id FROM users WHERE user_id = p_user_id FOR UPDATE;
  IF v_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'User not found'; END IF;
  UPDATE users SET session_version = session_version + 1 WHERE user_id = p_user_id;
  CALL sp_log_activity(p_admin_id, 'session_revoke', 'user', p_user_id, NULL);
  COMMIT;
END$$

-- Deactivate and revoke in one atomic operation, satisfying BR-17.
DROP PROCEDURE IF EXISTS sp_admin_deactivate_user_v2$$
CREATE PROCEDURE sp_admin_deactivate_user_v2(
  IN p_admin_id INT UNSIGNED,
  IN p_user_id INT UNSIGNED
)
BEGIN
  DECLARE v_id INT UNSIGNED DEFAULT NULL;
  DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
  IF p_admin_id = p_user_id THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'An administrator cannot deactivate their own account';
  END IF;
  START TRANSACTION;
  IF NOT fn_is_admin(p_admin_id) THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Only administrators can deactivate users';
  END IF;
  SELECT user_id INTO v_id FROM users WHERE user_id = p_user_id FOR UPDATE;
  IF v_id IS NULL THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'User not found'; END IF;
  UPDATE users SET is_active = FALSE, session_version = session_version + 1
   WHERE user_id = p_user_id;
  CALL sp_log_activity(p_admin_id, 'user_deactivate', 'user', p_user_id, 'sessions revoked');
  COMMIT;
END$$

DELIMITER ;

-- Notes for the application layer:
-- 1. Include users.session_version in the JWT. Reject a token when its
--    version differs from the current database value or when is_active=0.
-- 2. Use sp_view_merchandise_with_activity(item_id, user_id) for views that
--    must appear in period-based reports. Use NULL for a visitor.
-- 3. Exclude feedbacks WHERE is_deleted=TRUE from admin lists and reports.
-- 4. Filter public fandom selectors with is_active=TRUE.
-- 5. Use https URLs and validate upload type/size in the backend.
-- =====================================================================


-- =====================================================================
-- END FAN HUB PLUS COMPLETE DATABASE PACKAGE
-- =====================================================================
