import sys
from collections import defaultdict
from pathlib import Path
from time import perf_counter


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from etl.extract import ParquetLoader
from etl.transform.validator import DataValidator
from etl.transform.cleaner import TripCleaner
from etl.transform.outlier_detector import TripOutlierDetector
from etl.transform.zone_to_trip_merger import TripZoneMerger
from etl.transform.feature_engineer import TripFeatureEngineer
from etl.extract import LookupLoader
from etl.utils.config import TRIP_DATA_FILE, LOOKUP_FILE, CHUNK_SIZE
from backend.config.database import INDEXES_FILE, get_connection
from etl.load.analytics_accumulator import AnalyticsAccumulator
from etl.load.load_analytics import AGGREGATE_TABLES, refresh_analytics


def build_pipeline():
    """Load the lookup table and initialise all pipeline stages."""
    lookup_loader = LookupLoader(LOOKUP_FILE)
    lookup_data   = lookup_loader.load()
    return (
        lookup_data,
        DataValidator(),
        TripCleaner(),
        TripOutlierDetector(),
        TripZoneMerger(),
        TripFeatureEngineer(),
    )


def process_chunk(chunk, lookup_data, validator, cleaner, detector, merger, engineer):
    """Run one chunk through the full pipeline."""
    validated      = validator.validate_trip_data(chunk)
    cleaned        = cleaner.clean_trip_data(validated.data)
    outlier_result = detector.flag_trip_outliers(cleaned.data)
    merged         = merger.append_zone_info(outlier_result.data, lookup_data)
    featured       = engineer.add_trip_features(merged.data)
    return featured.data, cleaned.removed_records


TRIP_COLUMNS = [
    "vendor_id", "pickup_datetime", "dropoff_datetime", "passenger_count",
    "trip_distance", "rate_code_id", "store_and_fwd_flag",
    "pu_location_id", "do_location_id", "payment_type",
    "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
    "improvement_surcharge", "total_amount", "congestion_surcharge", "airport_fee",
    "is_outlier", "outlier_reasons",
    "pickup_borough", "pickup_zone", "pickup_service_zone",
    "dropoff_borough", "dropoff_zone", "dropoff_service_zone",
    "trip_duration_minutes", "average_speed_mph", "fare_per_mile",
    "pickup_hour", "pickup_day_of_week", "tip_percentage",
]

SUSPICIOUS_COLUMNS = [
    "vendor_id", "pickup_datetime", "dropoff_datetime", "passenger_count",
    "trip_distance", "rate_code_id", "store_and_fwd_flag",
    "pu_location_id", "do_location_id", "payment_type",
    "fare_amount", "extra", "mta_tax", "tip_amount", "tolls_amount",
    "improvement_surcharge", "total_amount", "congestion_surcharge", "airport_fee",
    "removal_reason",
]

RENAME_MAP = {
    "VendorID":              "vendor_id",
    "tpep_pickup_datetime":  "pickup_datetime",
    "tpep_dropoff_datetime": "dropoff_datetime",
    "RatecodeID":            "rate_code_id",
    "PULocationID":          "pu_location_id",
    "DOLocationID":          "do_location_id",
}

DATETIME_COLUMNS = ["pickup_datetime", "dropoff_datetime"]


def sanitize(df, columns):
    """
    Prepare a dataframe for SQLite insertion:
    - Rename raw ETL columns to db column names
    - Ensure all expected columns exist
    - Convert every value to a Python-native type SQLite can accept
    """
    prepared = df.rename(columns=RENAME_MAP).reindex(columns=columns).copy()

    for column in DATETIME_COLUMNS:
        values = pd.to_datetime(prepared[column], errors="coerce")
        prepared[column] = values.dt.strftime("%Y-%m-%dT%H:%M:%S")

    prepared = prepared.astype(object).where(prepared.notna(), None)
    return list(prepared.itertuples(index=False, name=None))


def insert_trips(cursor, trips_df):
    rows = sanitize(trips_df, TRIP_COLUMNS)
    placeholders = ", ".join(["?"] * len(TRIP_COLUMNS))
    sql = f"INSERT INTO trips ({', '.join(TRIP_COLUMNS)}) VALUES ({placeholders})"
    cursor.executemany(sql, rows)


def insert_suspicious(cursor, suspicious_df):
    if suspicious_df.empty:
        return
    rows = sanitize(suspicious_df, SUSPICIOUS_COLUMNS)
    placeholders = ", ".join(["?"] * len(SUSPICIOUS_COLUMNS))
    sql = f"INSERT INTO suspicious_records ({', '.join(SUSPICIOUS_COLUMNS)}) VALUES ({placeholders})"
    cursor.executemany(sql, rows)


def drop_trip_indexes(connection):
    """Defer trip indexes until after the bulk insert."""
    names = [
        row[0]
        for row in connection.execute("""
            SELECT name FROM sqlite_master
            WHERE type = 'index' AND name LIKE 'idx_trips_%'
        """).fetchall()
    ]
    for name in names:
        safe_name = name.replace('"', '""')
        connection.execute(f'DROP INDEX IF EXISTS "{safe_name}"')
    return len(names)


def rebuild_indexes(connection):
    """Create deferred indexes and collect query-planner statistics."""
    connection.executescript(INDEXES_FILE.read_text())
    connection.execute("ANALYZE")


