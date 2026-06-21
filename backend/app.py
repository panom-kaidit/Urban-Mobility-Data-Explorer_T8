import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes import trips, locations, suspicious_records, analytics
from backend.config.database import init_db, get_connection

app = FastAPI(
    title="Urban Mobility Data Explorer",
    version="1.0.0"
)

app.add_middleware(
    # we allow cors from any origin for simplicity and it will be  changed in the future when backend is on a different domain than frontend. --- IGNORE ---
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trips.router)
app.include_router(locations.router)
app.include_router(suspicious_records.router)
app.include_router(analytics.router)

@app.get("/")
def root():
    return {
        "message": "Urban Mobility Data Explorer API"
    }

init_db()

@app.on_event("startup")
def warmup_analytics_caches():
    """Pre-populate analytics caches and show timing for each step."""
    logger = logging.getLogger("uvicorn.error")

    total_start = time.perf_counter()

    try:
        db = get_connection()

        try:
            logger.info("=" * 70)
            logger.info("Starting analytics cache warmup...")

            start = time.perf_counter()
            analytics.get_summary(borough=None, date=None, distance=None, fare=None, db=db)
            logger.info(
                "[1/9] Summary cache ready (%.2fs)",
                time.perf_counter() - start
            )

            start = time.perf_counter()
            analytics.get_top_pickup_zones(top_n=10, borough=None, date=None, distance=None, fare=None, db=db)
            logger.info(
                "[2/9] Top Pickup Zones (10) cache ready (%.2fs)",
                time.perf_counter() - start
            )

            start = time.perf_counter()
            analytics.get_top_pickup_zones(top_n=15, borough=None, date=None, distance=None, fare=None, db=db)
            logger.info(
                "[3/9] Top Pickup Zones (15) cache ready (%.2fs)",
                time.perf_counter() - start
            )

            start = time.perf_counter()
            analytics.get_top_dropoff_zones(top_n=10, borough=None, date=None, distance=None, fare=None, db=db)
            logger.info(
                "[4/9] Top Dropoff Zones cache ready (%.2fs)",
                time.perf_counter() - start
            )

            start = time.perf_counter()
            analytics.get_fare_distribution(borough=None, date=None, distance=None, fare=None, db=db)
            logger.info(
                "[5/9] Fare Distribution cache ready (%.2fs)",
                time.perf_counter() - start
            )

            start = time.perf_counter()
            analytics.get_revenue_by_borough(borough=None, date=None, distance=None, fare=None, db=db)
            logger.info(
                "[6/9] Revenue By Borough cache ready (%.2fs)",
                time.perf_counter() - start
            )

            start = time.perf_counter()
            analytics.get_revenue_trends(borough=None, date=None, distance=None, fare=None, db=db)
            logger.info(
                "[7/9] Revenue Trends cache ready (%.2fs)",
                time.perf_counter() - start
            )

            start = time.perf_counter()
            analytics.get_average_fare(borough=None, date=None, distance=None, fare=None, db=db)
            logger.info(
                "[8/9] Average Fare cache ready (%.2fs)",
                time.perf_counter() - start
            )

            start = time.perf_counter()
            analytics.get_average_distance(borough=None, date=None, distance=None, fare=None, db=db)
            logger.info(
                "[9/9] Average Distance cache ready (%.2fs)",
                time.perf_counter() - start
            )

            logger.info(
                "Analytics cache warmup completed in %.2fs",
                time.perf_counter() - total_start
            )
            logger.info("=" * 70)

        finally:
            db.close()

    except Exception as exc:
        logger.warning("Analytics cache warmup failed: %s", exc)
