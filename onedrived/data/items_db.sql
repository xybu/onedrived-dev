CREATE TABLE IF NOT EXISTS items (
  id            TEXT UNIQUE ON CONFLICT REPLACE,
  type          INT,
  name          TEXT,
  parent_id     TEXT,
  parent_path   TEXT,
  etag          TEXT,
  ctag          TEXT,
  size          UNSIGNED BIG INT,
  size_local    UNSIGNED BIG INT,
  created_time  TEXT,
  modified_time TEXT,
  status        INT,
  sha1_hash     TEXT,
  record_time   TEXT,
  PRIMARY KEY (parent_path, name) ON CONFLICT REPLACE
);
