"""
Orchestrator V3 - SAM-V3 engine with planner post-processing.
Uses ActionExecutorV3 (SmartLocator) and planner_post_processor_v3.
"""
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Optional, Annotated
import operator
import logging
import traceback
import re

from app.agents.planner_agent import PlannerAgent, ExecutionStep
from app.agents.recovery_agent import RecoveryAgent
from app.agents.action_executor_v3 import ActionExecutorV3
from app.agents.planner_post_processor_v3 import process_steps
from app.core.action_executor import ActionResult
from app.core.browser import BrowserManager
from app.core.state_manager import StateManager
from app.flow_optimization.optimizer_engine import OptimizerEngine
from app.flow_optimization.fragment_matcher import FragmentMatcher
from app.flow_optimization.fragment_store import FragmentStore
from app.flow_optimization.url_shortcut_registry import URLShortcutRegistry
from app.flow_optimization.fragment_recorder import save_fragments
from app.config import settings

logger = logging.getLogger(__name__)


def _parse_wait_seconds(step: ExecutionStep) -> Optional[float]:
    """Parse WAIT step to get seconds."""
    for raw in (step.value, step.target):
        if not raw:
            continue
        s = str(raw).strip()
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:second|sec|s)?", s, re.I)
        if m:
            return float(m.group(1))
    return None


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
    last_optimization_skip: Optional[int]
    flow_start_url: Optional[str]
    step_end_urls: Optional[List[str]]
    fragment_reuse_count: Optional[int]
    url_shortcut_count: Optional[int]
    fragments_saved: Optional[int]


