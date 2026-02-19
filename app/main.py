"""
Main application entry point.
Logs go to terminal and to logs/uvicorn.log, logs/automation.log, logs/backend.log.
"""
import uvicorn
from app.api.main import app
from app.config import settings
from app.logging_config import UVICORN_LOG_CONFIG, LOGS_DIR

# Ensure logs dir exists
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Exclude these from reload watcher so log/file writes don't trigger restart loop
RELOAD_EXCLUDES = [
    "logs",
    "logs/*",
    "*.log",
    "api_startup*.log",
    "__pycache__",
    ".git",
    "venv",
]

if __name__ == "__main__":
    # Default: no reload so all logs appear in the same terminal and in log files
    use_reload = __import__("os").environ.get("RELOAD", "").lower() in ("1", "true", "yes")
    uvicorn.run(
        "app.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=use_reload,
        reload_excludes=RELOAD_EXCLUDES if use_reload else None,
        log_level=settings.LOG_LEVEL.lower(),
        log_config=UVICORN_LOG_CONFIG,
    )
