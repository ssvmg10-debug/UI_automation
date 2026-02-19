"""
FastAPI backend for UI automation platform.
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal
import asyncio
import logging

from app.agents.orchestrator import AutomationOrchestrator
from app.telemetry.metrics import metrics_collector
from app.telemetry.logger import setup_logging
from app.config import settings
from app.compiler.script_generator import ScriptGenerator

# Setup logging
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_file=settings.LOG_FILE,
    console=True
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Enterprise UI Automation Platform",
    description="Production-grade deterministic UI automation with AI assistance",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator = None


class ExecutionRequest(BaseModel):
    """Request model for test execution."""
    instruction: str
    headless: bool = True
    max_recovery_attempts: int = 2
    script_language: Literal["javascript", "typescript"] = "typescript"


class ExecutionResponse(BaseModel):
    """Response model for test execution."""
    success: bool
    steps_executed: int
    total_steps: int
    results: List[Dict[str, Any]]
    error: Optional[str] = None
    duration_seconds: Optional[float] = None


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    global orchestrator
    logger.info("Starting Enterprise UI Automation Platform...")
    logger.info(f"API Host: {settings.API_HOST}:{settings.API_PORT}")
    logger.info(f"Headless Mode: {settings.HEADLESS}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Enterprise UI Automation Platform...")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Enterprise UI Automation Platform",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": metrics_collector.get_summary()
    }


@app.post("/execute", response_model=ExecutionResponse)
async def execute_test(request: ExecutionRequest):
    """
    Execute test from natural language instruction.
    
    Args:
        request: Execution request with instruction
        
    Returns:
        Execution response with results
    """
    logger.info(f"Received execution request: {request.instruction[:100]}...")
    
    try:
        # Create orchestrator
        orchestrator = AutomationOrchestrator(
            max_recovery_attempts=request.max_recovery_attempts,
            headless=request.headless
        )
        
        # Start metrics tracking
        metrics_collector.start_execution(
            test_name=request.instruction[:50],
            steps_total=0
        )
        
        # Execute
        result = await orchestrator.run(request.instruction)
        
        # Generate script from execution steps
        generated_script = None
        file_extension = None
        if result.get("steps"):
            try:
                script_gen = ScriptGenerator(language=request.script_language)
                test_name = request.instruction[:50].replace(" ", "_").replace("'", "")
                generated_script = script_gen.generate_script(result["steps"], test_name)
                file_extension = script_gen.get_file_extension()
                logger.info(f"Generated {request.script_language} script")
            except Exception as e:
                logger.warning(f"Failed to generate script: {e}")
        
        # Complete metrics
        metrics_collector.complete_execution(result["success"])
        
        # Build response
        response_data = ExecutionResponse(
            success=result["success"],
            steps_executed=result["steps_executed"],
            total_steps=result["total_steps"],
            results=result["results"],
            error=result.get("error")
        )
        
        # Add generated script to response dict
        response_dict = response_data.dict()
        response_dict["generated_script"] = generated_script
        response_dict["script_language"] = request.script_language
        response_dict["file_extension"] = file_extension
        
        return response_dict
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        metrics_collector.complete_execution(False)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/summary")
async def get_metrics_summary():
    """Get metrics summary."""
    return metrics_collector.get_summary()


@app.get("/metrics/recent")
async def get_recent_executions(limit: int = 10):
    """Get recent executions."""
    executions = metrics_collector.get_recent_executions(limit)
    return {
        "executions": [e.to_dict() for e in executions]
    }


@app.post("/metrics/clear")
async def clear_metrics():
    """Clear all metrics."""
    metrics_collector.clear()
    return {"status": "metrics cleared"}


@app.websocket("/ws/execute")
async def websocket_execute(websocket: WebSocket):
    """
    WebSocket endpoint for real-time execution updates.
    """
    await websocket.accept()
    logger.info("WebSocket client connected")
    
    try:
        while True:
            # Receive instruction
            data = await websocket.receive_json()
            instruction = data.get("instruction")
            
            if not instruction:
                await websocket.send_json({"error": "No instruction provided"})
                continue
            
            # Send start notification
            await websocket.send_json({
                "status": "started",
                "instruction": instruction
            })
            
            # Execute
            try:
                orchestrator = AutomationOrchestrator(
                    headless=data.get("headless", True),
                    max_recovery_attempts=data.get("max_recovery_attempts", 2)
                )
                
                result = await orchestrator.run(instruction)
                
                # Send result
                await websocket.send_json({
                    "status": "completed",
                    "result": result
                })
                
            except Exception as e:
                await websocket.send_json({
                    "status": "error",
                    "error": str(e)
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")


# Export app
__all__ = ["app"]
