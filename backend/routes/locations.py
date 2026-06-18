import sqlite3
import json

from fastapi import APIRouter, Depends, HTTPException

from backend.config.database import get_connection


router = APIRouter(prefix="/api/zones", tags=["Zones"])


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


def get_db():
    """Open one SQLite connection for a request, then close it."""
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


@router.get("/map/summary")
def get_zone_map_summary(
    db: sqlite3.Connection = Depends(get_db),
):
    """Return zone boundaries with basic pickup metrics for the map."""
    rows = db.execute(
        """
        SELECT
            locations.location_id,
            locations.borough,
            locations.zone,
            locations.service_zone,
            zone_boundaries.geometry,
            COALESCE(zone_metrics.trip_count, 0) AS trip_count,
            COALESCE(zone_metrics.total_revenue, 0) AS total_revenue,
            zone_metrics.avg_fare,
            zone_metrics.avg_distance
        FROM locations
        LEFT JOIN zone_boundaries
            ON zone_boundaries.location_id = locations.location_id
        LEFT JOIN zone_metrics
            ON zone_metrics.location_id = locations.location_id
        WHERE zone_boundaries.geometry IS NOT NULL
        ORDER BY trip_count DESC
        """
    ).fetchall()

    features = []
    for row in rows:
        features.append({
            "type": "Feature",
            "geometry": json.loads(row["geometry"]),
            "properties": {
                "location_id": row["location_id"],
                "borough": display_borough(row["borough"]),
                "zone": row["zone"],
                "service_zone": display_service_zone(row["service_zone"]),
                "trip_count": row["trip_count"],
                "total_revenue": row["total_revenue"],
                "avg_fare": row["avg_fare"],
                "avg_distance": row["avg_distance"],
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/{zone_id}")
def get_zone(
    zone_id: int,
    db: sqlite3.Connection = Depends(get_db),
):
    """Return one taxi zone with its optional map boundary."""
    if zone_id < 1:
        raise HTTPException(status_code=400, detail="Zone ID must be a positive integer")

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

    zone = dict(row)
    zone["borough"] = display_borough(zone["borough"])
    zone["service_zone"] = display_service_zone(zone["service_zone"])
    return zone
