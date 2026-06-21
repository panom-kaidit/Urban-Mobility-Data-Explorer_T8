"""Analytics routes for mobility dashboard charts."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from backend.config.database import get_connection


router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def get_db():
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


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
