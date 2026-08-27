"""
Resume Information Extractor - FastAPI Application Entry Point
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.routers import resume

app = FastAPI(
    title="Resume Information Extractor",
    description=(
        "A production-quality API for extracting structured information from PDF and DOCX resumes "
        "using rule-based techniques — no LLM or external AI services are used."
    ),
    version="1.0.0",
    contact={
        "name": "Resume Extractor API",
    },
    license_info={
        "name": "MIT",
    },
)

# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Static files (Web UI)
# ---------------------------------------------------------------------------
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(resume.router, prefix="/api/v1", tags=["Resume"])


# ---------------------------------------------------------------------------
# Web UI  — serve index.html at root
# ---------------------------------------------------------------------------
@app.get("/ui", tags=["UI"], include_in_schema=False)
async def serve_ui() -> FileResponse:
    """Serve the resume extractor web UI."""
    return FileResponse(str(_STATIC_DIR / "index.html"))


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
async def root() -> dict:
    """Health check / API info endpoint."""
    return {
        "status": "ok",
        "message": "Resume Information Extractor API is running.",
        "endpoints": {
            "extract": "POST /api/v1/resume/extract",
            "docs":    "/docs",
            "redoc":   "/redoc",
            "web_ui":  "/ui",
        },
    }


@app.get("/health", tags=["Health"])
async def health() -> dict:
    """Detailed health check."""
    return {"status": "healthy", "version": "1.0.0"}
