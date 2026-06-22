"""Analytics routes backed by ETL-generated aggregate tables."""

import sqlite3
from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.algorithms.merge_sort import merge_sort
from backend.algorithms.top_zones import find_top_pickup_zones_from_database
from backend.config.database import get_read_connection


router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


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
    connection = get_read_connection()
    try:
        yield connection
    finally:
        connection.close()


def _dashboard_where(borough: Optional[str], pickup_date: Optional[str]):
    """Build predicates for the small dashboard aggregate tables."""
    conditions = []
    params = []

    if borough:
        conditions.append("pickup_borough = ?")
        params.append(borough)

    if pickup_date:
        try:
            date_type.fromisoformat(pickup_date)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid pickup_date. Use YYYY-MM-DD.",
            )
        conditions.append("pickup_date = ?")
        params.append(pickup_date)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    return where, params


@router.get("/dashboard-filter-options")
def get_dashboard_filter_options(db: sqlite3.Connection = Depends(get_db)):
    """Return valid pickup boroughs and dates from the dashboard cube."""
    try:
        boroughs = db.execute("""
            SELECT DISTINCT pickup_borough
            FROM analytics_dashboard_slices
            WHERE pickup_borough NOT IN ('Unknown', 'N/A')
            ORDER BY pickup_borough
        """).fetchall()
        dates = db.execute("""
            SELECT DISTINCT pickup_date
            FROM analytics_dashboard_slices
            ORDER BY pickup_date
        """).fetchall()
        return {
            "boroughs": [row[0] for row in boroughs],
            "pickup_dates": [row[0] for row in dates],
        }
    except Exception:
        raise HTTPException(status_code=500, detail="Dashboard filters unavailable")


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    borough: Optional[str] = Query(default=None),
    pickup_date: Optional[str] = Query(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return the dataset summary."""
    try:
        if borough or pickup_date:
            where, params = _dashboard_where(borough, pickup_date)
            row = db.execute(f"""
                SELECT
                    COALESCE(SUM(total_trips), 0) AS total_trips,
                    COALESCE(ROUND(SUM(total_revenue), 2), 0.0) AS total_revenue,
                    COALESCE(ROUND(SUM(total_fare) / NULLIF(SUM(total_trips), 0), 2), 0.0)
                        AS average_fare,
                    COALESCE(ROUND(SUM(total_distance) / NULLIF(SUM(total_trips), 0), 2), 0.0)
                        AS average_distance,
                    MIN(pickup_date) AS start_date,
                    MAX(pickup_date) AS end_date,
                    COALESCE(SUM(outlier_count), 0) AS outlier_count,
                    COALESCE(SUM(outside_january_count), 0) AS outside_january_count
                FROM analytics_dashboard_slices{where}
            """, params).fetchone()
            metadata = db.execute("""
                SELECT suspicious_records, location_count, zone_boundary_count
                FROM analytics_summary WHERE singleton_id = 1
            """).fetchone()
            if metadata is None:
                raise HTTPException(status_code=503, detail="Summary data unavailable")
            result = dict(row)
            result.update(dict(metadata))
            return result

        row = db.execute("""
            SELECT
                total_trips, total_revenue, average_fare,
                average_distance, start_date, end_date,
                outlier_count, outside_january_count,
                suspicious_records, location_count, zone_boundary_count
            FROM analytics_summary
            WHERE singleton_id = 1
        """).fetchone()
        if row is None:
            raise HTTPException(status_code=503, detail="Summary data unavailable")
        return dict(row)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Summary data unavailable")


@router.get("/top-pickup-zones")
def get_top_pickup_zones(
    top_n: int = Query(default=10, ge=1, le=265),
    borough: Optional[str] = Query(default=None),
    pickup_date: Optional[str] = Query(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return the top pickup zones."""
    try:
        if borough or pickup_date:
            where, params = _dashboard_where(borough, pickup_date)
            rows = db.execute(f"""
                SELECT zone_id, MIN(zone_name) AS zone_name,
                       MIN(pickup_borough) AS borough,
                       SUM(trip_count) AS trip_count
                FROM analytics_dashboard_pickup_zones{where}
                GROUP BY zone_id
            """, params).fetchall()
            zones = merge_sort(
                [dict(row) for row in rows], "trip_count", descending=True
            )[:top_n]
            return {"algorithm": "merge_sort", "top_n": top_n, "zones": zones}

        zones = find_top_pickup_zones_from_database(db, top_n)
        return {"algorithm": "merge_sort", "top_n": top_n, "zones": zones}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Pickup zone data unavailable")


@router.get("/top-dropoff-zones")
def get_top_dropoff_zones(
    top_n: int = Query(default=10, ge=1, le=265),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return the top dropoff zones."""
    try:
        rows = db.execute("""
            SELECT zone_id, zone_name, borough, trip_count
            FROM analytics_dropoff_zones
            ORDER BY trip_count DESC
            LIMIT ?
        """, (top_n,)).fetchall()
        return {"top_n": top_n, "zones": [dict(row) for row in rows]}
    except Exception:
        raise HTTPException(status_code=500, detail="Dropoff zone data unavailable")


@router.get("/fare-distribution")
def get_fare_distribution(
    borough: Optional[str] = Query(default=None),
    pickup_date: Optional[str] = Query(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return the fare distribution."""
    try:
        if borough or pickup_date:
            where, params = _dashboard_where(borough, pickup_date)
            rows = db.execute(f"""
                SELECT range_label AS range,
                       SUM(trip_count) AS trip_count,
                       ROUND(SUM(fare_total) / NULLIF(SUM(trip_count), 0), 2) AS avg_fare,
                       ROUND(SUM(total_revenue), 2) AS total_revenue
                FROM analytics_dashboard_fare_distribution{where}
                GROUP BY bucket_order, range_label
                HAVING SUM(trip_count) > 0
                ORDER BY bucket_order
            """, params).fetchall()
            return {"distribution": [dict(row) for row in rows]}

        rows = db.execute("""
            SELECT range_label AS range, trip_count, avg_fare, total_revenue
            FROM analytics_fare_distribution
            WHERE trip_count > 0
            ORDER BY bucket_order
        """).fetchall()
        return {"distribution": [dict(row) for row in rows]}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Fare data unavailable")


@router.get("/revenue-by-borough")
def get_revenue_by_borough(db: sqlite3.Connection = Depends(get_db)):
    """Return revenue grouped by pickup borough."""
    try:
        rows = db.execute("""
            SELECT borough, total_trips, total_revenue, avg_revenue_per_trip
            FROM analytics_borough_revenue
            ORDER BY total_revenue DESC
        """).fetchall()
        return {"boroughs": [dict(row) for row in rows]}
    except Exception:
        raise HTTPException(status_code=500, detail="Borough revenue data unavailable")


@router.get("/revenue-trends")
def get_revenue_trends(db: sqlite3.Connection = Depends(get_db)):
    """Return daily revenue totals."""
    try:
        rows = db.execute("""
            SELECT date, total_trips, total_revenue, avg_fare
            FROM analytics_daily_revenue
            ORDER BY date ASC
        """).fetchall()
        return {"trend": [dict(row) for row in rows]}
    except Exception:
        raise HTTPException(status_code=500, detail="Revenue trend data unavailable")


@router.get("/average-fare")
def get_average_fare(db: sqlite3.Connection = Depends(get_db)):
    """Return average fare metrics by borough and payment method."""
    try:
        rows = db.execute("""
            SELECT borough, payment_method, total_trips,
                   avg_fare, avg_tip, avg_total
            FROM analytics_average_fare
            ORDER BY borough, total_trips DESC
        """).fetchall()
        return {"fares": [dict(row) for row in rows]}
    except Exception:
        raise HTTPException(status_code=500, detail="Average fare data unavailable")


@router.get("/average-distance")
def get_average_distance(db: sqlite3.Connection = Depends(get_db)):
    """Return hourly trip-distance metrics."""
    try:
        rows = db.execute("""
            SELECT hour, trip_count, avg_distance, avg_duration_minutes
            FROM analytics_hourly_distance
            ORDER BY hour ASC
        """).fetchall()
        return {"distances": [dict(row) for row in rows]}
    except Exception:
        raise HTTPException(status_code=500, detail="Distance data unavailable")
