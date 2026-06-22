from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

RAW_DATA_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DATA_DIR = BASE_DIR / "data" / "processed"
LOG_DIR = BASE_DIR / "data" / "logs"

LOOKUP_FILE = RAW_DATA_DIR / "taxi_zone_lookup.csv"
SPATIAL_FILE = RAW_DATA_DIR / "spatial_metadata" / "taxi_zones.shp"
TRIP_DATA_FILE = RAW_DATA_DIR / "yellow_tripdata_2019-01.parquet"

# Larger chunks reduce repeated pandas copies/groupbys and SQLite tuple
# preparation while keeping peak memory reasonable on development machines.
CHUNK_SIZE = 100_000
