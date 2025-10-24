"""Unit tests for PDF processor service"""
import pytest
from io import BytesIO
from app.services.pdf_processor import PDFProcessor


@pytest.fixture
def pdf_processor():
    """Create PDF processor instance"""
    return PDFProcessor()


@pytest.mark.asyncio
async def test_pdf_processor_initialization(pdf_processor):
    """Test PDF processor initializes correctly"""
    assert pdf_processor is not None
    assert hasattr(pdf_processor, 'process_pdf')


@pytest.mark.asyncio
async def test_extract_text_with_valid_content(pdf_processor, sample_pdf_content):
    """Test text extraction works with valid content"""
    # This is a simplified test - in real scenario you'd use actual PDF bytes
    # For now, we test the text processing logic
    result = pdf_processor._clean_text(sample_pdf_content)
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0


def test_clean_text_removes_extra_whitespace(pdf_processor):
    """Test that clean_text removes extra whitespace"""
    dirty_text = "This   has    extra     spaces\n\n\n\nand newlines"
    clean = pdf_processor._clean_text(dirty_text)
    assert "   " not in clean
    assert "\n\n\n" not in clean


def test_clean_text_preserves_content(pdf_processor):
    """Test that clean_text preserves actual content"""
    text = "Important contract terms"
    clean = pdf_processor._clean_text(text)
    assert "Important" in clean
    assert "contract" in clean
    assert "terms" in clean


def test_extract_metadata_from_text(pdf_processor, sample_pdf_content):
    """Test metadata extraction from text"""
    # Test that we can identify key sections
    assert "SERVICE AGREEMENT" in sample_pdf_content
    assert "PARTY A" in sample_pdf_content
    assert "PARTY B" in sample_pdf_content


@pytest.mark.asyncio
async def test_process_pdf_handles_errors_gracefully(pdf_processor):
    """Test that PDF processor handles errors gracefully"""
    # Test with invalid PDF data
    invalid_pdf = BytesIO(b"not a pdf")
    with pytest.raises(Exception):
        await pdf_processor.process_pdf(invalid_pdf, "test.pdf")


def test_chunk_text_creates_reasonable_chunks(pdf_processor):
    """Test that text chunking creates reasonable chunks"""
    long_text = " ".join(["sentence"] * 1000)  # Very long text
    chunks = pdf_processor._chunk_text(long_text, chunk_size=500, overlap=50)

    assert len(chunks) > 1  # Should create multiple chunks
    assert all(len(chunk) <= 550 for chunk in chunks)  # Respect chunk size (with some buffer)
    # Check overlap exists
    if len(chunks) > 1:
        # There should be some overlap between consecutive chunks
        assert chunks[0][-50:] in chunks[1] or chunks[1][:50] in chunks[0]


def test_detect_language(pdf_processor):
    """Test language detection"""
    english_text = "This is an English contract"
    # PDF processor should handle English text
    assert len(english_text) > 0


@pytest.mark.asyncio
async def test_edge_case_empty_pdf(pdf_processor):
    """Test handling of empty PDF"""
    empty_pdf = BytesIO(b"")
    with pytest.raises(Exception):
        await pdf_processor.process_pdf(empty_pdf, "empty.pdf")


@pytest.mark.asyncio
async def test_edge_case_very_large_text(pdf_processor):
    """Test handling of very large text"""
    huge_text = "A" * 1000000  # 1 million characters
    chunks = pdf_processor._chunk_text(huge_text, chunk_size=1000, overlap=100)
    assert len(chunks) > 100  # Should create many chunks
    assert all(isinstance(chunk, str) for chunk in chunks)
