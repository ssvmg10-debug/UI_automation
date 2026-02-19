"""
LangGraph Orchestrator - coordinates the full execution flow.
AI assists planning and recovery, but execution is deterministic.
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional, Annotated
import operator
import logging
import traceback

from .planner_agent import PlannerAgent, ExecutionStep
from .recovery_agent import RecoveryAgent, RecoveryStrategy
from app.core.action_executor import ActionExecutor, ActionResult
from app.core.browser import BrowserManager
from app.core.state_manager import StateManager
from app.flow_optimization import FragmentStore, FragmentMatcher, URLShortcutRegistry, OptimizerEngine, FlowFragment

logger = logging.getLogger(__name__)


def _steps_to_dicts(steps: List[ExecutionStep]) -> List[dict]:
    """Convert ExecutionStep list to list of dicts for fragment matcher/optimizer."""
    return [
        {"action": getattr(s, "action", None), "target": getattr(s, "target", "") or "", "value": getattr(s, "value", None)}
        for s in steps
    ]


def _extract_site(url: str) -> str:
    """Extract site name from URL (e.g. lg.com)."""
    if not url:
        return "unknown"
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        host = (parsed.netloc or "").strip()
        if host.startswith("www."):
            host = host[4:]
        return host or "unknown"
    except Exception:
        return "unknown"


class AutomationState(TypedDict):
    """State for automation graph."""
    instruction: str
    steps: List[ExecutionStep]
    current_step_index: int
    results: Annotated[List[ActionResult], operator.add]
    error: Optional[str]
    recovery_attempts: int
    max_recovery_attempts: int
    browser_manager: Optional[BrowserManager]
    state_manager: Optional[StateManager]
    flow_start_url: Optional[str]
    last_optimization_skip: Optional[int]


class AutomationOrchestrator:
    """
    LangGraph orchestrator for UI automation.
    Coordinates planning, execution, validation, and recovery.
    """
    
    def __init__(
        self,
        max_recovery_attempts: int = 2,
        headless: bool = True
    ):
        """
        Initialize orchestrator.
        
        Args:
            max_recovery_attempts: Maximum recovery attempts per step
            headless: Run browser in headless mode
        """
        self.planner = PlannerAgent()
        self.executor = ActionExecutor()
        self.recovery_agent = RecoveryAgent()
        self.max_recovery_attempts = max_recovery_attempts
        self.headless = headless
        self._fragment_store = FragmentStore()
        self._fragment_matcher = FragmentMatcher(self._fragment_store)
        self._shortcut_registry = URLShortcutRegistry()
        self.optimizer = OptimizerEngine(self._fragment_matcher, self._shortcut_registry)
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build LangGraph execution flow."""
        
        # Create graph
        workflow = StateGraph(AutomationState)
        
        # Add nodes
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("execute", self._execute_node)
        workflow.add_node("validate", self._validate_node)
        workflow.add_node("recover", self._recover_node)
        workflow.add_node("cleanup", self._cleanup_node)
        
        # Set entry point
        workflow.set_entry_point("initialize")
        
        # If initialization fails, go to cleanup; otherwise plan
        workflow.add_conditional_edges(
            "initialize",
            self._after_initialize,
            {"plan": "plan", "cleanup": "cleanup"}
        )
        workflow.add_edge("plan", "execute")
        workflow.add_edge("execute", "validate")
        
        # Conditional edge from validate
        workflow.add_conditional_edges(
            "validate",
            self._should_recover,
            {
                "recover": "recover",
                "continue": "execute",
                "complete": "cleanup"
            }
        )
        
        # Edge from recover
        workflow.add_conditional_edges(
            "recover",
            self._should_retry_or_fail,
            {
                "retry": "execute",
                "fail": "cleanup"
            }
        )
        
        workflow.add_edge("cleanup", END)
        
        return workflow.compile()
    
    def _after_initialize(self, state: AutomationState) -> str:
        """If initialization failed, go to cleanup; else continue to plan."""
        if state.get("error") or state.get("browser_manager") is None:
            return "cleanup"
        return "plan"
    
    @staticmethod
    def _parse_wait_seconds(step: ExecutionStep) -> Optional[float]:
        """Parse WAIT step target/value to get seconds (e.g. '5', '5 seconds'). Returns None if not a plain wait."""
        import re
        for raw in (step.value, step.target):
            if not raw:
                continue
            s = str(raw).strip()
            # Extract number (e.g. "5", "5 seconds", "wait 5")
            m = re.search(r"(\d+(?:\.\d+)?)\s*(?:second|sec|s)?", s, re.I)
            if m:
                return float(m.group(1))
        return None
    
    async def _initialize_node(self, state: AutomationState) -> AutomationState:
        """Initialize browser and state manager."""
        logger.info("[ORCHESTRATOR] Step: INITIALIZE - Starting browser (headed=%s)", not self.headless)
        
        try:
            browser_manager = BrowserManager(headless=self.headless)
            await browser_manager.start()
            
            state_manager = StateManager()
            
            state["browser_manager"] = browser_manager
            state["state_manager"] = state_manager
            state["current_step_index"] = 0
            state["results"] = []
            state["recovery_attempts"] = 0
            state["max_recovery_attempts"] = self.max_recovery_attempts
            
            logger.info("[ORCHESTRATOR] Step: INITIALIZE - ✓ Browser and state manager ready")
            
        except Exception as e:
            logger.error("[ORCHESTRATOR] Step: INITIALIZE - ✗ Failed: %s", e)
            state["error"] = str(e)
        
        return state
    
    async def _plan_node(self, state: AutomationState) -> AutomationState:
        """Plan execution from natural language instruction."""
        logger.info("[ORCHESTRATOR] Step: PLAN - Converting instruction to steps...")
        
        try:
            steps = await self.planner.plan(state["instruction"])
            state["steps"] = steps
            
            logger.info("[ORCHESTRATOR] Step: PLAN - ✓ Generated %d steps", len(steps))
            for i, s in enumerate(steps, 1):
                logger.info("  [PLAN] Step %d: %s -> %s", i, s.action, (s.target or "")[:60])
        except Exception as e:
            logger.error("[ORCHESTRATOR] Step: PLAN - ✗ Failed: %s", e)
            state["error"] = str(e)
        
        return state
    
    async def _execute_node(self, state: AutomationState) -> AutomationState:
        """Execute current step."""
        step_index = state["current_step_index"]
        steps = state["steps"]
        
        if step_index >= len(steps):
            logger.info("All steps completed")
            return state
        
        current_step = steps[step_index]
        logger.info("[ORCHESTRATOR] Step: EXECUTE %d/%d - Action=%s Target=%s", step_index + 1, len(steps), current_step.action, (current_step.target or "")[:80])
        
        try:
            browser_manager = state.get("browser_manager")
            if browser_manager is None:
                err = "Browser not initialized (initialization may have failed). Check backend logs."
                logger.error("[ORCHESTRATOR] Step: EXECUTE %d/%d - ✗ %s", step_index + 1, len(steps), err)
                new_result = ActionResult(success=False, error=err)
                return {**state, "results": [new_result]}
            page = await browser_manager.get_page()

            # Flow optimization: try fragment reuse or URL shortcut before executing
            remaining_as_dicts = [
                {"action": s.action, "target": s.target or "", "value": getattr(s, "value", None)}
                for s in steps[step_index:]
            ]
            if step_index == 0:
                state["flow_start_url"] = page.url or ""

            try:
                opt = await self.optimizer.optimize(page, remaining_as_dicts)
            except Exception as opt_err:
                logger.debug("Optimizer check failed: %s", opt_err)
                opt = None
            if opt:
                if opt["type"] == "fragment":
                    await page.goto(opt["end_url"], wait_until="domcontentloaded")
                    skip = opt["skip"]
                    logger.info("[ORCHESTRATOR] Fragment reuse: goto %s, skip %d steps", opt["end_url"][:60], skip)
                    return {
                        **state,
                        "results": [ActionResult(success=True)],
                        "last_optimization_skip": skip,
                    }
                if opt["type"] == "shortcut":
                    await page.goto(opt["url"], wait_until="domcontentloaded")
                    skip = opt["skip"]
                    logger.info("[ORCHESTRATOR] URL shortcut: goto %s, skip %d step(s)", opt["url"][:60], skip)
                    return {
                        **state,
                        "results": [ActionResult(success=True)],
                        "last_optimization_skip": skip,
                    }

            if current_step.action == "NAVIGATE":
                result = await self.executor.navigate(page, current_step.target)
                
            elif current_step.action == "CLICK":
                result = await self.executor.click(
                    page,
                    current_step.target,
                    region_context=current_step.region
                )
                
            elif current_step.action == "TYPE":
                result = await self.executor.type_text(
                    page,
                    current_step.target,
                    current_step.value
                )
            
            elif current_step.action == "SELECT":
                result = await self.executor.select_option(
                    page,
                    current_step.target,
                    current_step.value
                )
            
            elif current_step.action == "WAIT":
                # "wait for 5 seconds" or value="5" -> sleep N seconds; else wait for element
                wait_seconds = self._parse_wait_seconds(current_step)
                if wait_seconds is not None:
                    import asyncio
                    logger.info("[ORCHESTRATOR] Step: EXECUTE %d/%d - WAIT %s seconds", step_index + 1, len(steps), wait_seconds)
                    await asyncio.sleep(wait_seconds)
                    result = ActionResult(success=True)
                else:
                    result = await self.executor.wait_for_element(
                        page,
                        current_step.target or ""
                    )
            
            else:
                result = ActionResult(
                    success=False,
                    error=f"Unknown action: {current_step.action}"
                )
            
            # Return only the new result - LangGraph merges with operator.add so existing + [result]
            if result.success and result.after_state:
                await state["state_manager"].record_state(
                    page,
                    action=current_step.action,
                    element_used=result.element.display_name if result.element else None
                )
            if step_index == 0 and result.success and getattr(result, "after_state", None) and result.after_state.url:
                state["flow_start_url"] = result.after_state.url

            logger.info("[ORCHESTRATOR] Step: EXECUTE %d/%d - %s %s", step_index + 1, len(steps), "✓ SUCCESS" if result.success else "✗ FAILED", (" | " + result.error) if getattr(result, "error", None) else "")
            return {**state, "results": [result]}
            
        except Exception as e:
            logger.error("[ORCHESTRATOR] Step: EXECUTE %d/%d - Exception: %s", step_index + 1, len(steps), e)
            logger.error("Orchestrator traceback:\n%s", traceback.format_exc())
            result = ActionResult(success=False, error=str(e))
            return {**state, "results": [result]}
    
    async def _validate_node(self, state: AutomationState) -> AutomationState:
        """Validate execution result."""
        last_result = state["results"][-1] if state["results"] else None
        
        if not last_result:
            state["error"] = "No execution result to validate"
            logger.error("[ORCHESTRATOR] Step: VALIDATE - No result to validate")
            return state
        
        if last_result.success:
            skip = state.pop("last_optimization_skip", None)
            state["current_step_index"] += (skip if skip is not None else 1)
            state["recovery_attempts"] = 0
            logger.info("[ORCHESTRATOR] Step: VALIDATE - ✓ Step OK, moving to next (index=%d)", state["current_step_index"])
        else:
            logger.warning("[ORCHESTRATOR] Step: VALIDATE - ✗ Step failed: %s", getattr(last_result, "error", ""))
        
        return state
    
    def _should_recover(self, state: AutomationState) -> str:
        """Determine next action after validation."""
        last_result = state["results"][-1] if state["results"] else None
        
        # Check if we're done
        if state["current_step_index"] >= len(state["steps"]):
            return "complete"
        
        # Check if last step succeeded
        if last_result and last_result.success:
            return "continue"
        
        # Check if we should attempt recovery
        if state["recovery_attempts"] < state["max_recovery_attempts"]:
            return "recover"
        
        # Exceeded recovery attempts
        logger.error("Maximum recovery attempts exceeded")
        state["error"] = "Maximum recovery attempts exceeded"
        return "complete"
    
    async def _recover_node(self, state: AutomationState) -> AutomationState:
        """Attempt recovery from failure."""
        logger.info("Attempting recovery...")
        
        state["recovery_attempts"] += 1
        
        try:
            # Get failure context
            current_step = state["steps"][state["current_step_index"]]
            last_result = state["results"][-1]
            
            # Get available elements from page
            browser_manager = state["browser_manager"]
            page = await browser_manager.get_page()
            
            from app.core.dom_extractor import DOMExtractor
            extractor = DOMExtractor()
            elements = await extractor.extract_all_interactive(page)
            available_texts = [e.display_name for e in elements[:50]]
            
            # Get recovery suggestions
            strategies = await self.recovery_agent.suggest_recovery(
                failed_action=current_step.action,
                failed_target=current_step.target,
                error_message=last_result.error or "Unknown error",
                available_elements=available_texts,
                page_context={
                    "url": page.url,
                    "title": await page.title()
                }
            )
            
            # Apply first strategy
            if strategies:
                strategy = strategies[0]
                logger.info(f"Applying recovery strategy: {strategy.description}")
                
                if strategy.alternative_target:
                    # Update step with alternative target
                    current_step.target = strategy.alternative_target
                    logger.info(f"Using alternative target: '{strategy.alternative_target}'")
                
                if strategy.wait_time:
                    # Wait before retry
                    import asyncio
                    logger.info(f"Waiting {strategy.wait_time}s before retry")
                    await asyncio.sleep(strategy.wait_time)
            
        except Exception as e:
            logger.error(f"Recovery failed: {e}")
        
        return state
    
    def _should_retry_or_fail(self, state: AutomationState) -> str:
        """Determine whether to retry or fail after recovery."""
        if state["recovery_attempts"] < state["max_recovery_attempts"]:
            return "retry"
        return "fail"
    
    async def _cleanup_node(self, state: AutomationState) -> AutomationState:
        """Cleanup resources."""
        logger.info("[ORCHESTRATOR] Step: CLEANUP - Closing browser...")
        
        try:
            browser_manager = state.get("browser_manager")
            if browser_manager:
                await browser_manager.close()
            
            logger.info("[ORCHESTRATOR] Step: CLEANUP - ✓ Done")
            
        except Exception as e:
            logger.error("[ORCHESTRATOR] Step: CLEANUP - Error: %s", e)
        
        return state
    
    async def run(self, instruction: str) -> dict:
        """
        Run automation from natural language instruction.
        
        Args:
            instruction: Natural language test case
            
        Returns:
            Execution result dictionary
        """
        logger.info("[ORCHESTRATOR] run() started. Instruction (first 150 chars): %s", instruction[:150] + ("..." if len(instruction) > 150 else ""))
        
        initial_state: AutomationState = {
            "instruction": instruction,
            "steps": [],
            "current_step_index": 0,
            "results": [],
            "error": None,
            "recovery_attempts": 0,
            "max_recovery_attempts": self.max_recovery_attempts,
            "browser_manager": None,
            "state_manager": None,
            "flow_start_url": None,
        }
        
        try:
            final_state = await self.graph.ainvoke(initial_state)
            
            steps_executed = final_state["current_step_index"]
            total_steps = len(final_state["steps"])
            step_results = final_state["results"]
            # Success only when: no init/plan error AND all steps ran and all passed
            all_passed = (
                len(step_results) > 0
                and all(getattr(r, "success", False) for r in step_results)
                and steps_executed >= total_steps
            )
            has_error = bool(final_state.get("error"))
            success = not has_error and (all_passed if total_steps > 0 else True)
            
            results = {
                "success": success,
                "steps_executed": steps_executed,
                "total_steps": total_steps,
                "results": [r.to_dict() for r in step_results],
                "steps": final_state["steps"],
                "error": final_state.get("error")
            }
            
            if results["success"]:
                logger.info("✓ Automation completed successfully")
            else:
                logger.error(f"✗ Automation failed: {results.get('error', 'steps failed')} (steps: {steps_executed}/{total_steps})")
            
            return results
            
        except Exception as e:
            logger.error(f"Orchestration error: {e}")
            return {
                "success": False,
                "error": str(e),
                "steps_executed": 0,
                "total_steps": 0,
                "results": []
            }
