"""
Tests for utility modules.
"""

import pytest
import logging
from unittest.mock import patch, Mock
from src.utils.logging import (
    setup_logger, set_global_log_level, configure_debug_logging, 
    silence_external_loggers
)


class TestLogging:
    """Test logging utilities."""
    
    def test_setup_logger_default(self):
        """Test default logger setup."""
        logger = setup_logger("test_logger")
        assert logger.name == "test_logger"
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0
    
    def test_setup_logger_debug(self):
        """Test debug logger setup."""
        logger = setup_logger("test_debug", level=logging.DEBUG)
        assert logger.level == logging.DEBUG
    
    def test_setup_logger_custom_format(self):
        """Test logger setup with custom format."""
        custom_format = "%(name)s - %(message)s"
        logger = setup_logger("test_custom", format_string=custom_format)
        
        # Check that handler has the custom formatter
        assert len(logger.handlers) > 0
        handler = logger.handlers[0]
        assert handler.formatter._fmt == custom_format
    
    def test_setup_logger_no_timestamp(self):
        """Test logger setup without timestamp."""
        logger = setup_logger("test_no_timestamp", include_timestamp=False)
        
        # Check that handler doesn't include timestamp in format
        assert len(logger.handlers) > 0
        handler = logger.handlers[0]
        assert "%(asctime)s" not in handler.formatter._fmt
    
    def test_setup_logger_no_duplicate_handlers(self):
        """Test that setup_logger doesn't add duplicate handlers."""
        logger_name = "test_no_duplicate"
        
        # Setup logger twice
        logger1 = setup_logger(logger_name)
        logger2 = setup_logger(logger_name)
        
        # Should be the same logger with only one handler
        assert logger1 is logger2
        assert len(logger1.handlers) == 1
    
    def test_set_global_log_level(self):
        """Test setting global log level."""
        # Set to DEBUG level
        set_global_log_level(logging.DEBUG)
        
        # Check root logger level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    def test_configure_debug_logging(self):
        """Test configuring debug logging."""
        configure_debug_logging()
        
        # Check that root logger is set to DEBUG
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
    
    def test_silence_external_loggers(self):
        """Test silencing external loggers."""
        silence_external_loggers()
        
        # Check that external loggers are set to WARNING level
        urllib3_logger = logging.getLogger('urllib3')
        assert urllib3_logger.level == logging.WARNING
        
        requests_logger = logging.getLogger('requests')
        assert requests_logger.level == logging.WARNING
        
        rich_logger = logging.getLogger('rich')
        assert rich_logger.level == logging.WARNING
    
    @patch('sys.stdout')
    def test_logger_output_stream(self, mock_stdout):
        """Test that logger uses correct output stream."""
        logger = setup_logger("test_stream")
        
        # Check that handler uses stdout
        assert len(logger.handlers) > 0
        handler = logger.handlers[0]
        assert handler.stream == mock_stdout
    
    def test_logger_formatter_content(self):
        """Test logger formatter content."""
        logger = setup_logger("test_formatter")
        
        # Get the formatter
        handler = logger.handlers[0]
        formatter = handler.formatter
        
        # Test formatting with a sample record
        record = logging.LogRecord(
            name="test_formatter",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        assert "test_formatter" in formatted
        assert "INFO" in formatted
        assert "Test message" in formatted
    
    def teardown_method(self):
        """Clean up loggers after each test."""
        # Remove handlers from test loggers to avoid interference
        for logger_name in ["test_logger", "test_debug", "test_custom", 
                           "test_no_timestamp", "test_no_duplicate", 
                           "test_stream", "test_formatter"]:
            logger = logging.getLogger(logger_name)
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
