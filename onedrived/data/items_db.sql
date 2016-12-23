CREATE TABLE IF NOT EXISTS items (
  item_id       TEXT UNIQUE PRIMARY KEY ON CONFLICT REPLACE,
  type          TEXT,
  item_name     TEXT,
  parent_id     TEXT,
  parent_path   TEXT,
  etag          TEXT,
  ctag          TEXT,
  size          INT,
  created_time  TEXT,
  modified_time TEXT,
  status        TEXT,
  crc32_hash    TEXT,
  sha1_hash     TEXT
);
