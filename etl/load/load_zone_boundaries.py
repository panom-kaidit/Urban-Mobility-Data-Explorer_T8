import json
from etl.extract import SpatialLoader
from etl.utils.config import SPATIAL_FILE


def load_zone_boundaries_data():
    """
    Load taxi zone shapefile and reproject from NAD83 State Plane (feet)
    to WGS84 lat/lon so the frontend can render polygons on a Leaflet map.
    """
    loader = SpatialLoader(SPATIAL_FILE)
    zones = loader.load()

    # reproject to WGS84 (EPSG:4326) — standard lat/lon for web mapping
    zones = zones.to_crs("EPSG:4326")

    return zones


if __name__ == "__main__":
    zones = load_zone_boundaries_data()
    print(f"Loaded {len(zones)} zone boundaries")
    print(f"CRS after reprojection: {zones.crs}")
    print(zones[["LocationID", "zone", "borough"]].head())