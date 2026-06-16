from fastapi import FastAPI
from backend.routes import trips, locations, suspicious_records

app = FastAPI(
    title="Urban Mobility Data Explorer",
    version="1.0.0"
)

app.include_router(trips.router)
app.include_router(locations.router)
app.include_router(suspicious_records.router)

@app.get("/")
def root():
    return {
        "message": "Urban Mobility Data Explorer API"
    }