import pandas as pd

from backend.config.database import get_connection
from etl.extract import LookupLoader, ParquetLoader
from etl.transform.cleaner import TripCleaner
from etl.transform.feature_engineer import TripFeatureEngineer
from etl.transform.outlier_detector import TripOutlierDetector
from etl.transform.validator import DataValidator
from etl.transform.zone_to_trip_merger import TripZoneMerger
from etl.utils.config import CHUNK_SIZE, LOOKUP_FILE, TRIP_DATA_FILE


def build_pipeline():
    """Load the lookup table and initialise all pipeline stages."""
    lookup_loader = LookupLoader(LOOKUP_FILE)
    lookup_data = lookup_loader.load()
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
    validated = validator.validate_trip_data(chunk)
    cleaned = cleaner.clean_trip_data(validated.data)
    outlier_result = detector.flag_trip_outliers(cleaned.data)
    merged = merger.append_zone_info(outlier_result.data, lookup_data)
    featured = engineer.add_trip_features(merged.data)
    return featured.data, cleaned.removed_records


TRIP_COLUMNS = [
    "vendor_id",
    "pickup_datetime",
    "dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "rate_code_id",
    "store_and_fwd_flag",
    "pu_location_id",
    "do_location_id",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
    "airport_fee",
    "is_outlier",
    "outlier_reasons",
    "pickup_borough",
    "pickup_zone",
    "pickup_service_zone",
    "dropoff_borough",
    "dropoff_zone",
    "dropoff_service_zone",
    "trip_duration_minutes",
    "average_speed_mph",
    "fare_per_mile",
    "pickup_hour",
    "pickup_day_of_week",
    "tip_percentage",
]

SUSPICIOUS_COLUMNS = [
    "vendor_id",
    "pickup_datetime",
    "dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "rate_code_id",
    "store_and_fwd_flag",
    "pu_location_id",
    "do_location_id",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "improvement_surcharge",
    "total_amount",
    "congestion_surcharge",
    "airport_fee",
    "removal_reason",
]

RENAME_MAP = {
    "VendorID": "vendor_id",
    "tpep_pickup_datetime": "pickup_datetime",
    "tpep_dropoff_datetime": "dropoff_datetime",
    "RatecodeID": "rate_code_id",
    "PULocationID": "pu_location_id",
    "DOLocationID": "do_location_id",
}


def to_python(value):
    """Convert any value to a Python-native type SQLite can accept."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    return value


def sanitize(df, columns):
    """
    Prepare a dataframe for SQLite insertion:
    - Rename raw ETL columns to db column names.
    - Ensure all expected columns exist.
    - Convert every value to a Python-native type SQLite can accept.
    """
    df = df.rename(columns=RENAME_MAP).copy()

    for column in columns:
        if column not in df.columns:
            df[column] = None

    return [
        tuple(to_python(value) for value in row)
        for row in df[columns].itertuples(index=False, name=None)
    ]


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
    sql = (
        f"INSERT INTO suspicious_records ({', '.join(SUSPICIOUS_COLUMNS)}) "
        f"VALUES ({placeholders})"
    )
    cursor.executemany(sql, rows)


def load_trips(clear_existing=True):
    """Run the full ETL pipeline and load trips into the database chunk by chunk."""
    print("Initialising pipeline...")
    lookup_data, validator, cleaner, detector, merger, engineer = build_pipeline()

    loader = ParquetLoader(TRIP_DATA_FILE, chunk_size=CHUNK_SIZE)
    total_rows = loader.get_row_count()
    total_chunks = (total_rows + CHUNK_SIZE - 1) // CHUNK_SIZE
    print(f"Processing {total_rows:,} rows in {total_chunks:,} chunks of {CHUNK_SIZE:,}...")

    conn = get_connection()
    cursor = conn.cursor()

    if clear_existing:
        cursor.execute("DELETE FROM suspicious_records")
        cursor.execute("DELETE FROM trips")

    trips_inserted = 0
    suspicious_inserted = 0
    chunk_num = 0

    try:
        for chunk in loader.load_chunks():
            chunk_num += 1
            trips_df, suspicious_df = process_chunk(
                chunk, lookup_data, validator, cleaner, detector, merger, engineer
            )

            insert_trips(cursor, trips_df)
            insert_suspicious(cursor, suspicious_df)

            trips_inserted += len(trips_df)
            suspicious_inserted += len(suspicious_df)

            if chunk_num % 10 == 0 or chunk_num == total_chunks:
                conn.commit()
                print(
                    f"  Chunk {chunk_num}/{total_chunks} - "
                    f"trips: {trips_inserted:,} | "
                    f"suspicious: {suspicious_inserted:,}",
                    flush=True,
                )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print("\nDone.")
    print(f"  Trips loaded       : {trips_inserted:,}")
    print(f"  Suspicious records : {suspicious_inserted:,}")


if __name__ == "__main__":
    load_trips()
