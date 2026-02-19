"""
Centralized logging configuration.
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


class FlushingStreamHandler(logging.StreamHandler):
    """StreamHandler that flushes after every emit so logs show immediately (e.g. under uvicorn --reload)."""

    def emit(self, record: logging.LogRecord) -> None:
        super().emit(record)
        self.flush()


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True
) -> None:
    """
    Setup centralized logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        console: Whether to log to console
    """
    # Create formatters
    detailed_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler - flush after each log so logs appear immediately (e.g. in uvicorn reload child)
    if console:
        console_handler = FlushingStreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(simple_formatter)
        root_logger.addHandler(console_handler)
    
    # File handlers: automation.log (detailed) and backend.log (all app logs for easy tail)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)
    # All app logs also go to logs/backend.log so you can tail one file to see everything
    backend_log = Path("logs") / "backend.log"
    try:
        backend_log.parent.mkdir(parents=True, exist_ok=True)
        backend_handler = logging.FileHandler(backend_log, mode="a", encoding="utf-8")
        backend_handler.setLevel(getattr(logging, log_level.upper()))
        backend_handler.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s] %(message)s", datefmt="%H:%M:%S"))
        root_logger.addHandler(backend_handler)
    except Exception:
        pass
    
    # Reduce noise from third-party libraries
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    # Stop "X change(s) detected" spam from uvicorn's file watcher (watchfiles)
    logging.getLogger("watchfiles.main").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LogContext:
    """Context manager for structured logging."""
    
    def __init__(self, logger: logging.Logger, context: str):
        self.logger = logger
        self.context = context
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"→ {self.context}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type:
            self.logger.error(f"✗ {self.context} failed after {duration:.2f}s: {exc_val}")
        else:
            self.logger.info(f"✓ {self.context} completed in {duration:.2f}s")
        
        return False  # Don't suppress exceptions
