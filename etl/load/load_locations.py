from etl.extract import LookupLoader
from etl.utils.config import LOOKUP_FILE


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


if __name__ == "__main__":
    print(load_locations_data().head())