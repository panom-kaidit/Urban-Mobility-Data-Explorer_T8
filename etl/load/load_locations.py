from etl.extract import LookupLoader
from etl.utils.config import LOOKUP_FILE
from backend.config.database import get_connection


def load_locations_data():
    """Load taxi zone lookup data and rename columns to match the locations table."""
    loader = LookupLoader(LOOKUP_FILE)
    lookup_data = loader.load()

    locations = lookup_data.rename(columns={
        "LocationID": "location_id",
        "Borough": "borough",
        "Zone": "zone",
    })

    return locations[["location_id", "borough", "zone", "service_zone"]]


def load_locations():
    """Load the locations dimension table from taxi_zone_lookup.csv."""
    locations = load_locations_data()

    conn = get_connection()
    cursor = conn.cursor()

    # clear existing rows so this script can be re-run safely
    cursor.execute("DELETE FROM locations")

    cursor.executemany(
        "INSERT INTO locations (location_id, borough, zone, service_zone) VALUES (?, ?, ?, ?)",
        locations.itertuples(index=False, name=None)
    )

    conn.commit()
    row_count = cursor.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
    conn.close()

    print(f"Loaded {row_count} locations.")


if __name__ == "__main__":
    load_locations()