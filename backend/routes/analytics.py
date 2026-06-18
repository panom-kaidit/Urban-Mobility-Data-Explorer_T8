
"""Analytics routes — top pickup zones and fare distribution."""

import sqlite3

from fastapi import APIRouter, Depends, Query
from backend.config.database import get_connection
from backend.algorithms.top_zones import find_top_pickup_zones_from_database


router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def display_borough(value):
    """Return a UI-friendly borough label without changing stored lookup data."""
    if value == "N/A":
        return "Unknown / N/A"
    return value


def display_service_zone(value):
    """Return a UI-friendly service-zone label without changing stored lookup data."""
    if value == "N/A":
        return "Unknown / N/A"
    return value


def zone_row_to_dict(row):
    item = dict(row)
    item["borough"] = display_borough(item.get("borough"))
    if "service_zone" in item:
        item["service_zone"] = display_service_zone(item.get("service_zone"))
    return item


def service_row_to_dict(row):
    item = dict(row)
    item["service_zone"] = display_service_zone(item.get("service_zone"))
    return item


def get_db():
    """Open one SQLite connection for a request, then close it."""
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


@router.get("/dashboard-summary")
def get_dashboard_summary(
    db: sqlite3.Connection = Depends(get_db),
):
    """Return the main numbers used at the top of the dashboard."""
    summary = db.execute(
        """
        SELECT
            COALESCE(SUM(trip_count), 0) AS total_trips,
            ROUND(COALESCE(SUM(total_revenue), 0), 2) AS total_revenue,
            ROUND(COALESCE(SUM(total_revenue) / NULLIF(SUM(trip_count), 0), 0), 2) AS avg_fare,
            ROUND(
                COALESCE(SUM(avg_distance * trip_count) / NULLIF(SUM(trip_count), 0), 0),
                2
            ) AS avg_distance,
            COUNT(*) AS active_zones
        FROM zone_metrics
        """
    ).fetchone()

    top_borough = db.execute(
        """
        SELECT
            locations.borough,
            SUM(zone_metrics.trip_count) AS trip_count
        FROM zone_metrics
        JOIN locations
            ON locations.location_id = zone_metrics.location_id
        WHERE locations.borough IS NOT NULL
          AND locations.borough != 'Unknown'
          AND locations.borough != 'N/A'
        GROUP BY locations.borough
        ORDER BY trip_count DESC
        LIMIT 1
        """
    ).fetchone()

    return {
        "total_trips": summary["total_trips"],
        "total_revenue": summary["total_revenue"],
        "avg_fare": summary["avg_fare"],
        "avg_distance": summary["avg_distance"],
        "active_zones": summary["active_zones"],
        "top_borough": dict(top_borough) if top_borough else None,
    }


