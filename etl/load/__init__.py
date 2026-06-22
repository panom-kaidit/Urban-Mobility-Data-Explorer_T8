"""Lazy entry points for the database loaders.

Keeping these imports lazy avoids preloading a loader when it is executed with
``python -m etl.load.<loader_name>``.
"""


def load_locations():
    from .load_locations import load_locations as run

    return run()


def load_zone_boundaries():
    from .load_zone_boundaries import load_zone_boundaries as run

    return run()


def load_trips():
    from .load_trips import load_trips as run

    return run()


def run_all_loaders():
    from .load_all import load_all as run

    return run()


__all__ = [
    "load_locations",
    "load_zone_boundaries",
    "load_trips",
    "run_all_loaders",
]
