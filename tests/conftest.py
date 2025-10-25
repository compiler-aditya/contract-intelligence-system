"""Pytest configuration and fixtures"""
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.database import Base
from app.main import app
from app.core.database import get_db


# Test database URL (using in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=NullPool,
    echo=False
)

# Create test session maker
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test"""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async with TestSessionLocal() as session:
        yield session

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def test_app():
    """Create test app"""
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def sample_pdf_content():
    """Sample PDF text content for testing"""
    return """
    SERVICE AGREEMENT

    This Service Agreement ("Agreement") is entered into as of January 1, 2024
    ("Effective Date") by and between:

    PARTY A: TechCorp Inc., a Delaware corporation ("Client")
    PARTY B: ServiceProvider LLC, a California LLC ("Provider")

    1. TERM
    This Agreement shall commence on the Effective Date and continue for a period
    of 24 months ("Initial Term"), unless terminated earlier in accordance with
    Section 5.

    2. PAYMENT TERMS
    Client shall pay Provider a monthly fee of $10,000 USD, payable within 30 days
    of invoice date.

    3. CONFIDENTIALITY
    Both parties agree to maintain confidentiality of all proprietary information
    disclosed during the term of this Agreement.

    4. INDEMNIFICATION
    Each party shall indemnify the other against any claims arising from their
    breach of this Agreement.

    5. LIABILITY CAP
    In no event shall either party's liability exceed the total fees paid in the
    12 months preceding the claim.

    6. TERMINATION
    Either party may terminate this Agreement with 60 days written notice.

    7. AUTO-RENEWAL
    This Agreement shall automatically renew for successive 12-month periods
    unless either party provides written notice of non-renewal at least 90 days
    before the end of the then-current term.

    8. GOVERNING LAW
    This Agreement shall be governed by the laws of the State of California.

    SIGNATURES:

    John Smith, CEO
    TechCorp Inc.
    Date: January 1, 2024

    Jane Doe, President
    ServiceProvider LLC
    Date: January 1, 2024
    """


@pytest.fixture
def sample_document_data():
    """Sample document data for testing"""
    return {
        "filename": "test_contract.pdf",
        "file_size": 102400,
        "page_count": 5,
        "text_content": "Sample contract text...",
    }


@pytest.fixture
def sample_extraction_data():
    """Sample extraction result for testing"""
    return {
        "parties": ["TechCorp Inc.", "ServiceProvider LLC"],
        "effective_date": "2024-01-01",
        "term": "24 months",
        "governing_law": "State of California",
        "payment_terms": "$10,000 USD monthly, payable within 30 days",
        "termination": "60 days written notice",
        "auto_renewal": "Automatically renews for 12-month periods with 90 days notice",
        "confidentiality": "Both parties maintain confidentiality of proprietary information",
        "indemnity": "Mutual indemnification for breach",
        "liability_cap": {
            "amount": 120000,
            "currency": "USD",
            "description": "Total fees paid in preceding 12 months"
        },
        "signatories": [
            {"name": "John Smith", "title": "CEO"},
            {"name": "Jane Doe", "title": "President"}
        ]
    }
