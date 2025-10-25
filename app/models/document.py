"""Document database models"""
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class ProcessingStatus(str, enum.Enum):
    """Document processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class SeverityLevel(str, enum.Enum):
    """Audit finding severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Document(Base):
    """Document model for storing uploaded PDFs"""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, default="application/pdf")

    # Content
    text_content = Column(Text)
    page_count = Column(Integer)

    # Processing
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    extracted_data = relationship("ExtractedData", back_populates="document", uselist=False, cascade="all, delete-orphan")
    audit_findings = relationship("AuditFinding", back_populates="document", cascade="all, delete-orphan")


class ExtractedData(Base):
    """Extracted structured data from contracts"""
    __tablename__ = "extracted_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)

    # Extracted fields as per requirements
    parties = Column(ARRAY(String), default=list)
    effective_date = Column(String, nullable=True)
    term = Column(String, nullable=True)
    governing_law = Column(String, nullable=True)
    payment_terms = Column(Text, nullable=True)
    termination = Column(Text, nullable=True)
    auto_renewal = Column(String, nullable=True)
    confidentiality = Column(Text, nullable=True)
    indemnity = Column(Text, nullable=True)

    # Liability cap
    liability_cap_amount = Column(Float, nullable=True)
    liability_cap_currency = Column(String, nullable=True)

    # Signatories as JSON array of objects
    signatories = Column(JSON, default=list)  # [{"name": "...", "title": "..."}]

    # Metadata
    extraction_confidence = Column(Float, nullable=True)
    extraction_method = Column(String, default="llm")  # llm or rule-based

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    document = relationship("Document", back_populates="extracted_data")


class AuditFinding(Base):
    """Audit findings for risky clauses"""
    __tablename__ = "audit_findings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)

    # Finding details
    finding_type = Column(String, nullable=False)  # e.g., "auto_renewal_short_notice"
    description = Column(Text, nullable=False)
    severity = Column(Enum(SeverityLevel), nullable=False)

    # Evidence
    evidence_text = Column(Text, nullable=True)
    page_number = Column(Integer, nullable=True)
    char_start = Column(Integer, nullable=True)
    char_end = Column(Integer, nullable=True)

    # Additional context
    recommendation = Column(Text, nullable=True)
    finding_metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    document = relationship("Document", back_populates="audit_findings")
