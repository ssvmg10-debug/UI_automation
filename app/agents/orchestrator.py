"""
LangGraph Orchestrator - coordinates the full execution flow.
AI assists planning and recovery, but execution is deterministic.
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional, Annotated
import operator
import logging

from .planner_agent import PlannerAgent, ExecutionStep
from .recovery_agent import RecoveryAgent, RecoveryStrategy
from app.core.action_executor import ActionExecutor, ActionResult
from app.core.browser import BrowserManager
from app.core.state_manager import StateManager

logger = logging.getLogger(__name__)


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
        
        # Add edges
        workflow.add_edge("initialize", "plan")
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
    
    async def _initialize_node(self, state: AutomationState) -> AutomationState:
        """Initialize browser and state manager."""
        logger.info("Initializing automation session...")
        
        try:
            # Create browser manager
            browser_manager = BrowserManager(headless=self.headless)
            await browser_manager.start()
            
            # Create state manager
            state_manager = StateManager()
            
            state["browser_manager"] = browser_manager
            state["state_manager"] = state_manager
            state["current_step_index"] = 0
            state["results"] = []
            state["recovery_attempts"] = 0
            state["max_recovery_attempts"] = self.max_recovery_attempts
            
            logger.info("✓ Initialization complete")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            state["error"] = str(e)
        
        return state
    
    async def _plan_node(self, state: AutomationState) -> AutomationState:
        """Plan execution from natural language instruction."""
        logger.info("Planning execution steps...")
        
        try:
            steps = await self.planner.plan(state["instruction"])
            state["steps"] = steps
            
            logger.info(f"✓ Generated {len(steps)} execution steps")
            
        except Exception as e:
            logger.error(f"Planning failed: {e}")
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
        logger.info(f"Executing step {step_index + 1}/{len(steps)}: {current_step}")
        
        try:
            browser_manager = state["browser_manager"]
            page = await browser_manager.get_page()
            
            # Execute action based on type
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
                
            elif current_step.action == "WAIT":
                result = await self.executor.wait_for_element(
                    page,
                    current_step.target
                )
            
            else:
                result = ActionResult(
                    success=False,
                    error=f"Unknown action: {current_step.action}"
                )
            
            # Record result
            state["results"].append(result)
            
            # Record state transition
            if result.success and result.after_state:
                await state["state_manager"].record_state(
                    page,
                    action=current_step.action,
                    element_used=result.element.display_name if result.element else None
                )
            
            logger.info(f"Step result: {'✓ SUCCESS' if result.success else '✗ FAILED'}")
            
        except Exception as e:
            logger.error(f"Execution error: {e}")
            result = ActionResult(success=False, error=str(e))
            state["results"].append(result)
        
        return state
    
    async def _validate_node(self, state: AutomationState) -> AutomationState:
        """Validate execution result."""
        last_result = state["results"][-1] if state["results"] else None
        
        if not last_result:
            state["error"] = "No execution result to validate"
            return state
        
        if last_result.success:
            # Success - move to next step
            state["current_step_index"] += 1
            state["recovery_attempts"] = 0  # Reset recovery counter
            logger.info("✓ Step validated successfully")
        else:
            # Failure - may need recovery
            logger.warning(f"✗ Step failed: {last_result.error}")
        
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
        logger.info("Cleaning up...")
        
        try:
            browser_manager = state["browser_manager"]
            if browser_manager:
                await browser_manager.close()
            
            logger.info("✓ Cleanup complete")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        
        return state
    
    async def run(self, instruction: str) -> dict:
        """
        Run automation from natural language instruction.
        
        Args:
            instruction: Natural language test case
            
        Returns:
            Execution result dictionary
        """
        logger.info(f"Starting automation: {instruction}")
        
        initial_state = {
            "instruction": instruction,
            "steps": [],
            "current_step_index": 0,
            "results": [],
            "error": None,
            "recovery_attempts": 0,
            "max_recovery_attempts": self.max_recovery_attempts,
            "browser_manager": None,
            "state_manager": None
        }
        
        try:
            final_state = await self.graph.ainvoke(initial_state)
            
            # Build result summary
            results = {
                "success": not final_state.get("error"),
                "steps_executed": final_state["current_step_index"],
                "total_steps": len(final_state["steps"]),
                "results": [r.to_dict() for r in final_state["results"]],
                "steps": final_state["steps"],  # Include steps for script generation
                "error": final_state.get("error")
            }
            
            if results["success"]:
                logger.info("✓ Automation completed successfully")
            else:
                logger.error(f"✗ Automation failed: {results['error']}")
            
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
