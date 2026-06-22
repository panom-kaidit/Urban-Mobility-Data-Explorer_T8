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
