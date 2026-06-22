"""Chunk-level analytics aggregation for the trip ETL."""

from __future__ import annotations

from collections import defaultdict

import pandas as pd


SOURCE_RENAME_MAP = {
    "tpep_pickup_datetime": "pickup_datetime",
    "PULocationID": "pu_location_id",
    "DOLocationID": "do_location_id",
}

FARE_LABELS = {1: "0-10", 2: "10-20", 3: "20-30", 4: "30-40", 5: "40-50", 6: "50+"}
PAYMENT_METHODS = {1: "Credit Card", 2: "Cash", 3: "No Charge", 4: "Dispute"}


def _python_value(value):
    """Convert one pandas/NumPy scalar into a SQLite-bindable value."""
    if value is None or pd.isna(value):
        return None
    if hasattr(value, "item"):
        value = value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _python_tuples(rows):
    """Yield SQLite-safe tuples from any iterable of scalar rows."""
    for row in rows:
        yield tuple(_python_value(value) for value in row)


def _python_tuple(row):
    """Return one SQLite-safe tuple."""
    return tuple(_python_value(value) for value in row)


def _python_rows(frame, columns=None):
    """Yield SQLite-safe rows from a finalized aggregate frame."""
    selected = frame if columns is None else frame.loc[:, columns]
    return _python_tuples(selected.itertuples(index=False, name=None))


def reconcile_zone_labels(connection):
    """Refresh aggregate display labels from the authoritative dimension."""
    connection.execute("""
        UPDATE analytics_pickup_zones
        SET zone_name = COALESCE(
                (SELECT zone FROM locations WHERE location_id = zone_id),
                zone_name
            ),
            borough = COALESCE(
                (SELECT borough FROM locations WHERE location_id = zone_id),
                borough
            )
    """)
    connection.execute("""
        UPDATE analytics_dropoff_zones
        SET zone_name = COALESCE(
                (SELECT zone FROM locations WHERE location_id = zone_id),
                zone_name
            ),
            borough = COALESCE(
                (SELECT borough FROM locations WHERE location_id = zone_id),
                borough
            )
    """)
    connection.execute("""
        UPDATE analytics_dashboard_pickup_zones
        SET zone_name = COALESCE(
            (SELECT zone FROM locations WHERE location_id = zone_id),
            zone_name
        )
    """)


