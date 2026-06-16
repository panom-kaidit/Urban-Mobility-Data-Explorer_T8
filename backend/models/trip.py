# Creating trip model with pydantic
from pydantic import BaseModel

class Trip(BaseModel):
    trip_id: int
    vendor_id: int | None = None
    pickup_datetime: str 
    dropoff_datetime: str 
    trip_distance: float 
    fare_amount: float 
    total_amount: float

    class Config:
        from_attributes = True