def _load_trips_legacy():
    """Run the full ETL pipeline and load trips into the database chunk by chunk."""
    print("Initialising pipeline...")
    lookup_data, validator, cleaner, detector, merger, engineer = build_pipeline()

    loader       = ParquetLoader(TRIP_DATA_FILE, chunk_size=CHUNK_SIZE)
    total_rows   = loader.get_row_count()
    total_chunks = (total_rows + CHUNK_SIZE - 1) // CHUNK_SIZE
    print(f"Processing {total_rows:,} rows in {total_chunks} chunks of {CHUNK_SIZE:,}...")

    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trips")
    cursor.execute("DELETE FROM suspicious_records")

    trips_inserted      = 0
    suspicious_inserted = 0
    chunk_num           = 0

    for chunk in loader.load_chunks():
        chunk_num += 1
        trips_df, suspicious_df = process_chunk(
            chunk, lookup_data, validator, cleaner, detector, merger, engineer
        )

        insert_trips(cursor, trips_df)
        insert_suspicious(cursor, suspicious_df)

        trips_inserted      += len(trips_df)
        suspicious_inserted += len(suspicious_df)

        if chunk_num % 10 == 0 or chunk_num == total_chunks:
            conn.commit()
            print(
                f"  Chunk {chunk_num}/{total_chunks} — "
                f"trips: {trips_inserted:,} | "
                f"suspicious: {suspicious_inserted:,}",
                flush=True
            )

    conn.commit()
    print("Building analytics aggregate tables...", flush=True)
    refresh_analytics(conn)
    conn.close()

    print(f"\nDone.")
    print(f"  Trips loaded       : {trips_inserted:,}")
    print(f"  Suspicious records : {suspicious_inserted:,}")


def load_trips():
    """Run the optimized chunked ETL and bulk database load."""
    print("Initialising pipeline...")
    lookup_data, validator, cleaner, detector, merger, engineer = build_pipeline()

    loader = ParquetLoader(TRIP_DATA_FILE, chunk_size=CHUNK_SIZE)
    total_rows = loader.get_row_count()
    total_chunks = (total_rows + CHUNK_SIZE - 1) // CHUNK_SIZE
    print(f"Processing {total_rows:,} rows in {total_chunks} chunks of {CHUNK_SIZE:,}...")

    conn = get_connection()
    cursor = conn.cursor()
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA wal_autocheckpoint = 10000")

    setup_started = perf_counter()
    dropped_indexes = drop_trip_indexes(conn)
    cursor.execute("DELETE FROM trips")
    cursor.execute("DELETE FROM suspicious_records")
    conn.commit()
    print(
        f"Prepared empty trip tables and deferred {dropped_indexes} indexes "
        f"in {perf_counter() - setup_started:.1f}s.",
        flush=True,
    )

    trips_inserted = 0
    suspicious_inserted = 0
    analytics = AnalyticsAccumulator()
    stage_seconds = defaultdict(float)
    load_started = perf_counter()

    try:
        chunks = iter(loader.load_chunks())
        for chunk_num in range(1, total_chunks + 1):
            stage_started = perf_counter()
            chunk = next(chunks)
            stage_seconds["extract"] += perf_counter() - stage_started
            chunk_started = perf_counter()

            stage_started = perf_counter()
            trips_df, suspicious_df = process_chunk(
                chunk, lookup_data, validator, cleaner, detector, merger, engineer
            )
            stage_seconds["transform"] += perf_counter() - stage_started

            stage_started = perf_counter()
            analytics.add_chunk(trips_df)
            stage_seconds["analytics"] += perf_counter() - stage_started

            stage_started = perf_counter()
            insert_trips(cursor, trips_df)
            insert_suspicious(cursor, suspicious_df)
            stage_seconds["prepare_and_insert"] += perf_counter() - stage_started

            trips_inserted += len(trips_df)
            suspicious_inserted += len(suspicious_df)

            if chunk_num % 10 == 0 or chunk_num == total_chunks:
                conn.commit()

            print(
                f"  Chunk {chunk_num}/{total_chunks} | "
                f"{perf_counter() - chunk_started:.1f}s | "
                f"trips: {trips_inserted:,} | suspicious: {suspicious_inserted:,}",
                flush=True,
            )

        conn.commit()

        stage_started = perf_counter()
        print("Writing incrementally accumulated analytics...", flush=True)
        analytics.write(conn, AGGREGATE_TABLES)
        conn.commit()
        stage_seconds["analytics_write"] = perf_counter() - stage_started

        stage_started = perf_counter()
        print("Building deferred indexes and planner statistics...", flush=True)
        rebuild_indexes(conn)
        conn.commit()
        stage_seconds["index_build"] = perf_counter() - stage_started
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("\nDone.")
    print(f"  Trips loaded       : {trips_inserted:,}")
    print(f"  Suspicious records : {suspicious_inserted:,}")
    print(f"  Total load time     : {perf_counter() - load_started:.1f}s")
    print("  Stage timings:")
    for stage, seconds in stage_seconds.items():
        print(f"    {stage:<20}: {seconds:.1f}s")


if __name__ == "__main__":
    load_trips()
