from time import perf_counter

import pandas as pd

from backend.config.database import INDEXES_FILE, get_connection
from etl.load.analytics_accumulator import AnalyticsAccumulator


AGGREGATE_TABLES = (
    "analytics_summary",
    "analytics_pickup_zones",
    "analytics_zone_revenue",
    "analytics_dropoff_zones",
    "analytics_fare_distribution",
    "analytics_borough_revenue",
    "analytics_daily_revenue",
    "analytics_average_fare",
    "analytics_hourly_distance",
    "analytics_dashboard_slices",
    "analytics_dashboard_pickup_zones",
    "analytics_dashboard_fare_distribution",
)


def _refresh_analytics_with_sql_scans(connection=None) -> None:
    """Legacy multi-scan implementation retained for output comparison tests."""
    owns_connection = connection is None
    conn = connection or get_connection()

    try:
        for table in AGGREGATE_TABLES:
            conn.execute(f"DELETE FROM {table}")

        conn.execute("""
            INSERT INTO analytics_summary
            SELECT
                1,
                COUNT(*),
                COALESCE(ROUND(SUM(total_amount), 2), 0.0),
                COALESCE(ROUND(AVG(fare_amount), 2), 0.0),
                COALESCE(ROUND(AVG(trip_distance), 2), 0.0),
                MIN(SUBSTR(pickup_datetime, 1, 10)),
                MAX(SUBSTR(pickup_datetime, 1, 10)),
                COALESCE(SUM(CASE WHEN is_outlier = 1 THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE
                    WHEN SUBSTR(pickup_datetime, 1, 10) < '2019-01-01'
                      OR SUBSTR(pickup_datetime, 1, 10) > '2019-01-31'
                    THEN 1 ELSE 0 END), 0),
                (SELECT COUNT(*) FROM suspicious_records),
                (SELECT COUNT(*) FROM locations),
                (SELECT COUNT(*) FROM zone_boundaries)
            FROM trips
        """)

        conn.execute("""
            INSERT INTO analytics_pickup_zones
            SELECT pu_location_id, MIN(pickup_zone), MIN(pickup_borough), COUNT(*)
            FROM trips
            WHERE pu_location_id IS NOT NULL
            GROUP BY pu_location_id
        """)

        conn.execute("""
            INSERT INTO analytics_zone_revenue
            SELECT pu_location_id, COUNT(*), ROUND(SUM(total_amount), 2)
            FROM trips
            WHERE pu_location_id IS NOT NULL
            GROUP BY pu_location_id
        """)

        conn.execute("""
            INSERT INTO analytics_dropoff_zones
            SELECT do_location_id, MIN(dropoff_zone), MIN(dropoff_borough), COUNT(*)
            FROM trips
            WHERE dropoff_zone IS NOT NULL
            GROUP BY do_location_id
        """)

        conn.execute("""
            INSERT INTO analytics_fare_distribution
            SELECT
                CASE
                    WHEN fare_amount < 10 THEN 1
                    WHEN fare_amount < 20 THEN 2
                    WHEN fare_amount < 30 THEN 3
                    WHEN fare_amount < 40 THEN 4
                    WHEN fare_amount < 50 THEN 5
                    ELSE 6
                END,
                CASE
                    WHEN fare_amount < 10 THEN '0-10'
                    WHEN fare_amount < 20 THEN '10-20'
                    WHEN fare_amount < 30 THEN '20-30'
                    WHEN fare_amount < 40 THEN '30-40'
                    WHEN fare_amount < 50 THEN '40-50'
                    ELSE '50+'
                END,
                COUNT(*), ROUND(AVG(fare_amount), 2), ROUND(SUM(total_amount), 2)
            FROM trips
            WHERE fare_amount > 0
            GROUP BY 1, 2
        """)

        conn.execute("""
            INSERT INTO analytics_borough_revenue
            SELECT pickup_borough, COUNT(*), ROUND(SUM(total_amount), 2),
                   ROUND(AVG(total_amount), 2)
            FROM trips
            WHERE pickup_borough IS NOT NULL AND pickup_borough != 'Unknown'
            GROUP BY pickup_borough
        """)

        conn.execute("""
            INSERT INTO analytics_daily_revenue
            SELECT SUBSTR(pickup_datetime, 1, 10), COUNT(*),
                   ROUND(SUM(total_amount), 2), ROUND(AVG(total_amount), 2)
            FROM trips
            WHERE pickup_datetime IS NOT NULL
            GROUP BY SUBSTR(pickup_datetime, 1, 10)
        """)

        conn.execute("""
            INSERT INTO analytics_average_fare
            SELECT
                pickup_borough,
                COALESCE(payment_type, -1),
                CASE payment_type
                    WHEN 1 THEN 'Credit Card'
                    WHEN 2 THEN 'Cash'
                    WHEN 3 THEN 'No Charge'
                    WHEN 4 THEN 'Dispute'
                    ELSE 'Other'
                END,
                COUNT(*), ROUND(AVG(fare_amount), 2),
                ROUND(AVG(tip_amount), 2), ROUND(AVG(total_amount), 2)
            FROM trips
            WHERE pickup_borough IS NOT NULL
              AND pickup_borough != 'Unknown'
              AND fare_amount > 0
            GROUP BY pickup_borough, payment_type
        """)

        conn.execute("""
            INSERT INTO analytics_hourly_distance
            SELECT pickup_hour, COUNT(*), ROUND(AVG(trip_distance), 2),
                   ROUND(AVG(trip_duration_minutes), 1)
            FROM trips
            WHERE pickup_hour IS NOT NULL AND trip_distance > 0
            GROUP BY pickup_hour
        """)

        conn.execute("""
            INSERT INTO analytics_dashboard_slices
            SELECT
                SUBSTR(pickup_datetime, 1, 10),
                COALESCE(pickup_borough, 'Unknown'),
                COUNT(*),
                COALESCE(SUM(total_amount), 0.0),
                COALESCE(SUM(fare_amount), 0.0),
                COALESCE(SUM(trip_distance), 0.0),
                COALESCE(SUM(CASE WHEN is_outlier = 1 THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE
                    WHEN SUBSTR(pickup_datetime, 1, 10) < '2019-01-01'
                      OR SUBSTR(pickup_datetime, 1, 10) > '2019-01-31'
                    THEN 1 ELSE 0 END), 0)
            FROM trips
            GROUP BY SUBSTR(pickup_datetime, 1, 10),
                     COALESCE(pickup_borough, 'Unknown')
        """)

        conn.execute("""
            INSERT INTO analytics_dashboard_pickup_zones
            SELECT
                SUBSTR(pickup_datetime, 1, 10),
                COALESCE(pickup_borough, 'Unknown'),
                pu_location_id,
                MIN(pickup_zone),
                COUNT(*)
            FROM trips
            WHERE pu_location_id IS NOT NULL
            GROUP BY SUBSTR(pickup_datetime, 1, 10),
                     COALESCE(pickup_borough, 'Unknown'),
                     pu_location_id
        """)

        conn.execute("""
            INSERT INTO analytics_dashboard_fare_distribution
            SELECT
                SUBSTR(pickup_datetime, 1, 10),
                COALESCE(pickup_borough, 'Unknown'),
                CASE
                    WHEN fare_amount < 10 THEN 1
                    WHEN fare_amount < 20 THEN 2
                    WHEN fare_amount < 30 THEN 3
                    WHEN fare_amount < 40 THEN 4
                    WHEN fare_amount < 50 THEN 5
                    ELSE 6
                END,
                CASE
                    WHEN fare_amount < 10 THEN '0-10'
                    WHEN fare_amount < 20 THEN '10-20'
                    WHEN fare_amount < 30 THEN '20-30'
                    WHEN fare_amount < 40 THEN '30-40'
                    WHEN fare_amount < 50 THEN '40-50'
                    ELSE '50+'
                END,
                COUNT(*),
                COALESCE(SUM(fare_amount), 0.0),
                COALESCE(SUM(total_amount), 0.0)
            FROM trips
            WHERE fare_amount > 0
            GROUP BY SUBSTR(pickup_datetime, 1, 10),
                     COALESCE(pickup_borough, 'Unknown'),
                     3, 4
        """)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if owns_connection:
            conn.close()


