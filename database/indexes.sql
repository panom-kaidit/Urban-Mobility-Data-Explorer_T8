-- run AFTER data has been loaded into trips and zone_boundaries

-- revenue trend queries grouped by date
CREATE INDEX IF NOT EXISTS idx_trips_pickup_datetime ON trips (pickup_datetime);

-- pickup and dropoff zone analytics
CREATE INDEX IF NOT EXISTS idx_trips_pu_location_id ON trips (pu_location_id);
CREATE INDEX IF NOT EXISTS idx_trips_do_location_id ON trips (do_location_id);

-- revenue-by-borough grouping (no JOIN needed, columns are denormalized)
CREATE INDEX IF NOT EXISTS idx_trips_pickup_borough ON trips (pickup_borough);
CREATE INDEX IF NOT EXISTS idx_trips_dropoff_borough ON trips (dropoff_borough);

-- outlier analytics
CREATE INDEX IF NOT EXISTS idx_trips_is_outlier ON trips (is_outlier);

-- payment-type analytics
CREATE INDEX IF NOT EXISTS idx_trips_payment_type ON trips (payment_type);

-- fare distribution analytics
CREATE INDEX IF NOT EXISTS idx_trips_fare_amount ON trips (fare_amount);

-- zone boundary lookups by location
CREATE INDEX IF NOT EXISTS idx_zone_boundaries_location_id ON zone_boundaries (location_id);

-- hour-of-day grouping for average-distance endpoint
CREATE INDEX IF NOT EXISTS idx_trips_pickup_hour ON trips (pickup_hour);

-- top dropoff zones grouping
CREATE INDEX IF NOT EXISTS idx_trips_dropoff_zone ON trips (dropoff_zone);
CREATE INDEX IF NOT EXISTS idx_trips_dropoff_zone_summary
ON trips (do_location_id, dropoff_zone, dropoff_borough);

-- fare distribution range scans with revenue aggregation
CREATE INDEX IF NOT EXISTS idx_trips_fare_distribution
ON trips (fare_amount, total_amount);

-- average-fare endpoint groups by borough + payment_type
CREATE INDEX IF NOT EXISTS idx_trips_borough_payment ON trips (pickup_borough, payment_type);

-- trip ordering and revenue-trend grouping
CREATE INDEX IF NOT EXISTS idx_trips_pickup_date ON trips (SUBSTR(pickup_datetime, 1, 10));

-- Fast borough-first lookups when no pickup date is selected.
CREATE INDEX IF NOT EXISTS idx_dashboard_slices_borough_date
ON analytics_dashboard_slices (pickup_borough, pickup_date);
CREATE INDEX IF NOT EXISTS idx_dashboard_zones_borough_date
ON analytics_dashboard_pickup_zones (pickup_borough, pickup_date);
CREATE INDEX IF NOT EXISTS idx_dashboard_fares_borough_date
ON analytics_dashboard_fare_distribution (pickup_borough, pickup_date);
