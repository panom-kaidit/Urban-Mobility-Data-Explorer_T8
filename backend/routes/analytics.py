"""Analytics routes — top pickup zones, fare distribution, and aggregated summary."""

import sqlite3
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from backend.config.database import get_connection
from backend.algorithms.top_zones import find_top_pickup_zones_from_database
from backend.algorithms.merge_sort import merge_sort


router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

_summary_lock = Lock()
_revenue_lock = Lock()
_fare_lock = Lock()
_average_fare_lock = Lock()
_trend_lock = Lock()
_distance_lock = Lock()
_top_pickup_zones_lock = Lock()
_top_dropoff_zones_lock = Lock()


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


def _build_filters(borough=None, date=None, distance=None, fare=None):
    """Return (conditions, params) for optional trip-table filters, matching trips.py logic."""
    conditions = []
    params = []
    if borough:
        conditions.append("(pickup_borough = ? OR dropoff_borough = ?)")
        params.extend([borough, borough])
    if distance is not None:
        conditions.append("trip_distance <= ?")
        params.append(distance)
    if fare is not None:
        conditions.append("total_amount <= ?")
        params.append(fare)
    if date:
        try:
            next_day = (datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        conditions.append("pickup_datetime >= ? AND pickup_datetime < ?")
        params.extend([date, next_day])
    return conditions, params


@router.get("/summary", response_model=SummaryResponse)
def get_summary(
    borough: Optional[str] = Query(default=None),
    date: Optional[str] = Query(default=None),
    distance: Optional[float] = Query(default=None, ge=0),
    fare: Optional[float] = Query(default=None, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return a single-row aggregate summary."""
    is_filtered = any([borough, date, distance is not None, fare is not None])

    if not is_filtered:
        with _summary_lock:
            try:
                row = db.execute("""
                    SELECT
                        total_trips, total_revenue, average_fare,
                        average_distance, start_date, end_date,
                        outlier_count, outside_january_count,
                        suspicious_records, location_count, zone_boundary_count
                    FROM analytics_summary
                    WHERE singleton_id = 1
                """).fetchone()
                result: dict = dict(row)
                result["total_trips"]           = int(result.get("total_trips") or 0)
                result["total_revenue"]         = float(result.get("total_revenue") or 0)
                result["average_fare"]          = float(result.get("average_fare") or 0)
                result["average_distance"]      = float(result.get("average_distance") or 0)
                result["outlier_count"]         = int(result.get("outlier_count") or 0)
                result["outside_january_count"] = int(result.get("outside_january_count") or 0)
                return result
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Summary query failed: {exc}")

    # Filtered requests require the source table because aggregates are unfiltered.
    conditions, params = _build_filters(borough, date, distance, fare)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    try:
        row = db.execute(f"""
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
            FROM trips {where}
        """, params).fetchone()
        result: dict = dict(row)
        result["total_trips"]           = int(result.get("total_trips") or 0)
        result["total_revenue"]         = float(result.get("total_revenue") or 0)
        result["average_fare"]          = float(result.get("average_fare") or 0)
        result["average_distance"]      = float(result.get("average_distance") or 0)
        result["outlier_count"]         = int(result.get("outlier_count") or 0)
        result["outside_january_count"] = int(result.get("outside_january_count") or 0)
        # suspicious_records / location_count / zone_boundary_count are dataset-level
        # metadata, not trip rows — they are always returned unfiltered.
        result["suspicious_records"] = int(db.execute(
            "SELECT COUNT(*) FROM suspicious_records"
        ).fetchone()[0] or 0)
        result["location_count"] = int(db.execute(
            "SELECT COUNT(*) FROM locations"
        ).fetchone()[0] or 0)
        result["zone_boundary_count"] = int(db.execute(
            "SELECT COUNT(*) FROM zone_boundaries"
        ).fetchone()[0] or 0)
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Summary query failed: {exc}")


@router.get("/top-pickup-zones")
def get_top_pickup_zones(
    top_n: int = Query(default=10, ge=1, le=265),
    borough: Optional[str] = Query(default=None),
    date: Optional[str] = Query(default=None),
    distance: Optional[float] = Query(default=None, ge=0),
    fare: Optional[float] = Query(default=None, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    is_filtered = any([borough, date, distance is not None, fare is not None])

    if not is_filtered:
        with _top_pickup_zones_lock:
            try:
                zones = find_top_pickup_zones_from_database(db, top_n)
                result = {"algorithm": "merge_sort", "top_n": top_n, "zones": zones}
                return result
            except Exception as exc:
                raise HTTPException(
                    status_code=500,
                    detail=f"Top pickup zones query failed: {exc}"
                )

    # Filtered path — run GROUP BY with filter conditions, then merge_sort.
    conditions, params = _build_filters(borough, date, distance, fare)
    all_conditions = ["pu_location_id IS NOT NULL"] + conditions
    where = "WHERE " + " AND ".join(all_conditions)
    try:
        rows = db.execute(f"""
            SELECT
                pu_location_id AS zone_id,
                pickup_zone    AS zone_name,
                pickup_borough AS borough,
                COUNT(*)       AS trip_count
            FROM trips {where}
            GROUP BY pu_location_id
        """, params).fetchall()
        zone_list = [dict(r) for r in rows]
        sorted_zones = merge_sort(zone_list, "trip_count", descending=True)
        return {"algorithm": "merge_sort", "top_n": top_n, "zones": sorted_zones[:top_n]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Top pickup zones query failed: {exc}")


@router.get("/top-dropoff-zones")
def get_top_dropoff_zones(
    top_n: int = Query(default=10, ge=1, le=265, description="Number of top dropoff zones to return"),
    borough: Optional[str] = Query(default=None),
    date: Optional[str] = Query(default=None),
    distance: Optional[float] = Query(default=None, ge=0),
    fare: Optional[float] = Query(default=None, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return the top N dropoff zones by trip count."""
    is_filtered = any([borough, date, distance is not None, fare is not None])

    if not is_filtered:
        with _top_dropoff_zones_lock:
            try:
                rows = db.execute("""
                    SELECT
                        zone_id, zone_name, borough, trip_count
                    FROM analytics_dropoff_zones
                    ORDER BY trip_count DESC
                    LIMIT ?
                """, (top_n,)).fetchall()
                result = {"top_n": top_n, "zones": [dict(r) for r in rows]}
                return result
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Top dropoff zones query failed: {exc}")

    # Filtered path — adds filter conditions to the WHERE clause.
    conditions, params = _build_filters(borough, date, distance, fare)
    all_conditions = ["dropoff_zone IS NOT NULL"] + conditions
    where = "WHERE " + " AND ".join(all_conditions)
    try:
        rows = db.execute(f"""
            SELECT
                do_location_id  AS zone_id,
                MIN(dropoff_zone)    AS zone_name,
                MIN(dropoff_borough) AS borough,
                COUNT(*)        AS trip_count
            FROM trips {where}
            GROUP BY do_location_id
            ORDER BY trip_count DESC
            LIMIT ?
        """, params + [top_n]).fetchall()
        return {"top_n": top_n, "zones": [dict(r) for r in rows]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Top dropoff zones query failed: {exc}")


@router.get("/fare-distribution")
def get_fare_distribution(
    borough: Optional[str] = Query(default=None),
    date: Optional[str] = Query(default=None),
    distance: Optional[float] = Query(default=None, ge=0),
    fare: Optional[float] = Query(default=None, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return distribution of fares across price ranges."""
    is_filtered = any([borough, date, distance is not None, fare is not None])

    if not is_filtered:
        with _fare_lock:
            try:
                rows = db.execute("""
                    SELECT range_label AS range, trip_count, avg_fare, total_revenue
                    FROM analytics_fare_distribution
                    WHERE trip_count > 0
                    ORDER BY bucket_order
                """).fetchall()
                result = {"distribution": [dict(r) for r in rows]}
                return result
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Fare distribution query failed: {exc}")

    # Filtered path — CASE WHEN avoids repeating params once per UNION ALL branch.
    conditions, params = _build_filters(borough, date, distance, fare)
    extra = (" AND " + " AND ".join(conditions)) if conditions else ""
    try:
        rows = db.execute(f"""
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
            WHERE fare_amount > 0{extra}
            GROUP BY range
            ORDER BY MIN(fare_amount)
        """, params).fetchall()
        return {"distribution": [dict(r) for r in rows]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Fare distribution query failed: {exc}")


@router.get("/revenue-by-borough")
def get_revenue_by_borough(
    borough: Optional[str] = Query(default=None),
    date: Optional[str] = Query(default=None),
    distance: Optional[float] = Query(default=None, ge=0),
    fare: Optional[float] = Query(default=None, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return total revenue grouped by pickup borough, ordered highest first."""
    is_filtered = any([borough, date, distance is not None, fare is not None])

    if not is_filtered:
        with _revenue_lock:
            try:
                rows = db.execute("""
                    SELECT borough, total_trips, total_revenue, avg_revenue_per_trip
                    FROM analytics_borough_revenue
                    ORDER BY total_revenue DESC
                """).fetchall()
                result = {"boroughs": [dict(r) for r in rows]}
                return result
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Revenue by borough query failed: {exc}")

    # Filtered path.
    conditions, params = _build_filters(borough, date, distance, fare)
    all_conditions = ["pickup_borough IS NOT NULL", "pickup_borough != 'Unknown'"] + conditions
    where = "WHERE " + " AND ".join(all_conditions)
    try:
        rows = db.execute(f"""
            SELECT
                pickup_borough              AS borough,
                COUNT(*)                    AS total_trips,
                ROUND(SUM(total_amount), 2) AS total_revenue,
                ROUND(AVG(total_amount), 2) AS avg_revenue_per_trip
            FROM trips {where}
            GROUP BY pickup_borough
            ORDER BY total_revenue DESC
        """, params).fetchall()
        return {"boroughs": [dict(r) for r in rows]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Revenue by borough query failed: {exc}")


@router.get("/revenue-trends")
def get_revenue_trends(
    borough: Optional[str] = Query(default=None),
    date: Optional[str] = Query(default=None),
    distance: Optional[float] = Query(default=None, ge=0),
    fare: Optional[float] = Query(default=None, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return daily revenue trend across the dataset's date range."""
    is_filtered = any([borough, date, distance is not None, fare is not None])

    if not is_filtered:
        with _trend_lock:
            try:
                rows = db.execute("""
                    SELECT date, total_trips, total_revenue, avg_fare
                    FROM analytics_daily_revenue
                    ORDER BY date ASC
                """).fetchall()
                result = {"trend": [dict(r) for r in rows]}
                return result
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Revenue trends query failed: {exc}")

    # Filtered path.
    conditions, params = _build_filters(borough, date, distance, fare)
    all_conditions = ["pickup_datetime IS NOT NULL"] + conditions
    where = "WHERE " + " AND ".join(all_conditions)
    try:
        rows = db.execute(f"""
            SELECT
                SUBSTR(pickup_datetime, 1, 10) AS date,
                COUNT(*)                        AS total_trips,
                ROUND(SUM(total_amount), 2)     AS total_revenue,
                ROUND(AVG(total_amount), 2)     AS avg_fare
            FROM trips {where}
            GROUP BY SUBSTR(pickup_datetime, 1, 10)
            ORDER BY date ASC
        """, params).fetchall()
        return {"trend": [dict(r) for r in rows]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Revenue trends query failed: {exc}")


@router.get("/average-fare")
def get_average_fare(
    borough: Optional[str] = Query(default=None),
    date: Optional[str] = Query(default=None),
    distance: Optional[float] = Query(default=None, ge=0),
    fare: Optional[float] = Query(default=None, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return average fare, tip, and total broken down by borough and payment method."""
    is_filtered = any([borough, date, distance is not None, fare is not None])

    if not is_filtered:
        with _average_fare_lock:
            try:
                rows = db.execute("""
                    SELECT
                        borough, payment_method, total_trips,
                        avg_fare, avg_tip, avg_total
                    FROM analytics_average_fare
                    ORDER BY borough, total_trips DESC
                """).fetchall()
                result = {"fares": [dict(r) for r in rows]}
                return result
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Average fare query failed: {exc}")

    # Filtered path.
    conditions, params = _build_filters(borough, date, distance, fare)
    all_conditions = ["pickup_borough IS NOT NULL", "pickup_borough != 'Unknown'", "fare_amount > 0"] + conditions
    where = "WHERE " + " AND ".join(all_conditions)
    try:
        rows = db.execute(f"""
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
            FROM trips {where}
            GROUP BY pickup_borough, payment_type
            ORDER BY pickup_borough, total_trips DESC
        """, params).fetchall()
        return {"fares": [dict(r) for r in rows]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Average fare query failed: {exc}")


@router.get("/average-distance")
def get_average_distance(
    borough: Optional[str] = Query(default=None),
    date: Optional[str] = Query(default=None),
    distance: Optional[float] = Query(default=None, ge=0),
    fare: Optional[float] = Query(default=None, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return average trip distance and duration grouped by pickup hour."""
    is_filtered = any([borough, date, distance is not None, fare is not None])

    if not is_filtered:
        with _distance_lock:
            try:
                rows = db.execute("""
                    SELECT
                        hour, trip_count, avg_distance, avg_duration_minutes
                    FROM analytics_hourly_distance
                    ORDER BY hour ASC
                """).fetchall()
                result = {"distances": [dict(r) for r in rows]}
                return result
            except Exception as exc:
                raise HTTPException(status_code=500, detail=f"Average distance query failed: {exc}")

    # Filtered path.
    conditions, params = _build_filters(borough, date, distance, fare)
    all_conditions = ["pickup_hour IS NOT NULL", "trip_distance > 0"] + conditions
    where = "WHERE " + " AND ".join(all_conditions)
    try:
        rows = db.execute(f"""
            SELECT
                pickup_hour                          AS hour,
                COUNT(*)                             AS trip_count,
                ROUND(AVG(trip_distance), 2)         AS avg_distance,
                ROUND(AVG(trip_duration_minutes), 1) AS avg_duration_minutes
            FROM trips {where}
            GROUP BY pickup_hour
            ORDER BY pickup_hour ASC
        """, params).fetchall()
        return {"distances": [dict(r) for r in rows]}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Average distance query failed: {exc}")
