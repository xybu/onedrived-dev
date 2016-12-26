CREATE TABLE IF NOT EXISTS items (
  item_id       TEXT UNIQUE PRIMARY KEY ON CONFLICT REPLACE,
  type          TEXT,
  item_name     TEXT,
  parent_id     TEXT,
  parent_path   TEXT,
  etag          TEXT,
  ctag          TEXT,
  size          UNSIGNED BIG INT,
  size_local    UNSIGNED BIG INT,
  created_time  TEXT,
  modified_time TEXT,
  status        TEXT,
  sha1_hash     TEXT
);
