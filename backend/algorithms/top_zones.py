"""
Top-N Pickup Zones  counts how many trips started in each zone, sorts
them with our custom Merge Sort, and returns the top N.

Time complexity: O(t + z log z), space complexity: O(z).
"""

import time

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


def fetch_pickup_zone_rows(database_connection):
    """
    Pulls only the columns the algorithm needs from the trips table.
    No grouping or ordering in SQL — that's handled in Python.
    """
    cursor = database_connection.execute(
        """
        SELECT
            pu_location_id,
            pickup_zone,
            pickup_borough
        FROM trips
        """
    )

    return cursor.fetchall()

# decided to add  timmer to investigate the time taken by the function to execute and return the top n zones
# Both time taken to fetch the rows and  time to sort and return the top n zones will be measured
def find_top_pickup_zones_from_database(database_connection, top_n=10):
    """Convenience wrapper for when you already have a SQLite connection."""

    total_start_time = time.time()

    # Measuring database fetch time separately to see how much time is spent in the database query itself
    fetch_start_time = time.time()

    trip_rows = fetch_pickup_zone_rows(database_connection)

    fetch_time = time.time() - fetch_start_time

    print(f"Database fetch took {fetch_time:.2f} seconds")
    print(f"Rows fetched: {len(trip_rows)}")

    # Measuring algorithm time separately to see how much time is spent in the algorithm itself
    algorithm_start_time = time.time()

    result = find_top_pickup_zones(trip_rows, top_n)

    algorithm_time = time.time() - algorithm_start_time

    print(f"Algorithm processing took {algorithm_time:.2f} seconds")

    total_time = time.time() - total_start_time

    print(f"Total execution time: {total_time:.2f} seconds")

    return result