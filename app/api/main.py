"""
FastAPI backend for UI automation platform.
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal
import asyncio
import logging
import traceback

from app.agents.orchestrator import AutomationOrchestrator
from app.telemetry.metrics import metrics_collector
from app.telemetry.logger import setup_logging
from app.config import settings
from app.compiler.script_generator import ScriptGenerator
from app.logging_config import add_app_handlers_to_root

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

# Execution cache: same test case (normalized instruction + script_lang) -> cached response for reuse
_execution_cache: dict = {}
_EXECUTION_CACHE_TTL_SECONDS = 3600  # 1 hour


class ExecutionRequest(BaseModel):
    """Request model for test execution."""
    instruction: str
    headless: bool = True
    max_recovery_attempts: int = 2
    script_language: Literal["javascript", "typescript"] = "typescript"
    use_v3: bool = False  # Use SAM-V3 engine (SmartLocator) when True
    force_run: bool = False  # If True, run even when same test was run recently (bypass cache)


class ExecutionResponse(BaseModel):
    """Response model for test execution."""
    success: bool
    steps_executed: int
    total_steps: int
    results: List[Dict[str, Any]]
    error: Optional[str] = None
    duration_seconds: Optional[float] = None
    # Generated test script (JavaScript or TypeScript per user selection) - always returned when steps exist
    generated_script: Optional[str] = None
    script_language: Optional[str] = None
    file_extension: Optional[str] = None
    # Script containing only the steps that executed successfully (for partial runs e.g. 6/24)
    generated_script_executed: Optional[str] = None


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    global orchestrator
    add_app_handlers_to_root()  # Ensure backend.log gets all logs (survives uvicorn dictConfig)
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
    summary = metrics_collector.get_summary()
    return {
        "status": "healthy",
        "timestamp": summary,  # legacy key for UI compatibility
        "metrics": summary,
    }


def _execution_cache_key(instruction: str, script_language: str) -> str:
    """Normalize instruction for cache key (strip, collapse whitespace)."""
    import hashlib
    normalized = " ".join((instruction or "").strip().split())
    return hashlib.sha256(f"{normalized}|{script_language}".encode()).hexdigest()


@app.post("/execute", response_model=ExecutionResponse)
async def execute_test(request: ExecutionRequest):
    """
    Execute test from natural language instruction.
    Reuses cached result when the same test case was run recently (unless force_run=True).
    """
    import time
    cache_key = _execution_cache_key(request.instruction, request.script_language)
    if not request.force_run and cache_key in _execution_cache:
        entry = _execution_cache[cache_key]
        if (time.monotonic() - entry["ts"]) < _EXECUTION_CACHE_TTL_SECONDS:
            logger.info("[API] Returning cached result for same test case (use force_run=true to re-run)")
            return entry["response"]
        del _execution_cache[cache_key]

    # Print so it shows even if logging is buffered (e.g. uvicorn --reload child on Windows)
    print("\n[BACKEND] POST /execute received - running test...", flush=True)
    logger.info("=" * 60)
    logger.info("EXECUTE REQUEST (from UI)")
    logger.info("Instruction: %s", request.instruction[:200] + ("..." if len(request.instruction) > 200 else ""))
    logger.info("Headless: %s | Max recovery: %s | Script lang: %s", request.headless, request.max_recovery_attempts, request.script_language)
    logger.info("=" * 60)
    
    start_time = time.monotonic()
    try:
        logger.info("[API] Creating orchestrator (use_v3=%s)...", request.use_v3)
        if request.use_v3:
            from app.orchestrator_v3 import AutomationOrchestratorV3
            orchestrator = AutomationOrchestratorV3(
                max_recovery_attempts=request.max_recovery_attempts,
                headless=request.headless
            )
        else:
            orchestrator = AutomationOrchestrator(
                max_recovery_attempts=request.max_recovery_attempts,
                headless=request.headless
            )
        
        metrics_collector.start_execution(
            test_name=request.instruction[:50],
            steps_total=0
        )
        
        logger.info("[API] Calling orchestrator.run() - see logs below for each step.")
        result = await orchestrator.run(request.instruction)
        duration_seconds = time.monotonic() - start_time
        logger.info("[API] Orchestrator finished. Steps: %s/%s, success: %s", result.get("steps_executed"), result.get("total_steps"), result.get("success"))
        
        # Generate script from execution steps - ALWAYS show script even on partial/full failure
        generated_script = None
        file_extension = None
        steps_for_script = result.get("steps")
        if not steps_for_script and result.get("error"):
            # Fallback: planner may not have run; try to get a plan for script display
            try:
                from app.agents.planner_agent import PlannerAgent
                from app.agents.planner_post_processor_v3 import process_steps
                planner = PlannerAgent()
                steps_for_script = await planner.plan(request.instruction)
                steps_for_script = process_steps(steps_for_script) if steps_for_script else []
            except Exception:
                pass
        generated_script_executed = None
        if steps_for_script:
            try:
                script_gen = ScriptGenerator(language=request.script_language)
                test_name = request.instruction[:50].replace(" ", "_").replace("'", "")
                generated_script = script_gen.generate_script(steps_for_script, test_name)
                file_extension = script_gen.get_file_extension()
                logger.info(f"Generated {request.script_language} script")

                # For partial runs: script with only the steps that executed successfully (first N steps)
                steps_ok = result.get("steps_executed", 0)
                if steps_ok > 0 and steps_ok < len(steps_for_script):
                    success_steps = steps_for_script[:steps_ok]
                    generated_script_executed = script_gen.generate_script(
                        success_steps,
                        test_name + "_executed_only"
                    )
                    logger.info("Generated script for executed steps only (%s steps)", len(success_steps))
            except Exception as e:
                logger.warning(f"Failed to generate script: {e}")
        
        # Update metrics with actual steps and duration before completing
        if metrics_collector.current_execution:
            metrics_collector.current_execution.steps_executed = result.get("steps_executed", 0)
            metrics_collector.current_execution.steps_total = result.get("total_steps", 0)
        metrics_collector.complete_execution(result["success"])
        
        # Build response (include generated script so UI can show it per user's language selection)
        response = ExecutionResponse(
            success=result["success"],
            steps_executed=result["steps_executed"],
            total_steps=result["total_steps"],
            results=result["results"],
            error=result.get("error"),
            duration_seconds=round(duration_seconds, 2),
            generated_script=generated_script,
            script_language=request.script_language,
            file_extension=file_extension or (".ts" if request.script_language == "typescript" else ".js"),
            generated_script_executed=generated_script_executed,
        )
        # Cache for reuse when same test is run again (saves execution time)
        _execution_cache[cache_key] = {"response": response, "ts": start_time}
        return response
        
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        logger.error("Backend traceback:\n%s", traceback.format_exc())
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
                use_v3 = data.get("use_v3", True)
                if use_v3:
                    from app.orchestrator_v3 import AutomationOrchestratorV3
                    orchestrator = AutomationOrchestratorV3(
                        headless=data.get("headless", True),
                        max_recovery_attempts=data.get("max_recovery_attempts", 2)
                    )
                else:
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
