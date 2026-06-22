from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from backend.routes import trips, locations, suspicious_records, analytics

app = FastAPI(
    title="Urban Mobility Data Explorer",
    version="1.0.0"
)

app.add_middleware(
    # allow cors from any origin for simplicity and it will be  changed in the future when backend is on a different domain than frontend. --- IGNORE ---
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(trips.router)
app.include_router(locations.router)
app.include_router(suspicious_records.router)
app.include_router(analytics.router)

@app.get("/")
def root():
    return {
        "message": "Urban Mobility Data Explorer API"
    }