class AutomationOrchestratorV3:
    """SAM-V3 Orchestrator: Planner + Post-Processor + ActionExecutorV3."""

    def __init__(self, max_recovery_attempts: int = 2, headless: bool = True):
        self.planner = PlannerAgent()
        self.executor = ActionExecutorV3()
        self.recovery_agent = RecoveryAgent()
        self.max_recovery_attempts = max_recovery_attempts
        self.headless = headless
        self._fragment_store = FragmentStore()
        self.optimizer = OptimizerEngine(
            fragment_matcher=FragmentMatcher(self._fragment_store),
            shortcut_registry=URLShortcutRegistry(),
        )
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AutomationState)
        workflow.add_node("initialize", self._initialize_node)
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("execute", self._execute_node)
        workflow.add_node("validate", self._validate_node)
        workflow.add_node("recover", self._recover_node)
        workflow.add_node("cleanup", self._cleanup_node)

        workflow.set_entry_point("initialize")
        workflow.add_conditional_edges("initialize", self._after_init, {"plan": "plan", "cleanup": "cleanup"})
        workflow.add_edge("plan", "execute")
        workflow.add_edge("execute", "validate")
        workflow.add_conditional_edges("validate", self._should_recover, {"recover": "recover", "continue": "execute", "complete": "cleanup"})
        workflow.add_conditional_edges("recover", self._retry_or_fail, {"retry": "execute", "fail": "cleanup"})
        workflow.add_edge("cleanup", END)
        return workflow.compile()

    def _after_init(self, state: AutomationState) -> str:
        if state.get("error") or state.get("browser_manager") is None:
            return "cleanup"
        return "plan"

    async def _initialize_node(self, state: AutomationState) -> AutomationState:
        logger.info("[ORCH_V3] INITIALIZE (headed=%s)", not self.headless)
        try:
            timeout = 60000
            bm = BrowserManager(headless=self.headless, timeout=timeout)
            await bm.start()
            state["browser_manager"] = bm
            state["state_manager"] = StateManager()
            state["current_step_index"] = 0
            state["results"] = []
            state["recovery_attempts"] = 0
            state["max_recovery_attempts"] = self.max_recovery_attempts
            state["flow_start_url"] = None
            state["step_end_urls"] = []
            state["fragment_reuse_count"] = 0
            state["url_shortcut_count"] = 0
        except Exception as e:
            logger.error("[ORCH_V3] Init failed: %s", e)
            state["error"] = str(e)
        return state

    async def _plan_node(self, state: AutomationState) -> AutomationState:
        logger.info("[ORCH_V3] PLAN")
        try:
            steps = await self.planner.plan(state["instruction"])
            steps = process_steps(steps)  # V3 post-processor
            state["steps"] = steps
            logger.info("[ORCH_V3] Planned %d steps (post-processed)", len(steps))
        except Exception as e:
            logger.error("[ORCH_V3] Plan failed: %s", e)
            state["error"] = str(e)
        return state

    async def _execute_node(self, state: AutomationState) -> AutomationState:
        idx = state["current_step_index"]
        steps = state["steps"]

        if idx >= len(steps):
            return state

        step = steps[idx]
        logger.info("[ORCH_V3] EXECUTE %d/%d: %s '%s'", idx + 1, len(steps), step.action, (step.target or "")[:60])

        try:
            bm = state.get("browser_manager")
            if not bm:
                state["results"] = [ActionResult(success=False, error="Browser not initialized")]
                return state

            page = await bm.get_page()

            # Flow optimization: try fragment reuse or URL shortcut before executing
            remaining_as_dicts = [
                {"action": s.action, "target": s.target or "", "value": getattr(s, "value", None)}
                for s in steps[idx:]
            ]
            try:
                opt = await self.optimizer.optimize(page, remaining_as_dicts)
            except Exception as opt_err:
                logger.debug("Optimizer check failed: %s", opt_err)
                opt = None
            if opt:
                end_url = opt.get("end_url") or opt.get("url", "")
                skip = opt["skip"]
                if opt["type"] == "fragment":
                    await page.goto(opt["end_url"], wait_until="domcontentloaded")
                    logger.info("[ORCH_V3] Fragment reuse: goto %s, skip %d steps", opt["end_url"][:60], skip)
                    updates = {"fragment_reuse_count": (state.get("fragment_reuse_count") or 0) + 1}
                else:
                    await page.goto(opt["url"], wait_until="domcontentloaded")
                    logger.info("[ORCH_V3] URL shortcut: goto %s, skip %d step(s)", opt["url"][:60], skip)
                    updates = {"url_shortcut_count": (state.get("url_shortcut_count") or 0) + 1}
                # Track for fragment saving
                urls = state.get("step_end_urls") or []
                urls.extend([end_url] * skip)
                updates["results"] = [ActionResult(success=True)]
                updates["last_optimization_skip"] = skip
                updates["step_end_urls"] = urls
                if idx == 0 and not state.get("flow_start_url"):
                    updates["flow_start_url"] = end_url
                return {**state, **updates}

            if step.action == "NAVIGATE":
                result = await self.executor.navigate(page, step.target or "")
            elif step.action == "CLICK":
                result = await self.executor.click(page, step.target or "", region_context=step.region)
            elif step.action == "TYPE":
                result = await self.executor.type_text(page, step.target or "", step.value or "")
            elif step.action == "SELECT":
                result = await self.executor.select_option(page, step.target or "", step.value or "")
            elif step.action == "WAIT":
                wait_sec = _parse_wait_seconds(step)
                if wait_sec is not None:
                    import asyncio
                    await asyncio.sleep(wait_sec)
                    result = ActionResult(success=True)
                else:
                    result = await self.executor.wait_for_element(page, step.target or "")
            else:
                result = ActionResult(success=False, error=f"Unknown action: {step.action}")

            if result.success and result.after_state and state.get("state_manager"):
                await state["state_manager"].record_state(page, action=step.action, element_used=None)

            # Track for fragment saving
            updates = {"results": [result]}
            if result.success:
                end_url = (
                    getattr(result.after_state, "url", None) if result.after_state
                    else (page.url if page else None)
                )
                urls = list(state.get("step_end_urls") or [])
                urls.append(end_url or "")
                updates["step_end_urls"] = urls
                if idx == 0 and not state.get("flow_start_url"):
                    updates["flow_start_url"] = end_url or (page.url if page else "")

            logger.info("[ORCH_V3] Step %d: %s", idx + 1, "✓" if result.success else f"✗ {result.error}")
            return {**state, **updates}

        except Exception as e:
            logger.error("[ORCH_V3] Execute exception: %s", traceback.format_exc())
            return {**state, "results": [ActionResult(success=False, error=str(e))]}

    async def _validate_node(self, state: AutomationState) -> AutomationState:
        last = state["results"][-1] if state["results"] else None
        if not last:
            state["error"] = "No result"
            return state
        if last.success:
            skip = state.pop("last_optimization_skip", None)
            state["current_step_index"] += (skip if skip is not None else 1)
            state["recovery_attempts"] = 0
        return state

    def _should_recover(self, state: AutomationState) -> str:
        if state["current_step_index"] >= len(state["steps"]):
            return "complete"
        if state["results"] and state["results"][-1].success:
            return "continue"
        if state["recovery_attempts"] < state["max_recovery_attempts"]:
            return "recover"
        state["error"] = "Max recovery exceeded"
        return "complete"

    async def _recover_node(self, state: AutomationState) -> AutomationState:
        state["recovery_attempts"] += 1
        logger.info("[ORCH_V3] Recovery attempt %d", state["recovery_attempts"])
        try:
            step = state["steps"][state["current_step_index"]]
            last = state["results"][-1]
            page = await state["browser_manager"].get_page()
            from app.core.dom_extractor import DOMExtractor
            ext = DOMExtractor()
            elements = await ext.extract_all_interactive(page)
            texts = [e.display_name for e in elements[:50]]
            strategies = await self.recovery_agent.suggest_recovery(
                step.action, step.target or "", last.error or "", texts, {"url": page.url}
            )
            if strategies and strategies[0].alternative_target:
                step.target = strategies[0].alternative_target
            if strategies and strategies[0].wait_time:
                import asyncio
                await asyncio.sleep(strategies[0].wait_time)
        except Exception as e:
            logger.debug("Recovery: %s", e)
        return state

    def _retry_or_fail(self, state: AutomationState) -> str:
        return "retry" if state["recovery_attempts"] < state["max_recovery_attempts"] else "fail"

    async def _cleanup_node(self, state: AutomationState) -> AutomationState:
        logger.info("[ORCH_V3] CLEANUP")
        try:
            # Save fragments for reuse before closing browser
            saved = 0
            if getattr(settings, "FRAGMENT_SAVE_ENABLED", True):
                saved = save_fragments(
                    state,
                    self._fragment_store,
                    min_length=getattr(settings, "FRAGMENT_MIN_LENGTH", 2),
                    enabled=True,
                )
                if saved > 0:
                    logger.info("[ORCH_V3] Saved %d new fragment(s) for reuse", saved)
            state["fragments_saved"] = saved
            if state.get("browser_manager"):
                await state["browser_manager"].close()
        except Exception as e:
            logger.error("Cleanup: %s", e)
        return state

    async def run(self, instruction: str) -> dict:
        logger.info("[ORCH_V3] run() instruction: %s...", instruction[:100])
        initial: AutomationState = {
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
            "step_end_urls": [],
            "fragment_reuse_count": 0,
            "url_shortcut_count": 0,
        }
        try:
            final = await self.graph.ainvoke(initial)
            executed = final["current_step_index"]
            total = len(final["steps"])
            results = final["results"]
            all_ok = results and all(getattr(r, "success", False) for r in results) and executed >= total
            success = not final.get("error") and (all_ok if total > 0 else True)
            return {
                "success": success,
                "steps_executed": executed,
                "total_steps": total,
                "results": [r.to_dict() for r in results],
                "steps": final["steps"],
                "error": final.get("error"),
                "fragment_reuse_count": final.get("fragment_reuse_count") or 0,
                "url_shortcut_count": final.get("url_shortcut_count") or 0,
                "fragments_saved": final.get("fragments_saved") or 0,
            }
        except Exception as e:
            logger.error("[ORCH_V3] Error: %s", e)
            return {"success": False, "error": str(e), "steps_executed": 0, "total_steps": 0, "results": []}
