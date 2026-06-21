-- locations: dimension table from taxi_zone_lookup.csv
CREATE TABLE IF NOT EXISTS locations (
    location_id   INTEGER PRIMARY KEY,
    borough       TEXT NOT NULL,
    zone          TEXT NOT NULL,
    service_zone  TEXT
);

-- zone_boundaries: spatial polygon data from taxi_zones shapefile
-- geometry is stored as GeoJSON text, reprojected to WGS84 (lat/lon)
-- so the frontend can render it directly on a Leaflet map
CREATE TABLE IF NOT EXISTS zone_boundaries (
    location_id   INTEGER PRIMARY KEY,
    zone          TEXT,
    borough       TEXT,
    shape_area    REAL,
    shape_length  REAL,
    geometry      TEXT,

    FOREIGN KEY (location_id) REFERENCES locations (location_id)
);

-- trips: cleaned, validated, outlier-flagged, zone-merged, and
-- feature-engineered records from yellow_tripdata_2019-01.parquet
CREATE TABLE IF NOT EXISTS trips (
    trip_id                INTEGER PRIMARY KEY AUTOINCREMENT,

    -- raw trip fields (validator.py / cleaner.py)
    vendor_id              INTEGER,
    pickup_datetime        TEXT NOT NULL,
    dropoff_datetime       TEXT NOT NULL,
    passenger_count        INTEGER,
    trip_distance          REAL NOT NULL CHECK (trip_distance >= 0),
    rate_code_id           INTEGER,
    store_and_fwd_flag     TEXT,
    pu_location_id         INTEGER NOT NULL,
    do_location_id         INTEGER NOT NULL,
    payment_type           INTEGER,
    fare_amount            REAL NOT NULL CHECK (fare_amount >= 0),
    extra                  REAL,
    mta_tax                REAL,
    tip_amount              REAL,
    tolls_amount            REAL,
    improvement_surcharge  REAL,
    total_amount            REAL NOT NULL CHECK (total_amount >= 0),
    congestion_surcharge   REAL,
    airport_fee             REAL,

    -- outlier_detector.py: rows are kept, just flagged
    is_outlier              INTEGER NOT NULL DEFAULT 0 CHECK (is_outlier IN (0, 1)),
    outlier_reasons          TEXT,

    -- zone_to_trip_merger.py: denormalized zone names for fast
    -- single-table revenue and mobility queries
    pickup_borough          TEXT,
    pickup_zone              TEXT,
    pickup_service_zone     TEXT,
    dropoff_borough          TEXT,
    dropoff_zone              TEXT,
    dropoff_service_zone     TEXT,

    -- feature_engineer.py: derived analytical columns
    trip_duration_minutes    REAL,
    average_speed_mph        REAL,
    fare_per_mile             REAL,
    pickup_hour               INTEGER CHECK (pickup_hour IS NULL OR pickup_hour BETWEEN 0 AND 23),
    pickup_day_of_week        TEXT,
    tip_percentage             REAL,

    FOREIGN KEY (pu_location_id) REFERENCES locations (location_id),
    FOREIGN KEY (do_location_id) REFERENCES locations (location_id)
);

-- suspicious_records: rows removed by cleaner.py before outlier
-- detection, zone merging, or feature engineering ran. All raw
-- columns are nullable since a bad/missing value is often the
-- reason the row was removed in the first place.
CREATE TABLE IF NOT EXISTS suspicious_records (
    record_id              INTEGER PRIMARY KEY AUTOINCREMENT,

    vendor_id               INTEGER,
    pickup_datetime          TEXT,
    dropoff_datetime         TEXT,
    passenger_count          INTEGER,
    trip_distance             REAL,
    rate_code_id              INTEGER,
    store_and_fwd_flag       TEXT,
    pu_location_id            INTEGER,
    do_location_id            INTEGER,
    payment_type               INTEGER,
    fare_amount                REAL,
    extra                       REAL,
    mta_tax                     REAL,
    tip_amount                   REAL,
    tolls_amount                 REAL,
    improvement_surcharge       REAL,
    total_amount                  REAL,
    congestion_surcharge         REAL,
    airport_fee                   REAL,

    removal_reason                TEXT NOT NULL,
    flagged_at                     TEXT NOT NULL DEFAULT (datetime('now'))
);