import sqlite3
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config.database import get_connection


router = APIRouter(prefix="/api/trips", tags=["Trips"])


def get_db():
    """Open one SQLite connection for a request, then close it."""
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a SQLite row into a normal dictionary for JSON responses."""
    return dict(row)


@router.get("")
def list_trips(
    borough: str | None = Query(default=None, description="Pickup or dropoff borough"),
    distance: float | None = Query(default=None, ge=0, description="Maximum trip distance"),
    fare: float | None = Query(default=None, ge=0, description="Maximum total fare"),
    date: str | None = Query(default=None, description="Pickup date in YYYY-MM-DD format"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """
    Returns trips from the database. Filters by borough (pickup or dropoff),
    max distance, max fare, and pickup date — all optional.
    """
    conditions = []
    filter_values = []

    if borough:
        conditions.append("(pickup_borough = ? OR dropoff_borough = ?)")
        filter_values.extend([borough, borough])

    if distance is not None:
        conditions.append("trip_distance <= ?")
        filter_values.append(distance)

    if fare is not None:
        conditions.append("total_amount <= ?")
        filter_values.append(fare)

    if date:
        # Use a range comparison so SQLite can use idx_trips_pickup_datetime.
        # Calling date() on the column side would prevent index usage.
        try:
            next_day = (
                datetime.strptime(date, "%Y-%m-%d") + timedelta(days=1)
            ).strftime("%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        conditions.append("pickup_datetime >= ? AND pickup_datetime < ?")
        filter_values.extend([date, next_day])

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    try:
        total_count = db.execute(
            f"SELECT COUNT(*) FROM trips {where_clause}",
            filter_values,
        ).fetchone()[0]

        query = f"""
            SELECT
                trip_id,
                vendor_id,
                pickup_datetime,
                dropoff_datetime,
                passenger_count,
                trip_distance,
                rate_code_id,
                store_and_fwd_flag,
                pu_location_id,
                do_location_id,
                payment_type,
                fare_amount,
                extra,
                mta_tax,
                tip_amount,
                tolls_amount,
                improvement_surcharge,
                total_amount,
                congestion_surcharge,
                airport_fee,
                is_outlier,
                outlier_reasons,
                pickup_borough,
                pickup_zone,
                pickup_service_zone,
                dropoff_borough,
                dropoff_zone,
                dropoff_service_zone,
                trip_duration_minutes,
                average_speed_mph,
                fare_per_mile,
                pickup_hour,
                pickup_day_of_week,
                tip_percentage
            FROM trips
            {where_clause}
            ORDER BY pickup_datetime DESC
            LIMIT ? OFFSET ?
        """

        rows = db.execute(query, filter_values + [limit, offset]).fetchall()

        return {
            "items": [row_to_dict(row) for row in rows],
            "limit": limit,
            "offset": offset,
            "count": total_count,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Trip data unavailable")


@router.get("/{trip_id}")
def get_trip(
    trip_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    """Return one trip by its database ID."""
    if trip_id < 1:
        raise HTTPException(status_code=400, detail="Trip ID must be a positive integer")

    try:
        row = db.execute(
            """
            SELECT
                trip_id,
                vendor_id,
                pickup_datetime,
                dropoff_datetime,
                passenger_count,
                trip_distance,
                rate_code_id,
                store_and_fwd_flag,
                pu_location_id,
                do_location_id,
                payment_type,
                fare_amount,
                extra,
                mta_tax,
                tip_amount,
                tolls_amount,
                improvement_surcharge,
                total_amount,
                congestion_surcharge,
                airport_fee,
                is_outlier,
                outlier_reasons,
                pickup_borough,
                pickup_zone,
                pickup_service_zone,
                dropoff_borough,
                dropoff_zone,
                dropoff_service_zone,
                trip_duration_minutes,
                average_speed_mph,
                fare_per_mile,
                pickup_hour,
                pickup_day_of_week,
                tip_percentage
            FROM trips
            WHERE trip_id = ?
            """,
            (trip_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Trip not found")

        return row_to_dict(row)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Trip data unavailable")
