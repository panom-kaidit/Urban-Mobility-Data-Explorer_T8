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

