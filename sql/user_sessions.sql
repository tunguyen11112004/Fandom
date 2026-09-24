-- Extra app table for refresh tokens (logout/refresh).
-- Dump fanhubplus_all_in_one.sql uses users.session_version in JWT for BR-17.
-- Run after importing the dump if you need refresh-token sessions.

USE fanhubplus;

CREATE TABLE IF NOT EXISTS user_sessions (
  session_id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id             INT UNSIGNED NOT NULL,
  refresh_token_hash  CHAR(64) NOT NULL,
  expires_at          DATETIME NOT NULL,
  revoked_at          DATETIME NULL,
  created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (session_id),
  UNIQUE KEY uq_user_sessions_hash (refresh_token_hash),
  KEY idx_user_sessions_user (user_id),
  CONSTRAINT fk_user_sessions_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
) ENGINE=InnoDB;
