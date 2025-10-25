"""Document ingestion endpoint"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import os
import uuid
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.models.schemas import IngestResponse
from app.models.document import Document, ProcessingStatus
from app.services.pdf_processor import PDFProcessor
from app.api.admin import increment_metric
from app.api.webhook import send_webhook_event

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_documents(
    files: List[UploadFile] = File(..., description="PDF files to ingest"),
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest one or more PDF documents

    - **files**: List of PDF files to upload
    - Returns list of document IDs for uploaded files
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided"
        )

    # Create upload directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

    document_ids = []
    pdf_processor = PDFProcessor()

    for file in files:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File {file.filename} is not a PDF"
            )

        # Validate file size
        file.file.seek(0, 2)  # Seek to end
        file_size = file.file.tell()
        file.file.seek(0)  # Reset to beginning

        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File {file.filename} exceeds maximum size of {settings.MAX_FILE_SIZE} bytes"
            )

        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{file_id}{file_extension}"
        file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

        # Save file to disk
        try:
            with open(file_path, "wb") as f:
                content = await file.read()
                f.write(content)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error saving file {file.filename}: {str(e)}"
            )

        # Extract text from PDF
        try:
            text_content, page_count = pdf_processor.extract_text(file_path)
            processing_status = ProcessingStatus.COMPLETED
            error_message = None
            processed_at = datetime.utcnow()
        except Exception as e:
            # If extraction fails, still save the document but mark as failed
            text_content = None
            page_count = None
            processing_status = ProcessingStatus.FAILED
            error_message = str(e)
            processed_at = None

        # Create document record in database
        document = Document(
            id=uuid.UUID(file_id),
            filename=file.filename,
            file_path=file_path,
            file_size=file_size,
            mime_type="application/pdf",
            text_content=text_content,
            page_count=page_count,
            status=processing_status,
            error_message=error_message,
            processed_at=processed_at
        )

        db.add(document)
        document_ids.append(file_id)

    # Commit all documents to database
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error saving documents to database: {str(e)}"
        )

    # Increment metrics and trigger webhooks for each document
    for doc_id in document_ids:
        increment_metric("documents_ingested")
        # Trigger webhook event
        await send_webhook_event(
            event_type="document.ingested",
            document_id=doc_id,
            data={
                "filename": files[document_ids.index(doc_id)].filename if document_ids.index(doc_id) < len(files) else "unknown",
                "status": "completed"
            }
        )

    return IngestResponse(
        document_ids=document_ids,
        total_files=len(document_ids),
        message=f"Successfully ingested {len(document_ids)} document(s)"
    )


@router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get document information by ID

    - **document_id**: UUID of the document
    """
    from sqlalchemy import select

    try:
        doc_uuid = uuid.UUID(document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )

    result = await db.execute(
        select(Document).where(Document.id == doc_uuid)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found"
        )

    return {
        "document_id": str(document.id),
        "filename": document.filename,
        "status": document.status,
        "page_count": document.page_count,
        "file_size": document.file_size,
        "created_at": document.created_at,
        "processed_at": document.processed_at,
        "error_message": document.error_message
    }
