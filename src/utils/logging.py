"""
Logging Configuration
Structured logging with loguru
Source: https://github.com/Delgan/loguru
Verified: 2025-11-14
"""

import sys
from pathlib import Path

from loguru import logger


def setup_logging(
    level: str = "INFO",
    log_file: str | None = None,
    json_logs: bool = False,
) -> None:
    """
    Configure application logging.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
        json_logs: Whether to output JSON format (useful for production)

    Evidence: Loguru provides structured logging with better DX than stdlib logging
    Source: https://loguru.readthedocs.io/en/stable/api/logger.html
    Verified: 2025-11-14
    """

    # Remove default logger
    logger.remove()

    # Console logging configuration
    if json_logs:
        # JSON format for production (machine-readable)
        logger.add(
            sys.stderr,
            format="{message}",
            level=level,
            serialize=True,  # Output as JSON
        )
    else:
        # Human-readable format for development
        logger.add(
            sys.stderr,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
            level=level,
            colorize=True,
        )

    # File logging (if specified)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            log_file,
            rotation="100 MB",  # Rotate when file reaches 100MB
            retention="30 days",  # Keep logs for 30 days
            compression="zip",  # Compress rotated logs
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=level,
            serialize=json_logs,
        )

    logger.info(f"Logging configured: level={level}, json_logs={json_logs}")


def get_logger(name: str = __name__):  # type: ignore[no-untyped-def]
    """
    Get a logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance

    Example:
        >>> from src.utils.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Application started")
    """
    return logger.bind(name=name)
