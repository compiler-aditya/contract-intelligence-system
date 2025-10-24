"""Data extraction endpoint"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.core.database import get_db
from app.models.schemas import ExtractRequest, ExtractResponse
from app.models.document import Document, ExtractedData, ProcessingStatus
from app.services.extraction_service import ExtractionService

router = APIRouter()


@router.post("/extract", response_model=ExtractResponse)
async def extract_data(
    request: ExtractRequest,
    use_llm: bool = Query(True, description="Use LLM extraction (True) or rule-based fallback (False)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Extract structured data from a contract document

    - **document_id**: UUID of the document to extract from
    - **use_llm**: Toggle between LLM and rule-based extraction
    - Returns extracted fields: parties, dates, terms, liability, signatories, etc.
    """
    # Validate document ID
    try:
        doc_uuid = uuid.UUID(request.document_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document ID format"
        )

    # Get document from database
    result = await db.execute(
        select(Document).where(Document.id == doc_uuid)
    )
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {request.document_id} not found"
        )

    # Check if document was successfully processed
    if document.status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Document is not ready for extraction. Status: {document.status}"
        )

    if not document.text_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no text content"
        )

    # Extract data
    extraction_service = ExtractionService()
    try:
        extracted_fields = extraction_service.extract(
            text=document.text_content,
            use_llm=use_llm
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction failed: {str(e)}"
        )

    # Check if extracted data already exists
    existing_result = await db.execute(
        select(ExtractedData).where(ExtractedData.document_id == doc_uuid)
    )
    existing_data = existing_result.scalar_one_or_none()

    if existing_data:
        # Update existing extraction
        existing_data.parties = extracted_fields.get("parties", [])
        existing_data.effective_date = extracted_fields.get("effective_date")
        existing_data.term = extracted_fields.get("term")
        existing_data.governing_law = extracted_fields.get("governing_law")
        existing_data.payment_terms = extracted_fields.get("payment_terms")
        existing_data.termination = extracted_fields.get("termination")
        existing_data.auto_renewal = extracted_fields.get("auto_renewal")
        existing_data.confidentiality = extracted_fields.get("confidentiality")
        existing_data.indemnity = extracted_fields.get("indemnity")
        existing_data.liability_cap_amount = extracted_fields.get("liability_cap_amount")
        existing_data.liability_cap_currency = extracted_fields.get("liability_cap_currency")
        existing_data.signatories = extracted_fields.get("signatories", [])
        existing_data.extraction_method = "llm" if use_llm else "rule-based"
    else:
        # Create new extraction record
        extracted_data = ExtractedData(
            document_id=doc_uuid,
            parties=extracted_fields.get("parties", []),
            effective_date=extracted_fields.get("effective_date"),
            term=extracted_fields.get("term"),
            governing_law=extracted_fields.get("governing_law"),
            payment_terms=extracted_fields.get("payment_terms"),
            termination=extracted_fields.get("termination"),
            auto_renewal=extracted_fields.get("auto_renewal"),
            confidentiality=extracted_fields.get("confidentiality"),
            indemnity=extracted_fields.get("indemnity"),
            liability_cap_amount=extracted_fields.get("liability_cap_amount"),
            liability_cap_currency=extracted_fields.get("liability_cap_currency"),
            signatories=extracted_fields.get("signatories", []),
            extraction_method="llm" if use_llm else "rule-based"
        )
        db.add(extracted_data)

    await db.commit()

    # Build response
    liability_cap = None
    if extracted_fields.get("liability_cap_amount") is not None:
        liability_cap = {
            "amount": extracted_fields.get("liability_cap_amount"),
            "currency": extracted_fields.get("liability_cap_currency", "USD")
        }

    return ExtractResponse(
        document_id=request.document_id,
        parties=extracted_fields.get("parties", []),
        effective_date=extracted_fields.get("effective_date"),
        term=extracted_fields.get("term"),
        governing_law=extracted_fields.get("governing_law"),
        payment_terms=extracted_fields.get("payment_terms"),
        termination=extracted_fields.get("termination"),
        auto_renewal=extracted_fields.get("auto_renewal"),
        confidentiality=extracted_fields.get("confidentiality"),
        indemnity=extracted_fields.get("indemnity"),
        liability_cap=liability_cap,
        signatories=extracted_fields.get("signatories", [])
    )
