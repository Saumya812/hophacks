"""
FindMyPal FastAPI application entrypoint.

Run locally:
    cd backend
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

Interactive docs: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from routers import persons, search, sightings

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

# Allow the React frontend (Vite default :5173) to call this API in development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount route modules — paths match the project spec exactly.
app.include_router(persons.router)
app.include_router(sightings.router)
app.include_router(search.router)


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
