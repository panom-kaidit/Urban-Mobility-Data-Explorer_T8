
from fastapi import APIRouter, HTTPException

from data import TRIPS
from models import Trip

router = APIRouter(prefix="/trips", tags=["Trips"])


@router.get("", response_model=list[Trip])
def list_trips(hour: int | None = None):
    """All trips. Pass ?hour=8 to see only trips that started at 8am."""
    if hour is None:
        return TRIPS
    return [t for t in TRIPS if t["pickup_hour"] == hour]


@router.get("/{trip_id}", response_model=Trip)
def get_trip(trip_id: int):
    """One trip by its id."""
    for trip in TRIPS:
        if trip["id"] == trip_id:
            return trip
    raise HTTPException(status_code=404, detail=f"No trip with id {trip_id}")