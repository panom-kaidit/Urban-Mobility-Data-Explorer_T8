-- run AFTER data has been loaded into trips and zone_boundaries

-- revenue trend queries grouped by date
CREATE INDEX idx_trips_pickup_datetime ON trips (pickup_datetime);

-- joins / filtering by pickup and dropoff zone
CREATE INDEX idx_trips_pu_location_id ON trips (pu_location_id);
CREATE INDEX idx_trips_do_location_id ON trips (do_location_id);

-- revenue-by-borough grouping (no JOIN needed, columns are denormalized)
CREATE INDEX idx_trips_pickup_borough ON trips (pickup_borough);
CREATE INDEX idx_trips_dropoff_borough ON trips (dropoff_borough);

-- filtering outlier vs non-outlier trips
CREATE INDEX idx_trips_is_outlier ON trips (is_outlier);

-- filtering by payment type
CREATE INDEX idx_trips_payment_type ON trips (payment_type);

-- fare-based filtering and fare distribution queries
CREATE INDEX idx_trips_fare_amount ON trips (fare_amount);

-- zone boundary lookups by location
CREATE INDEX idx_zone_boundaries_location_id ON zone_boundaries (location_id);