class AnalyticsAccumulator:
    """Accumulate compact grouped frames from each transformed trip chunk."""

    def __init__(self) -> None:
        self.parts = defaultdict(list)

    def add_chunk(self, trips: pd.DataFrame) -> None:
        if trips.empty:
            return

        data = trips.rename(columns=SOURCE_RENAME_MAP)
        pickup_datetime = pd.to_datetime(data["pickup_datetime"], errors="coerce")
        pickup_borough = data["pickup_borough"].astype("string")
        work = pd.DataFrame({
            "pickup_date": pickup_datetime.dt.strftime("%Y-%m-%d"),
            "pickup_borough": pickup_borough,
            "dashboard_borough": pickup_borough.fillna("Unknown"),
            "pickup_zone": data["pickup_zone"],
            "dropoff_borough": data["dropoff_borough"],
            "dropoff_zone": data["dropoff_zone"],
            "pu_location_id": data["pu_location_id"],
            "do_location_id": data["do_location_id"],
            "payment_type": data["payment_type"],
            "fare_amount": data["fare_amount"],
            "tip_amount": data["tip_amount"],
            "total_amount": data["total_amount"],
            "trip_distance": data["trip_distance"],
            "trip_duration_minutes": data["trip_duration_minutes"],
            "pickup_hour": data["pickup_hour"],
            "is_outlier": data["is_outlier"].astype("int64"),
        })

        self.parts["summary"].append(pd.DataFrame([{
            "total_trips": len(work),
            "total_revenue": work["total_amount"].sum(),
            "total_fare": work["fare_amount"].sum(),
            "total_distance": work["trip_distance"].sum(),
            "start_date": work["pickup_date"].min(),
            "end_date": work["pickup_date"].max(),
            "outlier_count": work["is_outlier"].sum(),
            "outside_january_count": (
                (work["pickup_date"] < "2019-01-01")
                | (work["pickup_date"] > "2019-01-31")
            ).sum(),
        }]))

        pickup = work[work["pu_location_id"].notna()]
        self.parts["pickup_zones"].append(
            pickup.groupby("pu_location_id", as_index=False, sort=False).agg(
                zone_name=("pickup_zone", "min"),
                borough=("pickup_borough", "min"),
                trip_count=("pu_location_id", "size"),
                total_revenue=("total_amount", "sum"),
            )
        )

        dropoff = work[work["dropoff_zone"].notna() & work["do_location_id"].notna()]
        self.parts["dropoff_zones"].append(
            dropoff.groupby("do_location_id", as_index=False, sort=False).agg(
                zone_name=("dropoff_zone", "min"),
                borough=("dropoff_borough", "min"),
                trip_count=("do_location_id", "size"),
            )
        )

        fare = work[work["fare_amount"] > 0].copy()
        fare["bucket_order"] = pd.cut(
            fare["fare_amount"].astype(float),
            [0, 10, 20, 30, 40, 50, float("inf")],
            labels=[1, 2, 3, 4, 5, 6],
            right=False,
        ).astype("int64")
        self.parts["fare_distribution"].append(
            fare.groupby("bucket_order", as_index=False, sort=False).agg(
                trip_count=("fare_amount", "size"),
                fare_total=("fare_amount", "sum"),
                total_revenue=("total_amount", "sum"),
            )
        )

        borough = work[
            work["pickup_borough"].notna() & (work["pickup_borough"] != "Unknown")
        ]
        self.parts["borough_revenue"].append(
            borough.groupby("pickup_borough", as_index=False, sort=False).agg(
                total_trips=("total_amount", "size"),
                total_revenue=("total_amount", "sum"),
            )
        )

        self.parts["daily_revenue"].append(
            work.groupby("pickup_date", as_index=False, sort=False).agg(
                total_trips=("total_amount", "size"),
                total_revenue=("total_amount", "sum"),
            )
        )

        average_fare = fare.copy()
        average_fare["payment_type"] = average_fare["payment_type"].fillna(-1).astype("int64")
        self.parts["average_fare"].append(
            average_fare[average_fare["pickup_borough"] != "Unknown"].groupby(
                ["pickup_borough", "payment_type"], as_index=False, sort=False
            ).agg(
                total_trips=("fare_amount", "size"),
                fare_sum=("fare_amount", "sum"), fare_count=("fare_amount", "count"),
                tip_sum=("tip_amount", "sum"), tip_count=("tip_amount", "count"),
                total_sum=("total_amount", "sum"), total_count=("total_amount", "count"),
            )
        )

        hourly = work[work["pickup_hour"].notna() & (work["trip_distance"] > 0)]
        self.parts["hourly_distance"].append(
            hourly.groupby("pickup_hour", as_index=False, sort=False).agg(
                trip_count=("trip_distance", "size"),
                distance_sum=("trip_distance", "sum"),
                distance_count=("trip_distance", "count"),
                duration_sum=("trip_duration_minutes", "sum"),
                duration_count=("trip_duration_minutes", "count"),
            )
        )

        self.parts["dashboard_slices"].append(
            work.groupby(["pickup_date", "dashboard_borough"], as_index=False, sort=False).agg(
                total_trips=("total_amount", "size"),
                total_revenue=("total_amount", "sum"),
                total_fare=("fare_amount", "sum"),
                total_distance=("trip_distance", "sum"),
                outlier_count=("is_outlier", "sum"),
            )
        )

        self.parts["dashboard_zones"].append(
            pickup.groupby(
                ["pickup_date", "dashboard_borough", "pu_location_id"],
                as_index=False, sort=False,
            ).agg(zone_name=("pickup_zone", "min"), trip_count=("pu_location_id", "size"))
        )

        self.parts["dashboard_fares"].append(
            fare.groupby(
                ["pickup_date", "dashboard_borough", "bucket_order"],
                as_index=False, sort=False,
            ).agg(
                trip_count=("fare_amount", "size"),
                fare_total=("fare_amount", "sum"),
                total_revenue=("total_amount", "sum"),
            )
        )

    def _combine(self, name, keys, aggregations):
        combined = pd.concat(self.parts[name], ignore_index=True)
        return combined.groupby(keys, as_index=False, sort=False).agg(**aggregations)

    def write(self, connection, aggregate_tables) -> None:
        """Finalize partial frames and replace the database analytics tables."""
        if not self.parts["summary"]:
            raise ValueError("Cannot write analytics: the trip source contained no rows.")

        for table in aggregate_tables:
            connection.execute(f"DELETE FROM {table}")

        summary = pd.concat(self.parts["summary"], ignore_index=True)
        total_trips = int(summary["total_trips"].sum())
        connection.execute(
            """INSERT INTO analytics_summary (
                singleton_id, total_trips, total_revenue, average_fare,
                average_distance, start_date, end_date, outlier_count,
                outside_january_count, suspicious_records, location_count,
                zone_boundary_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            _python_tuple((
                1, total_trips, round(float(summary["total_revenue"].sum()), 2),
                round(float(summary["total_fare"].sum()) / total_trips, 2) if total_trips else 0,
                round(float(summary["total_distance"].sum()) / total_trips, 2) if total_trips else 0,
                summary["start_date"].min(), summary["end_date"].max(),
                int(summary["outlier_count"].sum()),
                int(summary["outside_january_count"].sum()),
                connection.execute("SELECT COUNT(*) FROM suspicious_records").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM locations").fetchone()[0],
                connection.execute("SELECT COUNT(*) FROM zone_boundaries").fetchone()[0],
            )),
        )

        pickup = self._combine("pickup_zones", ["pu_location_id"], {
            "zone_name": ("zone_name", "min"), "borough": ("borough", "min"),
            "trip_count": ("trip_count", "sum"),
            "total_revenue": ("total_revenue", "sum"),
        })
        connection.executemany(
            """INSERT INTO analytics_pickup_zones
                (zone_id, zone_name, borough, trip_count)
                VALUES (?, ?, ?, ?)""",
            _python_rows(
                pickup,
                ["pu_location_id", "zone_name", "borough", "trip_count"],
            ),
        )
        connection.executemany(
            """INSERT INTO analytics_zone_revenue
                (zone_id, trip_count, total_revenue) VALUES (?, ?, ?)""",
            _python_tuples(
                (int(r.pu_location_id), int(r.trip_count), round(float(r.total_revenue), 2))
                for r in pickup.itertuples(index=False)
            ),
        )
        dropoff = self._combine("dropoff_zones", ["do_location_id"], {
            "zone_name": ("zone_name", "min"), "borough": ("borough", "min"),
            "trip_count": ("trip_count", "sum"),
        })
        connection.executemany(
            """INSERT INTO analytics_dropoff_zones
                (zone_id, zone_name, borough, trip_count) VALUES (?, ?, ?, ?)""",
            _python_rows(dropoff),
        )

        fares = self._combine("fare_distribution", ["bucket_order"], {
            "trip_count": ("trip_count", "sum"), "fare_total": ("fare_total", "sum"),
            "total_revenue": ("total_revenue", "sum"),
        })
        connection.executemany(
            """INSERT INTO analytics_fare_distribution
                (bucket_order, range_label, trip_count, avg_fare, total_revenue)
                VALUES (?, ?, ?, ?, ?)""",
            _python_tuples(
                (int(r.bucket_order), FARE_LABELS[int(r.bucket_order)], int(r.trip_count),
                 round(float(r.fare_total) / int(r.trip_count), 2), round(float(r.total_revenue), 2))
                for r in fares.itertuples(index=False)
            ),
        )

        boroughs = self._combine("borough_revenue", ["pickup_borough"], {
            "total_trips": ("total_trips", "sum"), "total_revenue": ("total_revenue", "sum"),
        })
        connection.executemany(
            """INSERT INTO analytics_borough_revenue
                (borough, total_trips, total_revenue, avg_revenue_per_trip)
                VALUES (?, ?, ?, ?)""",
            _python_tuples(
                (r.pickup_borough, int(r.total_trips), round(float(r.total_revenue), 2),
                 round(float(r.total_revenue) / int(r.total_trips), 2))
                for r in boroughs.itertuples(index=False)
            ),
        )

        daily = self._combine("daily_revenue", ["pickup_date"], {
            "total_trips": ("total_trips", "sum"), "total_revenue": ("total_revenue", "sum"),
        })
        connection.executemany(
            """INSERT INTO analytics_daily_revenue
                (date, total_trips, total_revenue, avg_fare)
                VALUES (?, ?, ?, ?)""",
            _python_tuples(
                (r.pickup_date, int(r.total_trips), round(float(r.total_revenue), 2),
                 round(float(r.total_revenue) / int(r.total_trips), 2))
                for r in daily.itertuples(index=False)
            ),
        )

        averages = self._combine("average_fare", ["pickup_borough", "payment_type"], {
            name: (name, "sum") for name in (
                "total_trips", "fare_sum", "fare_count", "tip_sum", "tip_count", "total_sum", "total_count"
            )
        })
        connection.executemany(
            """INSERT INTO analytics_average_fare
                (borough, payment_type, payment_method, total_trips,
                 avg_fare, avg_tip, avg_total)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
            _python_tuples(
                (r.pickup_borough, int(r.payment_type), PAYMENT_METHODS.get(int(r.payment_type), "Other"),
                 int(r.total_trips), round(float(r.fare_sum) / int(r.fare_count), 2),
                 round(float(r.tip_sum) / int(r.tip_count), 2) if r.tip_count else None,
                 round(float(r.total_sum) / int(r.total_count), 2))
                for r in averages.itertuples(index=False)
            ),
        )

        hourly = self._combine("hourly_distance", ["pickup_hour"], {
            name: (name, "sum") for name in (
                "trip_count", "distance_sum", "distance_count", "duration_sum", "duration_count"
            )
        })
        connection.executemany(
            """INSERT INTO analytics_hourly_distance
                (hour, trip_count, avg_distance, avg_duration_minutes)
                VALUES (?, ?, ?, ?)""",
            _python_tuples(
                (int(r.pickup_hour), int(r.trip_count),
                 round(float(r.distance_sum) / int(r.distance_count), 2),
                 round(float(r.duration_sum) / int(r.duration_count), 1)
                 if r.duration_count else None)
                for r in hourly.itertuples(index=False)
            ),
        )

        slices = self._combine("dashboard_slices", ["pickup_date", "dashboard_borough"], {
            name: (name, "sum") for name in (
                "total_trips", "total_revenue", "total_fare", "total_distance", "outlier_count"
            )
        })
        connection.executemany(
            """INSERT INTO analytics_dashboard_slices
                (pickup_date, pickup_borough, total_trips, total_revenue,
                 total_fare, total_distance, outlier_count, outside_january_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            _python_tuples(
                (r.pickup_date, r.dashboard_borough, int(r.total_trips), float(r.total_revenue),
                 float(r.total_fare), float(r.total_distance), int(r.outlier_count),
                 int(r.total_trips)
                 if r.pickup_date < "2019-01-01" or r.pickup_date > "2019-01-31" else 0)
                for r in slices.itertuples(index=False)
            ),
        )

        zones = self._combine("dashboard_zones", ["pickup_date", "dashboard_borough", "pu_location_id"], {
            "zone_name": ("zone_name", "min"), "trip_count": ("trip_count", "sum"),
        })
        connection.executemany(
            """INSERT INTO analytics_dashboard_pickup_zones
                (pickup_date, pickup_borough, zone_id, zone_name, trip_count)
                VALUES (?, ?, ?, ?, ?)""",
            _python_rows(zones),
        )
        dashboard_fares = self._combine(
            "dashboard_fares", ["pickup_date", "dashboard_borough", "bucket_order"], {
                "trip_count": ("trip_count", "sum"), "fare_total": ("fare_total", "sum"),
                "total_revenue": ("total_revenue", "sum"),
            }
        )
        connection.executemany(
            """INSERT INTO analytics_dashboard_fare_distribution
                (pickup_date, pickup_borough, bucket_order, range_label,
                 trip_count, fare_total, total_revenue)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
            _python_tuples(
                (r.pickup_date, r.dashboard_borough, int(r.bucket_order),
                 FARE_LABELS[int(r.bucket_order)], int(r.trip_count),
                 float(r.fare_total), float(r.total_revenue))
                for r in dashboard_fares.itertuples(index=False)
            ),
        )

        # The locations dimension is authoritative for display labels. This
        # also repairs analytics-only recovery when an older trip load stored
        # a missing pandas label before the lookup parser was corrected.
        reconcile_zone_labels(connection)
