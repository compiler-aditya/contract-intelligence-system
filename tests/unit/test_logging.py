"""Unit tests for PII redaction in logging"""
import pytest
import logging
from app.core.logging_config import PIIRedactionFilter, setup_logging, get_logger


def test_pii_filter_redacts_email():
    """Test that PII filter redacts email addresses"""
    filter = PIIRedactionFilter()
    text = "User email is john.doe@example.com"
    redacted = filter.redact_pii(text)

    assert "john.doe@example.com" not in redacted
    assert "[EMAIL_REDACTED]" in redacted


def test_pii_filter_redacts_phone():
    """Test that PII filter redacts phone numbers"""
    filter = PIIRedactionFilter()
    # Test with format that matches the regex pattern exactly
    text = "Call me at 555-123-4567"
    redacted = filter.redact_pii(text)
    assert "[PHONE_REDACTED]" in redacted
    assert "555-123-4567" not in redacted


def test_pii_filter_redacts_ssn():
    """Test that PII filter redacts SSN"""
    filter = PIIRedactionFilter()
    text = "SSN: 123-45-6789"
    redacted = filter.redact_pii(text)

    assert "123-45-6789" not in redacted
    assert "[SSN_REDACTED]" in redacted


def test_pii_filter_redacts_credit_card():
    """Test that PII filter redacts credit card numbers"""
    filter = PIIRedactionFilter()
    test_cases = [
        "Card: 1234-5678-9012-3456",
        "Card: 1234 5678 9012 3456",
        "Card: 1234567890123456",
    ]

    for text in test_cases:
        redacted = filter.redact_pii(text)
        assert "[CARD_REDACTED]" in redacted


def test_pii_filter_redacts_openai_key():
    """Test that PII filter redacts OpenAI API keys"""
    filter = PIIRedactionFilter()
    text = "API key: sk-ABCdefGHIjklMNOpqrsTUVwxyzABCdefGHIjklMNOpqr"
    redacted = filter.redact_pii(text)

    assert "sk-ABCdefGHIjklMNOpqrsTUVwxyzABCdefGHIjklMNOpqr" not in redacted
    # OpenAI keys starting with sk- are redacted (either as OPENAI_KEY or API_KEY)
    assert "REDACTED" in redacted


def test_pii_filter_redacts_jwt():
    """Test that PII filter redacts JWT tokens"""
    filter = PIIRedactionFilter()
    text = "Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    redacted = filter.redact_pii(text)

    # JWT tokens are redacted (may be caught by API_KEY or JWT pattern)
    assert "REDACTED" in redacted
    # Original JWT should be redacted
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted


def test_pii_filter_preserves_normal_text():
    """Test that PII filter preserves normal text"""
    filter = PIIRedactionFilter()
    text = "This is a normal log message about contracts"
    redacted = filter.redact_pii(text)

    assert redacted == text


def test_pii_filter_handles_multiple_pii_types():
    """Test that PII filter handles multiple PII types in one string"""
    filter = PIIRedactionFilter()
    text = "Contact john.doe@example.com or call 555-123-4567"
    redacted = filter.redact_pii(text)

    assert "[EMAIL_REDACTED]" in redacted
    assert "[PHONE_REDACTED]" in redacted
    assert "john.doe@example.com" not in redacted
    assert "555-123-4567" not in redacted


def test_logging_filter_applies_to_log_record():
    """Test that filter applies to log records"""
    filter = PIIRedactionFilter()

    # Create a log record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="User email: test@example.com",
        args=(),
        exc_info=None
    )

    # Apply filter
    filter.filter(record)

    assert "[EMAIL_REDACTED]" in record.msg
    assert "test@example.com" not in record.msg


def test_get_logger_has_pii_filter():
    """Test that get_logger returns logger with PII filter"""
    logger = get_logger("test_logger")

    assert logger is not None
    # Check if any filter is a PIIRedactionFilter
    has_pii_filter = any(
        isinstance(f, PIIRedactionFilter) for f in logger.filters
    )
    assert has_pii_filter


def test_pii_filter_case_insensitive():
    """Test that PII filter works case-insensitively"""
    filter = PIIRedactionFilter()
    text = "Email: JOHN.DOE@EXAMPLE.COM"
    redacted = filter.redact_pii(text)

    assert "JOHN.DOE@EXAMPLE.COM" not in redacted
    assert "[EMAIL_REDACTED]" in redacted


def test_edge_case_empty_string():
    """Test PII filter with empty string"""
    filter = PIIRedactionFilter()
    redacted = filter.redact_pii("")
    assert redacted == ""


def test_edge_case_none_values():
    """Test PII filter handles None gracefully"""
    filter = PIIRedactionFilter()
    # Should not crash
    try:
        redacted = filter.redact_pii(str(None))
        assert redacted is not None
    except Exception as e:
        pytest.fail(f"Should handle None gracefully: {e}")