ANALYTICS_SOURCE_COLUMNS = (
    "pickup_datetime", "pickup_borough", "pickup_zone",
    "dropoff_borough", "dropoff_zone", "pu_location_id", "do_location_id",
    "payment_type", "fare_amount", "tip_amount", "total_amount",
    "trip_distance", "trip_duration_minutes", "pickup_hour", "is_outlier",
)


def rebuild_query_indexes(connection) -> None:
    """Restore deferred query indexes after a load or recovery run."""
    connection.executescript(INDEXES_FILE.read_text())
    connection.execute("ANALYZE")


def refresh_analytics(
    connection=None,
    chunk_size: int = 100_000,
    rebuild_indexes: bool = True,
) -> None:
    """Rebuild analytics with one streamed scan instead of eleven SQL scans."""
    owns_connection = connection is None
    conn = connection or get_connection()
    accumulator = AnalyticsAccumulator()
    rows_seen = 0
    started = perf_counter()

    try:
        for chunk in pd.read_sql_query(
            f"SELECT {', '.join(ANALYTICS_SOURCE_COLUMNS)} FROM trips",
            conn,
            chunksize=chunk_size,
            parse_dates=["pickup_datetime"],
        ):
            accumulator.add_chunk(chunk)
            rows_seen += len(chunk)
            print(f"  Analytics scan: {rows_seen:,} rows", flush=True)

        accumulator.write(conn, AGGREGATE_TABLES)
        if rebuild_indexes:
            print("  Rebuilding deferred query indexes...", flush=True)
            rebuild_query_indexes(conn)
        conn.commit()
        print(
            f"Analytics refreshed in one pass ({perf_counter() - started:.1f}s).",
            flush=True,
        )
    except Exception:
        conn.rollback()
        raise
    finally:
        if owns_connection:
            conn.close()


if __name__ == "__main__":
    refresh_analytics()
    print("Analytics aggregate tables refreshed.")
