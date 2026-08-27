"""
Resume router.

Handles:
1. Multipart file upload
2. File validation (type, size, emptiness)
3. Delegating to the extraction service
4. Returning the validated JSON response
5. HTTP error responses for all edge cases

Extraction logic is NOT implemented here.
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.schemas.resume import ResumeResponse
from app.services.file_parser import (
    CorruptedFileError,
    EmptyFileError,
    FileParseError,
    UnsupportedFileTypeError,
    extract_text_from_file,
    validate_file_extension,
)
from app.services.resume_extractor import extract_resume_data, extract_resume_data_from_file

router = APIRouter()

# Maximum file size: 10 MB
_MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024


@router.post(
    "/resume/extract",
    response_model=ResumeResponse,
    summary="Extract structured information from a resume",
    description=(
        "Upload a PDF or DOCX resume file. "
        "Returns structured JSON with name, email, phone, skills, education, "
        "experience, LinkedIn, and GitHub profile. "
        "Extraction is completely rule-based — no resume content is sent to any external AI service."
    ),
    responses={
        200: {"description": "Extraction successful."},
        400: {"description": "Invalid file type, empty file, or corrupted file."},
        422: {"description": "Validation error in the request."},
        500: {"description": "Internal server error during extraction."},
    },
)
async def extract_resume(
    file: UploadFile = File(..., description="PDF or DOCX resume file"),
) -> ResumeResponse:
    """
    Extract structured information from an uploaded resume.

    Args:
        file: Uploaded resume file (PDF or DOCX).

    Returns:
        ResumeResponse with extracted fields.

    Raises:
        HTTPException 400: For unsupported types, empty files, or corrupted files.
        HTTPException 500: For unexpected extraction errors.
    """
    # --- Validate filename / extension ---
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided. Please upload a valid PDF or DOCX file.",
        )

    try:
        validate_file_extension(file.filename)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    # --- Read file bytes ---
    try:
        file_bytes = await file.read()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file: {exc}",
        ) from exc

    # --- Size check ---
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    if len(file_bytes) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File size ({len(file_bytes) / 1024 / 1024:.1f} MB) exceeds the "
                f"10 MB limit."
            ),
        )

    # --- Parse and extract ---
    try:
        raw_text = extract_text_from_file(file_bytes, file.filename)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except EmptyFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except CorruptedFileError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileParseError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error while parsing the file: {exc}",
        ) from exc

    try:
        result = extract_resume_data_from_file(
            file_bytes=file_bytes,
            filename=file.filename,
            raw_text=raw_text,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during information extraction: {exc}",
        ) from exc

    return result
