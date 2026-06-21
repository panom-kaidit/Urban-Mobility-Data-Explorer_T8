from sqlalchemy import Column, Float, Integer, String, Text

from backend.models.location import Base


class SuspiciousRecord(Base):
    """Represents a raw taxi trip record that was rejected by the cleaning step of the ETL pipeline.
    """

    __tablename__ = "suspicious_records"

    # Database-generated primary key for each rejected raw record.
    record_id = Column(Integer, primary_key=True, autoincrement=True)

    # Raw trip fields are nullable as bad or missing values can be the reason for this.
    # Because of the cleaning step, the following row was rejected:
    vendor_id = Column(Integer, nullable=True)
    pickup_datetime = Column(Text, nullable=True)
    dropoff_datetime = Column(Text, nullable=True)
    passenger_count = Column(Integer, nullable=True)
    trip_distance = Column(Float, nullable=True)
    rate_code_id = Column(Integer, nullable=True)
    store_and_fwd_flag = Column(String, nullable=True)
    pu_location_id = Column(Integer, nullable=True)
    do_location_id = Column(Integer, nullable=True)
    payment_type = Column(Integer, nullable=True)
    fare_amount = Column(Float, nullable=True)
    extra = Column(Float, nullable=True)
    mta_tax = Column(Float, nullable=True)
    tip_amount = Column(Float, nullable=True)
    tolls_amount = Column(Float, nullable=True)
    improvement_surcharge = Column(Float, nullable=True)
    total_amount = Column(Float, nullable=True)
    congestion_surcharge = Column(Float, nullable=True)
    airport_fee = Column(Float, nullable=True)

    # Cleaning metadata. removal_reason explains why the row was rejected.
    removal_reason = Column(Text, nullable=False)
    flagged_at = Column(Text, nullable=False)
