"""
Utility functions for Intelligent CD Chatbot.

This module contains shared utility functions that can be imported by both
main.py and the tab classes without creating circular dependencies.
"""

import os
import logging


def setup_logging():
    """Configure logging with different levels and formatters"""
    # Get log level from environment variable, default to INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure third-party loggers to reduce noise
    # Set httpx (HTTP client) to WARNING level to reduce HTTP request logs
    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)
    
    # Set urllib3 (HTTP library) to WARNING level
    urllib3_logger = logging.getLogger("urllib3")
    urllib3_logger.setLevel(logging.WARNING)
    
    # Set requests to WARNING level
    requests_logger = logging.getLogger("requests")
    requests_logger.setLevel(logging.WARNING)
    
    return log_level, formatter


def get_logger(name: str):
    """Get a logger with the specified name and proper configuration"""
    # Initialize logging configuration
    log_level, log_formatter = setup_logging()
    
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Prevent propagation to root logger to avoid duplicates
    logger.propagate = False
    
    # Create console handler only
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level))
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)
    
    return logger
