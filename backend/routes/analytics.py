"""Analytics routes — top pickup zones, fare distribution, and aggregated summary."""

import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.config.database import get_connection
from backend.algorithms.top_zones import find_top_pickup_zones_from_database


router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

# Module-level in-memory caches — dataset is static (January 2019 ETL load).
_summary_cache = None
_fare_distribution_cache = None
_revenue_by_borough_cache = None
_revenue_trends_cache = None
_average_fare_cache = None
_average_distance_cache = None
_top_dropoff_zones_cache: dict = {}


class SummaryResponse(BaseModel):
    total_trips: int
    total_revenue: float
    average_fare: float
    average_distance: float
    start_date: Optional[str]
    end_date: Optional[str]
    outlier_count: int
    outside_january_count: int
    suspicious_records: int
    location_count: int
    zone_boundary_count: int


def get_db():
    """Open one SQLite connection for a request, then close it."""
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


@router.get("/summary", response_model=SummaryResponse)
def get_summary(db: sqlite3.Connection = Depends(get_db)):
    """Return a single-row aggregate summary."""
    global _summary_cache
    if _summary_cache is not None:
        return _summary_cache
    try:
        row = db.execute("""
            SELECT
                COUNT(*) AS total_trips,
                COALESCE(ROUND(SUM(total_amount), 2), 0.0)    AS total_revenue,
                COALESCE(ROUND(AVG(fare_amount), 2), 0.0)     AS average_fare,
                COALESCE(ROUND(AVG(trip_distance), 2), 0.0)   AS average_distance,
                MIN(SUBSTR(pickup_datetime, 1, 10))            AS start_date,
                MAX(SUBSTR(pickup_datetime, 1, 10))            AS end_date,
                COALESCE(SUM(CASE WHEN is_outlier = 1 THEN 1 ELSE 0 END), 0)
                                                               AS outlier_count,
                COALESCE(SUM(CASE WHEN SUBSTR(pickup_datetime,1,10) < '2019-01-01'
                                       OR SUBSTR(pickup_datetime,1,10) > '2019-01-31'
                              THEN 1 ELSE 0 END), 0)           AS outside_january_count
            FROM trips
        """).fetchone()

        result: dict = dict(row)

        result["total_trips"]           = int(result.get("total_trips") or 0)
        result["total_revenue"]         = float(result.get("total_revenue") or 0)
        result["average_fare"]          = float(result.get("average_fare") or 0)
        result["average_distance"]      = float(result.get("average_distance") or 0)
        result["outlier_count"]         = int(result.get("outlier_count") or 0)
        result["outside_january_count"] = int(result.get("outside_january_count") or 0)

        result["suspicious_records"] = int(db.execute(
            "SELECT COUNT(*) FROM suspicious_records"
        ).fetchone()[0] or 0)
        result["location_count"] = int(db.execute(
            "SELECT COUNT(*) FROM locations"
        ).fetchone()[0] or 0)
        result["zone_boundary_count"] = int(db.execute(
            "SELECT COUNT(*) FROM zone_boundaries"
        ).fetchone()[0] or 0)

        if result["total_trips"] > 0:
            _summary_cache = result

        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Summary query failed: {exc}")


