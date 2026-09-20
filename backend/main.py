"""
FindMyPal FastAPI application entrypoint.

Run locally:
    cd backend
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Interactive docs: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from database import DatabaseError, get_database
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import features, intelligence, lookup_router, persons, search, sightings

settings = get_settings()

app = FastAPI(
    title="FindMyPal API",
    description=(
        "Missing-persons platform API. "
        "Creates profiles, accepts sightings/tips, and supports Gemini-powered "
        "natural-language search. Auth is mocked in v1."
    ),
    version="0.1.0",
)

# Allow the React frontend (Vite :5173/:5174, etc.) to call this API in development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=(
        r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"
        r"|https://[a-z0-9-]+\.trycloudflare\.com$"
        r"|https://[a-z0-9-]+\.ngrok-free\.app$"
        r"|https://[a-z0-9-]+\.ngrok\.io$"
        r"|https://(www\.)?findmypal\.us$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules — paths match the project spec exactly.
app.include_router(persons.router)
app.include_router(sightings.router)
app.include_router(search.router)
app.include_router(lookup_router.router)
app.include_router(intelligence.router)
app.include_router(features.router)


@app.get("/", tags=["health"])
def root():
    """Simple health / info endpoint."""
    return {
        "app": "FindMyPal",
        "status": "ok",
        "docs": "/docs",
        "mock_user": {
            "id": settings.mock_user_id,
            "email": settings.mock_user_email,
        },
    }


@app.get("/health", tags=["health"])
def health():
    """Liveness check for DigitalOcean / load balancers."""
    return {"status": "healthy"}


@app.exception_handler(DatabaseError)
async def database_error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.get("/health/database", tags=["health"])
def database_health():
    get_database().table("persons").select("id").limit(1).execute()
    return {"status": "healthy", "database": "spacetimedb"}
