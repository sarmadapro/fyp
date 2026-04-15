"""
Document management API routes.
Handles file upload, deletion, and status queries.
"""

import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.core.config import settings
from app.models.schemas import DocumentStatus, DocumentUploadResponse, DocumentDeleteResponse
from app.services.document_service import document_service
from app.services.chat_service import invalidate_domain_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/document", tags=["Document"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.get("/status", response_model=DocumentStatus)
async def get_document_status():
    """Check if a document is currently loaded and get its metadata."""
    return DocumentStatus(
        has_document=document_service.has_document,
        document_name=document_service.document_name,
        document_type=document_service.document_type,
        chunk_count=document_service.chunk_count,
    )


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document (PDF, DOCX, or TXT) for RAG processing.
    Only one document is allowed at a time — uploading a new one replaces the old.
    """
    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{file_ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)} MB.",
        )

    # Delete existing document if any
    if document_service.has_document:
        document_service.delete_document()
        logger.info("Deleted existing document before uploading new one.")

    # Save file to upload directory
    file_path = settings.UPLOAD_DIR / file.filename
    file_path.write_bytes(content)

    try:
        # Process and index the document
        chunk_count = document_service.process_and_index(file_path, file.filename, file_ext)

        # Invalidate domain summary cache so it re-analyzes the new document
        invalidate_domain_cache()

        return DocumentUploadResponse(
            message="Document uploaded and indexed successfully.",
            document_name=file.filename,
            chunk_count=chunk_count,
        )
    except ValueError as e:
        # Clean up on failure
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Clean up on failure
        if file_path.exists():
            file_path.unlink()
        logger.error(f"Document processing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process document.")


@router.delete("/delete", response_model=DocumentDeleteResponse)
async def delete_document():
    """Delete the currently loaded document and its index."""
    if not document_service.has_document:
        raise HTTPException(status_code=404, detail="No document is currently loaded.")

    document_service.delete_document()
    invalidate_domain_cache()
    return DocumentDeleteResponse(message="Document deleted successfully.")
