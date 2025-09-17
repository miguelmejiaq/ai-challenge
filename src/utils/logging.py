"""
Logging configuration utilities for MiniTel-Lite client.
"""

import logging
import sys
from typing import Optional


def setup_logger(
    name: str,
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    include_timestamp: bool = True
) -> logging.Logger:
    """
    Set up a logger with consistent formatting.
    
    Args:
        name: Logger name
        level: Logging level
        format_string: Custom format string
        include_timestamp: Whether to include timestamp in logs
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding multiple handlers
    if logger.handlers:
        return logger
    
    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    # Create formatter
    if format_string is None:
        if include_timestamp:
            format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        else:
            format_string = '%(name)s - %(levelname)s - %(message)s'
    
    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger


def set_global_log_level(level: int) -> None:
    """
    Set the global logging level for all loggers.
    
    Args:
        level: Logging level (e.g., logging.DEBUG, logging.INFO)
    """
    logging.getLogger().setLevel(level)
    
    # Also set for specific loggers
    for logger_name in ['src.minitel', 'src.tui']:
        logger = logging.getLogger(logger_name)
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)


def configure_debug_logging() -> None:
    """Configure debug-level logging for development."""
    set_global_log_level(logging.DEBUG)
    
    # Add more detailed formatting for debug mode
    debug_format = '%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s'
    
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            handler.setFormatter(logging.Formatter(debug_format))


def silence_external_loggers() -> None:
    """Silence noisy external library loggers."""
    # Silence common noisy loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('rich').setLevel(logging.WARNING)
