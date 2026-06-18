"""Routes for querying suspicious records."""

import sqlite3

from fastapi import APIRouter, Depends, Query

from backend.config.database import get_connection


router = APIRouter(prefix="/api/suspicious-records", tags=["Suspicious Records"])


def get_db():
    """Open one SQLite connection for a request, then close it."""
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()

@router.get("")
def list_suspicious_records(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
):
    """Return suspicious records removed during the cleaning step.

    The response already includes limit, offset, and count so it can grow into
    full pagination later without changing the frontend shape too much.
    """
    rows = db.execute(
        """
        SELECT
            record_id,
            vendor_id,
            pickup_datetime,
            dropoff_datetime,
            passenger_count,
            trip_distance,
            rate_code_id,
            store_and_fwd_flag,
            pu_location_id,
            do_location_id,
            payment_type,
            fare_amount,
            extra,
            mta_tax,
            tip_amount,
            tolls_amount,
            improvement_surcharge,
            total_amount,
            congestion_surcharge,
            airport_fee,
            removal_reason,
            flagged_at
        FROM suspicious_records
        ORDER BY flagged_at DESC, record_id DESC
        LIMIT ? OFFSET ?
        """,
        (limit, offset),
    ).fetchall()

    return {
        "items": [dict(row) for row in rows],
        "limit": limit,
        "offset": offset,
        "count": len(rows),
    }
