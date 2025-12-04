import logging
from unittest.mock import patch

from dynafield.logger.logger_config import setup_logging, get_logger, ColorFormatter, LogFilter
import pytest


def test_setup_logging():
    """Test basic logging setup."""
    setup_logging(level="DEBUG", format_type="simple", enable_colors=False)
    
    logger = get_logger("test")
    logger.info("Test message")
    
    assert logger.root.level == logging.DEBUG


def test_color_formatter():
    """Test color formatter."""
    formatter = ColorFormatter("%(levelname)s %(message)s", use_colors=True)
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    
    formatted = formatter.format(record)
    assert "INFO" in formatted
    assert "Test message" in formatted


def test_log_filter():
    """Test log filter adds service name."""
    log_filter = LogFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test",
        args=(),
        exc_info=None,
    )
    
    with patch.dict("os.environ", {"SERVICE_NAME": "test-service"}):
        result = log_filter.filter(record)
        assert result is True
        assert hasattr(record, "service_name")
        assert record.service_name == "test-service"


def test_get_logger():
    """Test getting logger with name."""
    logger = get_logger("custom_name")
    assert logger.name == "custom_name"
    
    default_logger = get_logger()
    assert default_logger.name == "app"


if __name__ == "__main__":
    pytest.main([__file__])