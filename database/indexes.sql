-- run AFTER data has been loaded into trips and zone_boundaries

-- revenue trend queries grouped by date
CREATE INDEX IF NOT EXISTS idx_trips_pickup_datetime ON trips (pickup_datetime);

-- All dashboard analytics are read from compact precomputed tables. Additional
-- indexes on the 7.68M-row trips table would only slow bulk loading and index
-- creation; trip detail lookup uses its primary key and this ordering index.

-- Fast borough-first lookups when no pickup date is selected.
CREATE INDEX IF NOT EXISTS idx_dashboard_slices_borough_date
ON analytics_dashboard_slices (pickup_borough, pickup_date);
CREATE INDEX IF NOT EXISTS idx_dashboard_zones_borough_date
ON analytics_dashboard_pickup_zones (pickup_borough, pickup_date);
CREATE INDEX IF NOT EXISTS idx_dashboard_fares_borough_date
ON analytics_dashboard_fare_distribution (pickup_borough, pickup_date);