@router.get("/dashboard-metrics")
def get_dashboard_metrics(
    top_n: int = Query(default=8, ge=3, le=25),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return the dashboard's cached metric bundle."""
    summary = get_dashboard_summary(db)

    borough_rows = db.execute(
        """
        SELECT
            locations.borough,
            SUM(zone_metrics.trip_count) AS total_trips,
            ROUND(SUM(zone_metrics.total_revenue), 2) AS total_revenue,
            ROUND(
                SUM(zone_metrics.total_revenue) / NULLIF(SUM(zone_metrics.trip_count), 0),
                2
            ) AS avg_fare
        FROM zone_metrics
        JOIN locations
            ON locations.location_id = zone_metrics.location_id
        WHERE locations.borough IS NOT NULL
          AND locations.borough != 'Unknown'
          AND locations.borough != 'N/A'
        GROUP BY locations.borough
        ORDER BY total_trips DESC
        """
    ).fetchall()

    service_rows = db.execute(
        """
        SELECT
            COALESCE(locations.service_zone, 'Unknown') AS service_zone,
            SUM(zone_metrics.trip_count) AS total_trips,
            ROUND(SUM(zone_metrics.total_revenue), 2) AS total_revenue
        FROM zone_metrics
        JOIN locations
            ON locations.location_id = zone_metrics.location_id
        GROUP BY COALESCE(locations.service_zone, 'Unknown')
        ORDER BY total_trips DESC
        """
    ).fetchall()

    top_zone_rows = db.execute(
        """
        SELECT
            zone_metrics.location_id AS zone_id,
            locations.zone AS zone_name,
            locations.borough,
            zone_metrics.trip_count,
            zone_metrics.total_revenue,
            zone_metrics.avg_fare,
            zone_metrics.avg_distance
        FROM zone_metrics
        JOIN locations
            ON locations.location_id = zone_metrics.location_id
        ORDER BY zone_metrics.trip_count DESC
        LIMIT ?
        """,
        (top_n,),
    ).fetchall()

    fare_rows = db.execute(
        """
        SELECT
            fare_range AS range,
            trip_count,
            avg_fare,
            total_revenue
        FROM fare_distribution_metrics
        ORDER BY sort_order
        """
    ).fetchall()

    return {
        "summary": summary,
        "boroughs": [dict(row) for row in borough_rows],
        "service_zones": [service_row_to_dict(row) for row in service_rows],
        "top_zones": [zone_row_to_dict(row) for row in top_zone_rows],
        "fare_distribution": [dict(row) for row in fare_rows],
    }


@router.get("/top-pickup-zones")
def get_top_pickup_zones(
    top_n: int = Query(default=10, ge=1, le=265, description="Number of top zones to return"),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return the top N pickup zones by trip count."""
    cached_rows = db.execute(
        """
        SELECT
            zone_metrics.location_id AS zone_id,
            locations.zone AS zone_name,
            locations.borough,
            zone_metrics.trip_count
        FROM zone_metrics
        JOIN locations
            ON locations.location_id = zone_metrics.location_id
        ORDER BY zone_metrics.trip_count DESC
        LIMIT ?
        """,
        (top_n,),
    ).fetchall()

    if cached_rows:
        return {
            "algorithm": "zone_metrics_cache",
            "top_n": top_n,
            "zones": [zone_row_to_dict(row) for row in cached_rows],
        }

    zones = find_top_pickup_zones_from_database(db, top_n)
    for zone in zones:
        zone["borough"] = display_borough(zone.get("borough"))

    return {
        "algorithm": "merge_sort",
        "top_n": top_n,
        "zones": zones,
    }


@router.get("/zone-revenue-ranking")
def get_zone_revenue_ranking(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return pickup zones ranked by total revenue."""
    total_count = db.execute(
        """
        SELECT COUNT(*)
        FROM zone_metrics
        JOIN locations
            ON locations.location_id = zone_metrics.location_id
        """
    ).fetchone()[0]

    rows = db.execute(
        """
        SELECT
            zone_metrics.location_id AS zone_id,
            locations.zone AS zone_name,
            locations.borough,
            zone_metrics.trip_count,
            ROUND(zone_metrics.total_revenue, 2) AS total_revenue,
            zone_metrics.avg_fare,
            zone_metrics.avg_distance
        FROM zone_metrics
        JOIN locations
            ON locations.location_id = zone_metrics.location_id
        ORDER BY zone_metrics.total_revenue DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()

    return {
        "items": [zone_row_to_dict(row) for row in rows],
        "limit": limit,
        "offset": offset,
        "count": total_count,
    }


@router.get("/borough-revenue-ranking")
def get_borough_revenue_ranking(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return boroughs ranked by total revenue."""
    all_rows = db.execute(
        """
        SELECT
            locations.borough,
            ROUND(SUM(zone_metrics.total_revenue), 2) AS total_revenue,
            ROUND(
                SUM(zone_metrics.total_revenue) / NULLIF(SUM(zone_metrics.trip_count), 0),
                2
            ) AS avg_fare,
            COUNT(*) AS zone_count
        FROM zone_metrics
        JOIN locations
            ON locations.location_id = zone_metrics.location_id
        WHERE locations.borough IS NOT NULL
          AND locations.borough != 'Unknown'
          AND locations.borough != 'N/A'
        GROUP BY locations.borough
        ORDER BY total_revenue DESC
        """
    ).fetchall()

    return {
        "items": [dict(row) for row in all_rows[offset:offset + limit]],
        "limit": limit,
        "offset": offset,
        "count": len(all_rows),
    }


@router.get("/hourly-trip-counts")
def get_hourly_trip_counts(
    db: sqlite3.Connection = Depends(get_db),
):
    """Return trip counts grouped by pickup hour."""
    rows = db.execute(
        """
        SELECT
            pickup_hour,
            COUNT(*) AS trip_count
        FROM trips
        WHERE pickup_hour IS NOT NULL
        GROUP BY pickup_hour
        ORDER BY pickup_hour
        """
    ).fetchall()

    trips_by_hour = {
        int(row["pickup_hour"]): row["trip_count"]
        for row in rows
    }

    return {
        "hours": [
            {
                "pickup_hour": hour,
                "trip_count": trips_by_hour.get(hour, 0),
            }
            for hour in range(24)
        ],
    }


@router.get("/borough-trip-ranking")
def get_borough_trip_ranking(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return boroughs ranked by pickup trip count."""
    all_rows = db.execute(
        """
        SELECT
            locations.borough,
            SUM(zone_metrics.trip_count) AS total_trips,
            ROUND(SUM(zone_metrics.total_revenue), 2) AS total_revenue,
            ROUND(
                SUM(zone_metrics.total_revenue) / NULLIF(SUM(zone_metrics.trip_count), 0),
                2
            ) AS avg_fare
        FROM zone_metrics
        JOIN locations
            ON locations.location_id = zone_metrics.location_id
        WHERE locations.borough IS NOT NULL
          AND locations.borough != 'Unknown'
          AND locations.borough != 'N/A'
        GROUP BY locations.borough
        ORDER BY total_trips DESC
        """
    ).fetchall()

    return {
        "items": [dict(row) for row in all_rows[offset:offset + limit]],
        "limit": limit,
        "offset": offset,
        "count": len(all_rows),
    }



@router.get("/fare-distribution")
def get_fare_distribution(
    db: sqlite3.Connection = Depends(get_db),
):
    """Return the distribution of fares across price ranges.
    Groups fares into ranges and reports trip count, average fare,
    and total revenue per range.
    """
    cached_rows = db.execute(
        """
        SELECT
            fare_range AS range,
            trip_count,
            avg_fare,
            total_revenue
        FROM fare_distribution_metrics
        ORDER BY sort_order
        """
    ).fetchall()

    if cached_rows:
        return {
            "distribution": [dict(row) for row in cached_rows],
        }

    rows = db.execute(
        """
        SELECT
            CASE
                WHEN fare_amount >= 0  AND fare_amount < 10  THEN '0-10'
                WHEN fare_amount >= 10 AND fare_amount < 20  THEN '10-20'
                WHEN fare_amount >= 20 AND fare_amount < 30  THEN '20-30'
                WHEN fare_amount >= 30 AND fare_amount < 40  THEN '30-40'
                WHEN fare_amount >= 40 AND fare_amount < 50  THEN '40-50'
                ELSE '50+'
            END AS range,
            COUNT(*)                    AS trip_count,
            ROUND(AVG(fare_amount), 2)  AS avg_fare,
            ROUND(SUM(total_amount), 2) AS total_revenue
        FROM trips
        WHERE fare_amount > 0
        GROUP BY range
        ORDER BY MIN(fare_amount)
        """
    ).fetchall()
 
    return {
        "distribution": [dict(row) for row in rows],
    }

@router.get("/revenue-by-borough")
def get_revenue_by_borough(
    db: sqlite3.Connection = Depends(get_db),
):
    """Return total revenue grouped by pickup borough, ordered highest first."""
    rows = db.execute(
        """
        SELECT
            pickup_borough              AS borough,
            COUNT(*)                    AS total_trips,
            ROUND(SUM(total_amount), 2) AS total_revenue,
            ROUND(AVG(total_amount), 2) AS avg_revenue_per_trip
        FROM trips
        WHERE pickup_borough IS NOT NULL
          AND pickup_borough != 'Unknown'
          AND pickup_borough != 'N/A'
        GROUP BY pickup_borough
        ORDER BY total_revenue DESC
        """
    ).fetchall()

    return {
        "boroughs": [dict(row) for row in rows],
    }

@router.get("/revenue-trends")
def get_revenue_trends(
    db: sqlite3.Connection = Depends(get_db),
):
    """Return daily revenue trend across the dataset's date range."""
    rows = db.execute(
        """
        SELECT
            SUBSTR(pickup_datetime, 1, 10) AS date,
            COUNT(*)                        AS total_trips,
            ROUND(SUM(total_amount), 2)     AS total_revenue,
            ROUND(AVG(total_amount), 2)     AS avg_fare
        FROM trips
        WHERE pickup_datetime IS NOT NULL
        GROUP BY SUBSTR(pickup_datetime, 1, 10)
        ORDER BY date ASC
        """
    ).fetchall()
 
    return {
        "trend": [dict(row) for row in rows],
    }
 
@router.get("/average-fare")
def get_average_fare(
    db: sqlite3.Connection = Depends(get_db),
):
    """Return average fare, tip, and total broken down by borough and payment method."""
    rows = db.execute(
        """
        SELECT
            pickup_borough              AS borough,
            CASE payment_type
                WHEN 1 THEN 'Credit Card'
                WHEN 2 THEN 'Cash'
                WHEN 3 THEN 'No Charge'
                WHEN 4 THEN 'Dispute'
                ELSE 'Other'
            END                         AS payment_method,
            COUNT(*)                    AS total_trips,
            ROUND(AVG(fare_amount), 2)  AS avg_fare,
            ROUND(AVG(tip_amount), 2)   AS avg_tip,
            ROUND(AVG(total_amount), 2) AS avg_total
        FROM trips
        WHERE pickup_borough IS NOT NULL
          AND pickup_borough != 'Unknown'
          AND pickup_borough != 'N/A'
          AND fare_amount > 0
        GROUP BY pickup_borough, payment_type
        ORDER BY pickup_borough, total_trips DESC
        """
    ).fetchall()
 
    return {
        "fares": [dict(row) for row in rows],
    }

@router.get("/top-dropoff-zones")
def get_top_dropoff_zones(
    top_n: int = Query(default=10, ge=1, le=265, description="Number of top zones to return"),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return the top dropoff zones by trip count."""
    rows = db.execute(
        """
        SELECT
            COALESCE(dropoff_zone, 'Unknown') AS dropoff_zone,
            COUNT(*) AS trip_count
        FROM trips
        GROUP BY COALESCE(dropoff_zone, 'Unknown')
        ORDER BY trip_count DESC
        LIMIT ?
        """,
        (top_n,),
    ).fetchall()

    return {
        "top_n": top_n,
        "zones": [dict(row) for row in rows],
    }


@router.get("/average-distance")
def get_average_distance_by_pickup_hour(
    db: sqlite3.Connection = Depends(get_db),
):
    """Return average trip distance for pickup hours 0 through 23."""
    rows = db.execute(
        """
        SELECT
            pickup_hour,
            ROUND(AVG(trip_distance), 2) AS average_distance
        FROM trips
        WHERE pickup_hour IS NOT NULL
        GROUP BY pickup_hour
        ORDER BY pickup_hour
        """
    ).fetchall()

    distance_by_hour = {
        int(row["pickup_hour"]): row["average_distance"]
        for row in rows
    }

    return {
        "hours": [
            {
                "pickup_hour": hour,
                "average_distance": distance_by_hour.get(hour, 0),
            }
            for hour in range(24)
        ],
    }

