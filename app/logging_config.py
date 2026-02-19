"""
Logging configuration for backend and uvicorn.
Uvicorn calls dictConfig() on startup, which replaces the root logger.
So we put app log handlers (console + backend.log) in this config so all logs are captured.
"""
import logging
import sys
from pathlib import Path

# Use path relative to project root (parent of app/) so logs are always in project/logs
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = _PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

UVICORN_LOG_FILE = str(LOGS_DIR / "uvicorn.log")
APP_LOG_FILE = str(LOGS_DIR / "automation.log")
BACKEND_LOG_FILE = str(LOGS_DIR / "backend.log")

# Uvicorn applies this via dictConfig() - so root logger MUST have handlers here
# or app logs (API, orchestrator, etc.) will go nowhere after startup.
UVICORN_LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "detailed": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": "ext://sys.stdout",
        },
        "uvicorn_file": {
            "class": "logging.FileHandler",
            "formatter": "detailed",
            "filename": UVICORN_LOG_FILE,
            "mode": "a",
            "encoding": "utf-8",
        },
        "backend_file": {
            "class": "logging.FileHandler",
            "formatter": "detailed",
            "filename": BACKEND_LOG_FILE,
            "mode": "a",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "uvicorn": {
            "handlers": ["console", "uvicorn_file"],
            "level": "INFO",
            "propagate": False,
        },
        "uvicorn.error": {
            "handlers": ["console", "uvicorn_file"],
            "level": "INFO",
            "propagate": False,
        },
    },
    # App loggers propagate to root - so root must have handlers for execute/orchestrator logs to appear
    "root": {
        "level": "INFO",
        "handlers": ["console", "backend_file"],
    },
}


def add_app_handlers_to_root():
    """Ensure root logger has a file handler for backend.log (in case uvicorn dictConfig cleared it)."""
    root = logging.getLogger()
    backend_path = str(Path(BACKEND_LOG_FILE).resolve())
    has_backend = any(
        getattr(h, "baseFilename", None) == backend_path
        for h in root.handlers
        if isinstance(h, logging.FileHandler)
    )
    if not has_backend:
        Path(BACKEND_LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(BACKEND_LOG_FILE, mode="a", encoding="utf-8")
        fh.setFormatter(logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s] %(message)s", datefmt="%H:%M:%S"))
        root.addHandler(fh)
