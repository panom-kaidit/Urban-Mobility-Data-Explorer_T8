from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .location import Base


class Trip(Base):
    """Clean taxi trip record from the trips table.
    """

    __tablename__ = "trips"

    # Database-generated primary key for each cleaned trip automatically.
    trip_id = Column(Integer, primary_key=True, autoincrement=True)

    # Raw trip fields loaded from the taxi trip dataset.
    vendor_id = Column(Integer, nullable=True)
    pickup_datetime = Column(Text, nullable=False)
    dropoff_datetime = Column(Text, nullable=False)
    passenger_count = Column(Integer, nullable=True)
    trip_distance = Column(Float, nullable=False)
    rate_code_id = Column(Integer, nullable=True)
    store_and_fwd_flag = Column(String, nullable=True)
    pu_location_id = Column(Integer, ForeignKey("locations.location_id"), nullable=False)
    do_location_id = Column(Integer, ForeignKey("locations.location_id"), nullable=False)
    payment_type = Column(Integer, nullable=True)

    # Fare and payment fields. The ETL pipeline removes trips with negative or zero fare_amount or total_amount.
    fare_amount = Column(Float, nullable=False)
    extra = Column(Float, nullable=True)
    mta_tax = Column(Float, nullable=True)
    tip_amount = Column(Float, nullable=True)
    tolls_amount = Column(Float, nullable=True)
    improvement_surcharge = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=False)
    congestion_surcharge = Column(Float, nullable=True)
    airport_fee = Column(Float, nullable=True)

    # The ETL keeps suspicious-but-valid trips and marks them instead of deleting them 

    is_outlier = Column(Integer, nullable=False, default=0)
    outlier_reasons = Column(Text, nullable=True)

    # Denormalized pickup/dropoff labels added by the ETL for fast filtering
    pickup_borough = Column(String, nullable=True)
    pickup_zone = Column(String, nullable=True)
    pickup_service_zone = Column(String, nullable=True)
    dropoff_borough = Column(String, nullable=True)
    dropoff_zone = Column(String, nullable=True)
    dropoff_service_zone = Column(String, nullable=True)

    # The database stores trip_duration_minutes and average_speed_mph. These are not raw fields from the dataset but are calculated during the ETL cleaning step for easier filtering
    trip_duration_minutes = Column(Float, nullable=True)
    average_speed_mph = Column(Float, nullable=True)
    fare_per_mile = Column(Float, nullable=True)
    pickup_hour = Column(Integer, nullable=True)
    pickup_day_of_week = Column(String, nullable=True)
    tip_percentage = Column(Float, nullable=True)

    # Relationship to the pickup location row in locations.
    pickup_location = relationship(
        "Location",
        back_populates="pickup_trips",
        foreign_keys=[pu_location_id],
    )

    # Relationship to the dropoff location row in locations.
    dropoff_location = relationship(
        "Location",
        back_populates="dropoff_trips",
        foreign_keys=[do_location_id],
    )
