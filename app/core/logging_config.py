"""Logging configuration with PII redaction"""
import logging
import re
from typing import Any


class PIIRedactionFilter(logging.Filter):
    """
    Filter that redacts PII from log messages
    Redacts: emails, phone numbers, SSNs, credit cards, API keys
    """

    # Regex patterns for PII detection
    PATTERNS = {
        'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        'phone': r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
        'api_key': r'\b[A-Za-z0-9]{32,}\b',  # Generic API key pattern
        'openai_key': r'sk-[A-Za-z0-9]{48}',
        'jwt': r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*',
    }

    REPLACEMENTS = {
        'email': '[EMAIL_REDACTED]',
        'phone': '[PHONE_REDACTED]',
        'ssn': '[SSN_REDACTED]',
        'credit_card': '[CARD_REDACTED]',
        'api_key': '[API_KEY_REDACTED]',
        'openai_key': '[OPENAI_KEY_REDACTED]',
        'jwt': '[JWT_REDACTED]',
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Redact PII from log record
        """
        if hasattr(record, 'msg'):
            record.msg = self.redact_pii(str(record.msg))

        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                self.redact_pii(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )

        return True

    def redact_pii(self, text: str) -> str:
        """
        Redact PII from text using regex patterns
        """
        for pii_type, pattern in self.PATTERNS.items():
            replacement = self.REPLACEMENTS[pii_type]
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        return text


def setup_logging(log_level: str = "INFO") -> None:
    """
    Setup logging configuration with PII redaction
    """
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.addFilter(PIIRedactionFilter())

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)

    # Also apply to uvicorn loggers
    for logger_name in ['uvicorn', 'uvicorn.access', 'uvicorn.error']:
        logger = logging.getLogger(logger_name)
        logger.addFilter(PIIRedactionFilter())


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with PII redaction
    """
    logger = logging.getLogger(name)
    logger.addFilter(PIIRedactionFilter())
    return logger


# Example usage
if __name__ == "__main__":
    setup_logging("INFO")
    logger = get_logger(__name__)

    # Test PII redaction
    logger.info("User email: john.doe@example.com")
    logger.info("Phone number: 555-123-4567")
    logger.info("SSN: 123-45-6789")
    logger.info("Credit card: 1234-5678-9012-3456")
    logger.info("API key: sk-ABCdefGHIjklMNOpqrsTUVwxyzABCdefGHIjklMNOpqr")

    # Should output [EMAIL_REDACTED], [PHONE_REDACTED], etc.
