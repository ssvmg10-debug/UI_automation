"""
Main application entry point.
"""
import uvicorn
from app.api.main import app
from app.config import settings


if __name__ == "__main__":
    uvicorn.run(
        "app.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
