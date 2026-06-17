"""Analytics routes — top pickup zones and fare distribution."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from backend.config.database import get_connection
from backend.algorithms.top_zones import find_top_pickup_zones_from_database


router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


def get_db():
    """Open one SQLite connection for a request, then close it."""
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


@router.get("/top-pickup-zones")
def get_top_pickup_zones(
    top_n: int = Query(default=10, ge=1, le=265, description="Number of top zones to return"),
    db: sqlite3.Connection = Depends(get_db),
):
    """ Return the top N pickup zones by trip count.
    Uses the custom Merge Sort algorithm (backend/algorithms/merge_sort.py).
    """
    zones = find_top_pickup_zones_from_database(db, top_n)

    return {
        "algorithm": "merge_sort",
        "top_n": top_n,
        "zones": zones,
    }



@router.get("/fare-distribution")
def get_fare_distribution(
    db: sqlite3.Connection = Depends(get_db),
):
    """Return the distribution of fares across price ranges.
    Groups fares into ranges and reports trip count, average fare,
    and total revenue per range.
    """
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
#Get revenue-by borough

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
        GROUP BY pickup_borough
        ORDER BY total_revenue DESC
        """
    ).fetchall()

    return {
        "boroughs": [dict(row) for row in rows],
    }


