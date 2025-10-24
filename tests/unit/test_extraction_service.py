"""Unit tests for extraction service"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app.services.extraction_service import ExtractionService


@pytest.fixture
def extraction_service():
    """Create extraction service instance"""
    return ExtractionService()


@pytest.mark.asyncio
async def test_extraction_service_initialization(extraction_service):
    """Test extraction service initializes correctly"""
    assert extraction_service is not None
    assert hasattr(extraction_service, 'extract')


@pytest.mark.asyncio
async def test_rule_based_extraction(extraction_service, sample_pdf_content):
    """Test rule-based extraction without LLM"""
    result = extraction_service._rule_based_extraction(sample_pdf_content)

    assert result is not None
    assert isinstance(result, dict)
    assert 'parties' in result
    assert 'effective_date' in result
    assert 'term' in result


def test_extract_parties(extraction_service, sample_pdf_content):
    """Test party extraction from text"""
    parties = extraction_service._extract_parties(sample_pdf_content)

    assert isinstance(parties, list)
    assert len(parties) >= 2
    assert any("TechCorp" in party for party in parties)
    assert any("ServiceProvider" in party for party in parties)


def test_extract_date(extraction_service, sample_pdf_content):
    """Test date extraction from text"""
    date = extraction_service._extract_date(sample_pdf_content, "effective")

    assert date is not None
    assert isinstance(date, str)
    # Should find January 1, 2024 in some format
    assert "2024" in date or "January" in date or "01" in date


def test_extract_term(extraction_service, sample_pdf_content):
    """Test term extraction"""
    term = extraction_service._extract_term(sample_pdf_content)

    assert term is not None
    assert isinstance(term, str)
    assert "24" in term or "months" in term.lower()


def test_extract_governing_law(extraction_service, sample_pdf_content):
    """Test governing law extraction"""
    law = extraction_service._extract_governing_law(sample_pdf_content)

    assert law is not None
    assert "California" in law


def test_extract_payment_terms(extraction_service, sample_pdf_content):
    """Test payment terms extraction"""
    payment = extraction_service._extract_payment_terms(sample_pdf_content)

    assert payment is not None
    assert "$10,000" in payment or "10000" in payment
    assert "monthly" in payment.lower() or "30 days" in payment


def test_extract_liability_cap(extraction_service, sample_pdf_content):
    """Test liability cap extraction"""
    liability = extraction_service._extract_liability_cap(sample_pdf_content)

    assert liability is not None
    assert 'amount' in liability or 'description' in liability


def test_extract_signatories(extraction_service, sample_pdf_content):
    """Test signatory extraction"""
    signatories = extraction_service._extract_signatories(sample_pdf_content)

    assert isinstance(signatories, list)
    assert len(signatories) >= 2

    # Check structure
    for signatory in signatories:
        assert 'name' in signatory
        assert 'title' in signatory


@pytest.mark.asyncio
async def test_extract_with_llm_fallback(extraction_service, sample_pdf_content):
    """Test extraction falls back to rules when LLM fails"""
    with patch.object(extraction_service, '_llm_extraction', side_effect=Exception("LLM failed")):
        result = await extraction_service.extract(sample_pdf_content, use_llm=True)

        # Should fall back to rule-based
        assert result is not None
        assert isinstance(result, dict)


@pytest.mark.asyncio
async def test_extract_handles_empty_text(extraction_service):
    """Test extraction handles empty text gracefully"""
    result = extraction_service._rule_based_extraction("")

    assert result is not None
    assert isinstance(result, dict)
    # Should return empty/null values
    assert result['parties'] == []


def test_extract_handles_malformed_text(extraction_service):
    """Test extraction handles malformed text"""
    malformed = "asdfkj asldkfj laskdjf laksdjf"
    result = extraction_service._rule_based_extraction(malformed)

    assert result is not None
    assert isinstance(result, dict)
    # Should have empty values but not crash


def test_date_normalization(extraction_service):
    """Test date normalization to ISO format"""
    dates = [
        "January 1, 2024",
        "01/01/2024",
        "2024-01-01",
        "Jan 1, 2024"
    ]

    for date_str in dates:
        normalized = extraction_service._normalize_date(date_str)
        # Should return ISO format or original if can't parse
        assert normalized is not None
        assert isinstance(normalized, str)


def test_currency_extraction(extraction_service):
    """Test currency extraction from payment terms"""
    text = "Payment of $5,000 USD per month"
    payment = extraction_service._extract_payment_terms(text)

    assert "5000" in payment or "5,000" in payment
    assert "USD" in payment or "month" in payment.lower()


@pytest.mark.asyncio
async def test_edge_case_multiple_dates(extraction_service):
    """Test extraction when multiple dates present"""
    text = """
    Effective Date: January 1, 2024
    Termination Date: December 31, 2025
    Signed on: February 15, 2024
    """

    effective_date = extraction_service._extract_date(text, "effective")
    assert "January" in effective_date or "01" in effective_date or "2024" in effective_date
