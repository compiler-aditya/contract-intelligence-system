"""Contract audit endpoint"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.core.database import get_db
from app.models.schemas import AuditRequest, AuditResponse, AuditFinding as AuditFindingSchema
from app.models.document import Document, AuditFinding, ProcessingStatus, SeverityLevel
from app.services.audit_service import AuditService
from app.api.admin import increment_metric
from app.api.webhook import send_webhook_event

router = APIRouter()


@router.post("/audit", response_model=AuditResponse)
async def audit_contract(
    request: AuditRequest,
    use_llm: bool = Query(True, description="Use LLM audit (True) or rule-based (False)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Audit a contract for risky clauses

    - **document_id**: UUID of the document to audit
    - **use_llm**: Toggle between LLM and rule-based audit
    - Returns list of findings with severity, evidence, and recommendations
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
            detail=f"Document is not ready for audit. Status: {document.status}"
        )

    if not document.text_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document has no text content"
        )

    # Perform audit
    audit_service = AuditService()
    try:
        findings = audit_service.audit(
            text=document.text_content,
            use_llm=use_llm
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audit failed: {str(e)}"
        )

    # Calculate risk score
    risk_score = audit_service.calculate_risk_score(findings)

    # Delete existing audit findings for this document
    await db.execute(
        select(AuditFinding).where(AuditFinding.document_id == doc_uuid)
    )

    # Save findings to database
    for finding in findings:
        audit_finding = AuditFinding(
            document_id=doc_uuid,
            finding_type=finding.get("finding_type", "unknown"),
            description=finding.get("description", ""),
            severity=SeverityLevel(finding.get("severity", "medium")),
            evidence_text=finding.get("evidence_text"),
            recommendation=finding.get("recommendation")
        )
        db.add(audit_finding)

    await db.commit()

    # Increment metrics
    increment_metric("audits_completed")

    # Trigger webhook event
    await send_webhook_event(
        event_type="audit.completed",
        document_id=request.document_id,
        data={
            "audit_method": "llm" if use_llm else "rule-based",
            "total_findings": len(findings),
            "risk_score": risk_score,
            "status": "completed"
        }
    )

    # Build response
    formatted_findings = [
        AuditFindingSchema(
            finding_type=f.get("finding_type"),
            description=f.get("description"),
            severity=SeverityLevel(f.get("severity", "medium")),
            evidence_text=f.get("evidence_text"),
            recommendation=f.get("recommendation")
        )
        for f in findings
    ]

    return AuditResponse(
        document_id=request.document_id,
        findings=formatted_findings,
        total_findings=len(formatted_findings),
        risk_score=risk_score
    )
