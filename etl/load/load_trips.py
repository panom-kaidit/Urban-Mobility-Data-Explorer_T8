import sys
from etl.extract import ParquetLoader
from etl.transform.validator import DataValidator
from etl.transform.cleaner import TripCleaner
from etl.transform.outlier_detector import TripOutlierDetector
from etl.transform.zone_to_trip_merger import TripZoneMerger
from etl.transform.feature_engineer import TripFeatureEngineer
from etl.extract import LookupLoader
from etl.utils.config import TRIP_DATA_FILE, LOOKUP_FILE, CHUNK_SIZE
from backend.config.database import get_connection


def build_pipeline():
    """Load the lookup table and initialise all pipeline stages."""
    lookup_loader = LookupLoader(LOOKUP_FILE)
    lookup_data = lookup_loader.load()

    validator   = DataValidator()
    cleaner     = TripCleaner()
    detector    = TripOutlierDetector()
    merger      = TripZoneMerger()
    engineer    = TripFeatureEngineer()

    return lookup_data, validator, cleaner, detector, merger, engineer


def process_chunk(chunk, lookup_data, validator, cleaner, detector, merger, engineer):
    """
    Run one chunk of raw trip data through the full pipeline.

    Returns:
        cleaned_trips      — DataFrame ready to insert into trips table
        suspicious_records — DataFrame ready to insert into suspicious_records table
    """
    validated       = validator.validate_trip_data(chunk)
    cleaned         = cleaner.clean_trip_data(validated.data)
    outlier_result  = detector.flag_trip_outliers(cleaned.data)
    merged          = merger.append_zone_info(outlier_result.data, lookup_data)
    featured        = engineer.add_trip_features(merged.data)

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

# maps raw ETL column names to database column names
RENAME_MAP = {
    "VendorID":              "vendor_id",
    "tpep_pickup_datetime":  "pickup_datetime",
    "tpep_dropoff_datetime": "dropoff_datetime",
    "RatecodeID":            "rate_code_id",
    "PULocationID":          "pu_location_id",
    "DOLocationID":          "do_location_id",
}


def insert_trips(cursor, trips_df):
    """Rename columns and insert a batch of cleaned trips into the trips table."""
    df = trips_df.rename(columns=RENAME_MAP)

    # make sure all expected columns exist, fill missing ones with None
    for col in TRIP_COLUMNS:
        if col not in df.columns:
            df[col] = None

    placeholders = ", ".join(["?"] * len(TRIP_COLUMNS))
    sql = f"INSERT INTO trips ({', '.join(TRIP_COLUMNS)}) VALUES ({placeholders})"

    rows = [
        tuple(None if hasattr(v, '__class__') and v.__class__.__name__ in ('NAType', 'float') and str(v) in ('nan', '<NA>') else v for v in row)
        for row in df[TRIP_COLUMNS].itertuples(index=False, name=None)
    ]
    cursor.executemany(sql, rows)


def insert_suspicious(cursor, suspicious_df):
    """Rename columns and insert removed records into the suspicious_records table."""
    if suspicious_df.empty:
        return

    df = suspicious_df.rename(columns={**RENAME_MAP, "removal_reason": "removal_reason"})

    for col in SUSPICIOUS_COLUMNS:
        if col not in df.columns:
            df[col] = None

    placeholders = ", ".join(["?"] * len(SUSPICIOUS_COLUMNS))
    sql = f"INSERT INTO suspicious_records ({', '.join(SUSPICIOUS_COLUMNS)}) VALUES ({placeholders})"

    rows = [
        tuple(None if str(v) in ('nan', '<NA>', 'NaT') else v for v in row)
        for row in df[SUSPICIOUS_COLUMNS].itertuples(index=False, name=None)
    ]
    cursor.executemany(sql, rows)


def load_trips():
    """Run the full ETL pipeline and load trips into the database chunk by chunk."""
    print("Initialising pipeline...")
    lookup_data, validator, cleaner, detector, merger, engineer = build_pipeline()

    loader = ParquetLoader(TRIP_DATA_FILE, chunk_size=CHUNK_SIZE)
    total_rows   = loader.get_row_count()
    total_chunks = (total_rows // CHUNK_SIZE) + 1
    print(f"Processing {total_rows:,} rows in ~{total_chunks} chunks of {CHUNK_SIZE:,}...")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trips")
    cursor.execute("DELETE FROM suspicious_records")

    trips_inserted     = 0
    suspicious_inserted = 0
    chunk_num          = 0

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
    conn.close()

    print(f"\nDone.")
    print(f"  Trips loaded       : {trips_inserted:,}")
    print(f"  Suspicious records : {suspicious_inserted:,}")


if __name__ == "__main__":
    load_trips()