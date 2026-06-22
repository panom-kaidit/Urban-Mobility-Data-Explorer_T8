"""
Top-N Pickup Zones  counts how many trips started in each zone, sorts
them with our custom Merge Sort, and returns the top N.

Time complexity  (database path):  O(z log z)  where z = number of zones.
                                   SQL does the counting; Python does the ranking.
Space complexity: O(z).
"""

from backend.algorithms.merge_sort import merge_sort


def get_value(row, column_name):
    """
    Reads a column from either a dict-like or object-like row, so the
    algorithm works with both SQLite rows and plain Python dicts in tests.
    """
    try:
        return row[column_name]
    except (KeyError, TypeError):
        return getattr(row, column_name)


def count_pickup_zones(trip_rows):
    """
    Walks every trip and counts how many started in each zone.
    Keyed by pickup location ID, so each zone only gets one entry.
    """
    zone_counts = {}

    for trip_row in trip_rows:
        pickup_location_id = get_value(trip_row, "pu_location_id")

        # Skip rows with no pickup location -- shouldn't happen in clean data, but good to guard against in tests.
        if pickup_location_id is None:
            continue

        if pickup_location_id not in zone_counts:
            zone_counts[pickup_location_id] = {
                "zone_id": pickup_location_id,
                "zone_name": get_value(trip_row, "pickup_zone"),
                "borough": get_value(trip_row, "pickup_borough"),
                "trip_count": 0,
            }

        zone_counts[pickup_location_id]["trip_count"] += 1

    return zone_counts


def convert_counts_to_list(zone_counts):
    """Converts the zone counts dict into a list so Merge Sort can work on it."""
    zone_summary_list = []

    for zone_id in zone_counts:
        zone_summary_list.append(zone_counts[zone_id])

    return zone_summary_list


def take_top_n(sorted_zones, top_n):
    """Grabs the first N items from an already-sorted list."""
    top_zones = []
    current_index = 0

    while current_index < len(sorted_zones) and current_index < top_n:
        top_zones.append(sorted_zones[current_index])
        current_index += 1

    return top_zones


def find_top_pickup_zones(trip_rows, top_n=10):
    """
    Main entry point — counts zones, sorts with Merge Sort, returns top N.
    No sorted(), list.sort(), Counter, heapq, pandas, or numpy.
    """
    if top_n < 1:
        return []

    zone_counts = count_pickup_zones(trip_rows)
    zone_summary_list = convert_counts_to_list(zone_counts)
    sorted_zones = merge_sort(zone_summary_list, "trip_count", descending=True)

    return take_top_n(sorted_zones, top_n)


def fetch_zone_counts_from_db(database_connection):
    """
    Reads the pickup-zone counts precomputed by the ETL instead of scanning
    and grouping the trips table. The custom merge sort still ranks the
    resulting small set of zone rows.

    Each row has:  zone_id, zone_name, borough, trip_count
    """
    return database_connection.execute(
        """
        SELECT
            zone_id,
            zone_name,
            borough,
            trip_count
        FROM analytics_pickup_zones
        """
    ).fetchall()


def find_top_pickup_zones_from_database(database_connection, top_n=10):
    """
    Returns the top-N pickup zones by trip count.

    Reads the precomputed pickup-zone aggregate, ranks it with the custom
    merge sort, and returns the requested number of zones.
    """
    rows = fetch_zone_counts_from_db(database_connection)
    zone_list = [dict(row) for row in rows]

    # Step 3 — rank with custom merge sort (algorithm requirement)
    sorted_zones = merge_sort(zone_list, "trip_count", descending=True)

    return sorted_zones[:top_n]
