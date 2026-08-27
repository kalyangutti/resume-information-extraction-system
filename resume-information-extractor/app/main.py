"""
Resume Information Extractor - FastAPI Application Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import resume

app = FastAPI(
    title="Resume Information Extractor",
    description=(
        "A REST API for extracting structured information from PDF and DOCX resumes "
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
# Routers
# ---------------------------------------------------------------------------
app.include_router(resume.router, prefix="/api/v1", tags=["Resume"])


# ---------------------------------------------------------------------------
# Health check / API Info
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
        },
    }


@app.get("/health", tags=["Health"])
async def health() -> dict:
    """Detailed health check."""
    return {"status": "healthy", "version": "1.0.0"}
