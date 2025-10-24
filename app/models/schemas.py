"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID
from enum import Enum


class ProcessingStatus(str, Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SeverityLevel(str, Enum):
    """Audit finding severity"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Ingest Schemas
class IngestResponse(BaseModel):
    """Response for document ingestion"""
    document_ids: List[str] = Field(..., description="List of uploaded document IDs")
    total_files: int = Field(..., description="Total number of files uploaded")
    message: str = Field(default="Documents ingested successfully")


# Extract Schemas
class Signatory(BaseModel):
    """Signatory information"""
    name: str
    title: str


class ExtractRequest(BaseModel):
    """Request for data extraction"""
    document_id: str = Field(..., description="Document ID to extract data from")


class ExtractResponse(BaseModel):
    """Response for extracted data"""
    document_id: str
    parties: List[str] = Field(default_factory=list)
    effective_date: Optional[str] = None
    term: Optional[str] = None
    governing_law: Optional[str] = None
    payment_terms: Optional[str] = None
    termination: Optional[str] = None
    auto_renewal: Optional[str] = None
    confidentiality: Optional[str] = None
    indemnity: Optional[str] = None
    liability_cap: Optional[dict] = Field(
        default=None,
        description="Liability cap with 'amount' and 'currency' keys"
    )
    signatories: List[Signatory] = Field(default_factory=list)


# Ask (RAG) Schemas
class Citation(BaseModel):
    """Citation from document"""
    document_id: str
    page: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    text: str = Field(..., description="Cited text from document")


class AskRequest(BaseModel):
    """Request for RAG question answering"""
    question: str = Field(..., description="Question to ask about the contracts")
    document_ids: Optional[List[str]] = Field(
        default=None,
        description="Specific document IDs to search in (optional)"
    )


class AskResponse(BaseModel):
    """Response for RAG question answering"""
    answer: str = Field(..., description="Answer to the question")
    citations: List[Citation] = Field(default_factory=list, description="Citations supporting the answer")
    confidence: Optional[float] = Field(default=None, description="Confidence score")


# Audit Schemas
class AuditRequest(BaseModel):
    """Request for contract audit"""
    document_id: str = Field(..., description="Document ID to audit")


class AuditFinding(BaseModel):
    """Individual audit finding"""
    finding_type: str = Field(..., description="Type of finding")
    description: str = Field(..., description="Description of the risk")
    severity: SeverityLevel = Field(..., description="Severity level")
    evidence_text: Optional[str] = Field(default=None, description="Evidence text from contract")
    page: Optional[int] = Field(default=None, description="Page number")
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    recommendation: Optional[str] = Field(default=None, description="Recommendation to mitigate risk")


class AuditResponse(BaseModel):
    """Response for contract audit"""
    document_id: str
    findings: List[AuditFinding] = Field(default_factory=list)
    total_findings: int
    risk_score: Optional[float] = Field(default=None, description="Overall risk score 0-100")


# Webhook Schemas
class WebhookEvent(BaseModel):
    """Webhook event payload"""
    event_type: str = Field(..., description="Type of event")
    document_id: str
    status: str
    timestamp: datetime
    data: Optional[dict] = None


class WebhookRequest(BaseModel):
    """Webhook configuration"""
    url: str = Field(..., description="Webhook URL to POST events to")
    events: List[str] = Field(
        default=["extraction_complete", "audit_complete"],
        description="Event types to subscribe to"
    )


# Health & Metrics Schemas
class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(default="healthy")
    version: str
    timestamp: datetime
    database: str = Field(default="connected")


class MetricsResponse(BaseModel):
    """Metrics response"""
    total_documents: int
    documents_processed: int
    documents_pending: int
    total_extractions: int
    total_audits: int
    uptime_seconds: float


# Document Info Schema
class DocumentInfo(BaseModel):
    """Document information"""
    document_id: str
    filename: str
    status: ProcessingStatus
    page_count: Optional[int] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
