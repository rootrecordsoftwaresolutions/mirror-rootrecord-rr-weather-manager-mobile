-- D1 (SQLite): isolated weather snapshots for the Weather Manager Worker.
-- Apply in the rootrecord-primary (or equivalent) migration pipeline.
-- Each successful upstream fetch inserts one row (historical series).
-- Serve cached bundle when the latest row for (user_id, grid_key) is within TTL.

CREATE TABLE IF NOT EXISTS weather_data (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  location_id TEXT,
  grid_key TEXT NOT NULL,
  lat REAL NOT NULL,
  lon REAL NOT NULL,
  fetched_at TEXT NOT NULL,
  bundle_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_weather_data_user_grid_time
  ON weather_data (user_id, grid_key, fetched_at DESC);

CREATE INDEX IF NOT EXISTS idx_weather_data_user_location_time
  ON weather_data (user_id, location_id, fetched_at DESC);

-- Optional later: scheduled DELETE of rows older than N days to cap growth.
