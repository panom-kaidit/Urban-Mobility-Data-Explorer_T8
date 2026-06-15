import json
from etl.extract import SpatialLoader
from etl.utils.config import SPATIAL_FILE
from backend.config.database import get_connection


def load_zone_boundaries_data():
    """
    Load taxi zone shapefile and reproject from NAD83 State Plane (feet)
    to WGS84 lat/lon so the frontend can render polygons on a Leaflet map.

    Some zones (e.g. Corona, Governor's Island) span multiple disconnected
    polygons stored as separate rows in the shapefile. We dissolve them into
    a single MultiPolygon per LocationID before storing.
    """
    loader = SpatialLoader(SPATIAL_FILE)
    zones = loader.load()

    # reproject to WGS84 (EPSG:4326) — standard lat/lon for web mapping
    zones = zones.to_crs("EPSG:4326")

    # dissolve duplicate LocationIDs into single MultiPolygon rows
    # keep first value of zone/borough/Shape_Area/Shape_Leng per group
    zones = zones.dissolve(
        by="LocationID",
        aggfunc={
            "zone":       "first",
            "borough":    "first",
            "Shape_Area": "sum",
            "Shape_Leng": "sum",
        }
    ).reset_index()

    return zones


def load_zone_boundaries():
    """Load zone polygon data from the shapefile into the zone_boundaries table."""
    zones = load_zone_boundaries_data()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM zone_boundaries")

    rows_inserted = 0
    for _, row in zones.iterrows():
        location_id  = int(row["LocationID"])
        zone         = str(row["zone"]) if row["zone"] else None
        borough      = str(row["borough"]) if row["borough"] else None
        shape_area   = float(row["Shape_Area"]) if row.get("Shape_Area") is not None else None
        shape_length = float(row["Shape_Leng"]) if row.get("Shape_Leng") is not None else None

        # convert shapely geometry to GeoJSON string for SQLite text storage
        geometry_geojson = json.dumps(row["geometry"].__geo_interface__)

        cursor.execute("""
            INSERT INTO zone_boundaries
                (location_id, zone, borough, shape_area, shape_length, geometry)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (location_id, zone, borough, shape_area, shape_length, geometry_geojson))

        rows_inserted += 1

    conn.commit()
    conn.close()

    print(f"Loaded {rows_inserted} zone boundaries.")


if __name__ == "__main__":
    load_zone_boundaries()