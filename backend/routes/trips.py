import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.config.database import get_read_connection


router = APIRouter(prefix="/api/trips", tags=["Trips"])


def get_db():
    """Open one SQLite connection for a request, then close it."""
    connection = get_read_connection()
    try:
        yield connection
    finally:
        connection.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a SQLite row into a normal dictionary for JSON responses."""
    return dict(row)


@router.get("")
def list_trips(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return a paginated list of trips."""
    try:
        total_count = db.execute(
            "SELECT COUNT(*) FROM trips",
        ).fetchone()[0]

        query = """
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
            ORDER BY pickup_datetime DESC
            LIMIT ? OFFSET ?
        """

        rows = db.execute(query, [limit, offset]).fetchall()

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