@router.get("/top-pickup-zones")
def get_top_pickup_zones(
    top_n: int = Query(default=10, ge=1, le=265, description="Number of top zones to return"),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return the top N pickup zones by trip count using the custom Merge Sort algorithm."""
    try:
        zones = find_top_pickup_zones_from_database(db, top_n)
        return {"algorithm": "merge_sort", "top_n": top_n, "zones": zones}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Top pickup zones query failed: {exc}")


@router.get("/top-dropoff-zones")
def get_top_dropoff_zones(
    top_n: int = Query(default=10, ge=1, le=265, description="Number of top dropoff zones to return"),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return the top N dropoff zones by trip count."""
    global _top_dropoff_zones_cache
    cache_key = top_n
    if cache_key in _top_dropoff_zones_cache:
        return _top_dropoff_zones_cache[cache_key]
    try:
        rows = db.execute("""
            SELECT
                do_location_id  AS zone_id,
                dropoff_zone    AS zone_name,
                dropoff_borough AS borough,
                COUNT(*)        AS trip_count
            FROM trips
            WHERE dropoff_zone IS NOT NULL
            GROUP BY do_location_id, dropoff_zone, dropoff_borough
            ORDER BY trip_count DESC
            LIMIT ?
        """, (top_n,)).fetchall()
        result = {"top_n": top_n, "zones": [dict(r) for r in rows]}
        _top_dropoff_zones_cache[cache_key] = result
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Top dropoff zones query failed: {exc}")


@router.get("/fare-distribution")
def get_fare_distribution(db: sqlite3.Connection = Depends(get_db)):
    """Return distribution of fares across price ranges."""
    global _fare_distribution_cache
    if _fare_distribution_cache is not None:
        return _fare_distribution_cache
    try:
        rows = db.execute("""
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
        """).fetchall()
        result = {"distribution": [dict(r) for r in rows]}
        _fare_distribution_cache = result
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fare distribution query failed: {exc}")


@router.get("/revenue-by-borough")
def get_revenue_by_borough(db: sqlite3.Connection = Depends(get_db)):
    """Return total revenue grouped by pickup borough, ordered highest first."""
    global _revenue_by_borough_cache
    if _revenue_by_borough_cache is not None:
        return _revenue_by_borough_cache
    try:
        rows = db.execute("""
            SELECT
                pickup_borough              AS borough,
                COUNT(*)                    AS total_trips,
                ROUND(SUM(total_amount), 2) AS total_revenue,
                ROUND(AVG(total_amount), 2) AS avg_revenue_per_trip
            FROM trips
            WHERE pickup_borough IS NOT NULL
              AND pickup_borough != 'Unknown'
            GROUP BY pickup_borough
            ORDER BY total_revenue DESC
        """).fetchall()
        result = {"boroughs": [dict(r) for r in rows]}
        _revenue_by_borough_cache = result
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Revenue by borough query failed: {exc}")


@router.get("/revenue-trends")
def get_revenue_trends(db: sqlite3.Connection = Depends(get_db)):
    """Return daily revenue trend across the dataset's date range."""
    global _revenue_trends_cache
    if _revenue_trends_cache is not None:
        return _revenue_trends_cache
    try:
        rows = db.execute("""
            SELECT
                SUBSTR(pickup_datetime, 1, 10) AS date,
                COUNT(*)                        AS total_trips,
                ROUND(SUM(total_amount), 2)     AS total_revenue,
                ROUND(AVG(total_amount), 2)     AS avg_fare
            FROM trips
            WHERE pickup_datetime IS NOT NULL
            GROUP BY SUBSTR(pickup_datetime, 1, 10)
            ORDER BY date ASC
        """).fetchall()
        result = {"trend": [dict(r) for r in rows]}
        _revenue_trends_cache = result
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Revenue trends query failed: {exc}")


@router.get("/average-fare")
def get_average_fare(db: sqlite3.Connection = Depends(get_db)):
    """Return average fare, tip, and total broken down by borough and payment method."""
    global _average_fare_cache
    if _average_fare_cache is not None:
        return _average_fare_cache
    try:
        rows = db.execute("""
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
              AND fare_amount > 0
            GROUP BY pickup_borough, payment_type
            ORDER BY pickup_borough, total_trips DESC
        """).fetchall()
        result = {"fares": [dict(r) for r in rows]}
        _average_fare_cache = result
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Average fare query failed: {exc}")


@router.get("/average-distance")
def get_average_distance(db: sqlite3.Connection = Depends(get_db)):
    """Return average trip distance and duration grouped by pickup hour."""
    global _average_distance_cache
    if _average_distance_cache is not None:
        return _average_distance_cache
    try:
        rows = db.execute("""
            SELECT
                pickup_hour                          AS hour,
                COUNT(*)                             AS trip_count,
                ROUND(AVG(trip_distance), 2)         AS avg_distance,
                ROUND(AVG(trip_duration_minutes), 1) AS avg_duration_minutes
            FROM trips
            WHERE pickup_hour IS NOT NULL
              AND trip_distance > 0
            GROUP BY pickup_hour
            ORDER BY pickup_hour ASC
        """).fetchall()
        result = {"distances": [dict(r) for r in rows]}
        _average_distance_cache = result
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Average distance query failed: {exc}")