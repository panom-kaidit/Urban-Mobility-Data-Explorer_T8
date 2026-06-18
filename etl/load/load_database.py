import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from backend.config.database import DB_PATH, get_connection, init_db
from etl.load.load_locations import load_locations
from etl.load.load_trips import load_trips
from etl.load.load_zone_boundaries import load_zone_boundaries
from etl.utils.config import LOOKUP_FILE, SPATIAL_FILE, TRIP_DATA_FILE


TABLE_NAMES = [
    "locations",
    "zone_boundaries",
    "trips",
    "suspicious_records",
    "zone_metrics",
    "fare_distribution_metrics",
]


def get_table_counts():
    conn = get_connection()
    counts = {}

    try:
        for table_name in TABLE_NAMES:
            row = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
            counts[table_name] = row[0]
    finally:
        conn.close()

    return counts


def print_table_counts():
    print("Current table counts:")
    counts = get_table_counts()

    for table_name in TABLE_NAMES:
        print(f"  {table_name}: {counts[table_name]:,}")


def clear_tables(table_names):
    conn = get_connection()

    try:
        cursor = conn.cursor()
        for table_name in table_names:
            cursor.execute(f"DELETE FROM {table_name}")
        conn.commit()
    finally:
        conn.close()


def build_zone_metrics():
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM zone_metrics")
        cursor.execute(
            """
            INSERT INTO zone_metrics (
                location_id,
                trip_count,
                total_revenue,
                avg_fare,
                avg_distance
            )
            SELECT
                pu_location_id,
                COUNT(*) AS trip_count,
                ROUND(SUM(total_amount), 2) AS total_revenue,
                ROUND(AVG(total_amount), 2) AS avg_fare,
                ROUND(AVG(trip_distance), 2) AS avg_distance
            FROM trips
            GROUP BY pu_location_id
            """
        )
        conn.commit()
    finally:
        conn.close()


def build_fare_distribution_metrics():
    conn = get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fare_distribution_metrics")
        cursor.execute(
            """
            INSERT INTO fare_distribution_metrics (
                fare_range,
                sort_order,
                trip_count,
                avg_fare,
                total_revenue
            )
            SELECT
                CASE
                    WHEN fare_amount >= 0  AND fare_amount < 10  THEN '0-10'
                    WHEN fare_amount >= 10 AND fare_amount < 20  THEN '10-20'
                    WHEN fare_amount >= 20 AND fare_amount < 30  THEN '20-30'
                    WHEN fare_amount >= 30 AND fare_amount < 40  THEN '30-40'
                    WHEN fare_amount >= 40 AND fare_amount < 50  THEN '40-50'
                    ELSE '50+'
                END AS fare_range,
                CASE
                    WHEN fare_amount >= 0  AND fare_amount < 10  THEN 1
                    WHEN fare_amount >= 10 AND fare_amount < 20  THEN 2
                    WHEN fare_amount >= 20 AND fare_amount < 30  THEN 3
                    WHEN fare_amount >= 30 AND fare_amount < 40  THEN 4
                    WHEN fare_amount >= 40 AND fare_amount < 50  THEN 5
                    ELSE 6
                END AS sort_order,
                COUNT(*) AS trip_count,
                ROUND(AVG(fare_amount), 2) AS avg_fare,
                ROUND(SUM(total_amount), 2) AS total_revenue
            FROM trips
            WHERE fare_amount > 0
            GROUP BY fare_range, sort_order
            """
        )
        conn.commit()
    finally:
        conn.close()


def check_input_files(load_dimensions, load_trips_data):
    missing_files = []

    if load_dimensions:
        if not LOOKUP_FILE.exists():
            missing_files.append(f"taxi zone lookup CSV: {LOOKUP_FILE}")
        if not SPATIAL_FILE.exists():
            missing_files.append(f"taxi zone shapefile: {SPATIAL_FILE}")

    if load_trips_data and not TRIP_DATA_FILE.exists():
        missing_files.append(f"yellow taxi trip parquet: {TRIP_DATA_FILE}")

    if missing_files:
        message = "Missing required input file(s):\n- " + "\n- ".join(missing_files)
        raise FileNotFoundError(message)


def load_database(reset=True, load_dimensions=True, load_trips_data=True):
    print(f"Using database: {DB_PATH}")
    init_db()

    # Check first so we do not clear the database and then fail on a missing file.
    check_input_files(load_dimensions, load_trips_data)

    if reset and load_dimensions:
        print("Clearing all ETL tables...")
        clear_tables([
            "zone_metrics",
            "fare_distribution_metrics",
            "suspicious_records",
            "trips",
            "zone_boundaries",
            "locations",
        ])
    elif reset and load_trips_data:
        print("Clearing trip tables...")
        clear_tables([
            "zone_metrics",
            "fare_distribution_metrics",
            "suspicious_records",
            "trips",
        ])

    if load_dimensions:
        print("Loading locations...")
        load_locations()

        print("Loading zone boundaries...")
        load_zone_boundaries()

    if load_trips_data:
        counts = get_table_counts()
        if counts["locations"] == 0:
            raise RuntimeError("Trips cannot be loaded until locations are loaded.")

        print("Loading trips and suspicious records...")
        load_trips(clear_existing=False)

        print("Building zone metrics for dashboard...")
        build_zone_metrics()

        print("Building fare distribution for dashboard...")
        build_fare_distribution_metrics()

    print_table_counts()


def parse_args():
    parser = argparse.ArgumentParser(description="Load ETL data into mobility.db")
    parser.add_argument("--no-reset", action="store_true")
    parser.add_argument("--dimensions-only", action="store_true")
    parser.add_argument("--trips-only", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()

    if args.dimensions_only and args.trips_only:
        raise SystemExit("Use either --dimensions-only or --trips-only, not both.")

    try:
        load_database(
            reset=not args.no_reset,
            load_dimensions=not args.trips_only,
            load_trips_data=not args.dimensions_only,
        )
    except (FileNotFoundError, RuntimeError) as error:
        raise SystemExit(f"Load failed: {error}") from None


if __name__ == "__main__":
    main()
