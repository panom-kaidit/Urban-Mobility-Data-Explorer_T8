import json
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from backend.config.database import get_read_connection


router = APIRouter(prefix="/api/zones", tags=["Zones"])


def get_db():
    """Open one SQLite connection for a request, then close it."""
    connection = get_read_connection()
    try:
        yield connection
    finally:
        connection.close()


@router.get("")
def list_zone_map(db: sqlite3.Connection = Depends(get_db)):
    """Return every mapped taxi zone with precomputed pickup revenue."""
    try:
        rows = db.execute("""
            SELECT
                locations.location_id,
                locations.borough,
                locations.zone,
                locations.service_zone,
                zone_boundaries.shape_area,
                zone_boundaries.shape_length,
                zone_boundaries.geometry,
                COALESCE(analytics_zone_revenue.trip_count, 0) AS trip_count,
                COALESCE(analytics_zone_revenue.total_revenue, 0.0) AS total_revenue,
                CASE
                    WHEN COALESCE(analytics_zone_revenue.trip_count, 0) > 0
                    THEN ROUND(
                        analytics_zone_revenue.total_revenue
                        / analytics_zone_revenue.trip_count,
                        2
                    )
                    ELSE 0.0
                END AS average_revenue_per_trip
            FROM locations
            INNER JOIN zone_boundaries
                ON zone_boundaries.location_id = locations.location_id
            LEFT JOIN analytics_zone_revenue
                ON analytics_zone_revenue.zone_id = locations.location_id
            WHERE zone_boundaries.geometry IS NOT NULL
            ORDER BY locations.location_id
        """).fetchall()
        zones = []
        for row in rows:
            zone = dict(row)
            zone["geometry"] = json.loads(zone["geometry"])
            zones.append(zone)
        metadata = db.execute("""
            SELECT
                (SELECT COUNT(*) FROM locations) AS total_zones,
                (SELECT COUNT(*) FROM zone_boundaries WHERE geometry IS NOT NULL)
                    AS boundary_count,
                (SELECT COUNT(DISTINCT borough) FROM locations
                 WHERE borough NOT IN ('N/A', 'Unknown')) AS borough_count
        """).fetchone()
        return {**dict(metadata), "count": len(zones), "zones": zones}
    except Exception:
        raise HTTPException(status_code=500, detail="Zone map data unavailable")


@router.get("/{zone_id}")
def get_zone(
    zone_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    """Return one taxi zone with its optional map boundary."""
    if zone_id < 1:
        raise HTTPException(status_code=400, detail="Zone ID must be a positive integer")

    try:
        row = db.execute(
            """
            SELECT
                locations.location_id,
                locations.borough,
                locations.zone,
                locations.service_zone,
                zone_boundaries.shape_area,
                zone_boundaries.shape_length,
                zone_boundaries.geometry
            FROM locations
            LEFT JOIN zone_boundaries
                ON zone_boundaries.location_id = locations.location_id
            WHERE locations.location_id = ?
            """,
            (zone_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Zone not found")

        return dict(row)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Zone data unavailable")
