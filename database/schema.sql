-- locations: dimension table from taxi_zone_lookup.csv
CREATE TABLE locations (
    location_id   INTEGER PRIMARY KEY,
    borough       TEXT NOT NULL,
    zone          TEXT NOT NULL,
    service_zone  TEXT
);

-- zone_boundaries: spatial polygon data from taxi_zones shapefile
-- geometry is stored as GeoJSON text, reprojected to WGS84 (lat/lon)
-- so the frontend can render it directly on a Leaflet map
CREATE TABLE zone_boundaries (
    location_id   INTEGER PRIMARY KEY,
    zone          TEXT,
    borough       TEXT,
    shape_area    REAL,
    shape_length  REAL,
    geometry      TEXT,

    FOREIGN KEY (location_id) REFERENCES locations (location_id)
);