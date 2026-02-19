"""
Recovery Agent - provides suggestions when execution fails.
Advisory only - does NOT execute actions.
"""
from openai import AsyncAzureOpenAI
from typing import Optional, Dict, Any, List
import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class RecoveryStrategy:
    """Represents a recovery strategy suggestion."""
    
    def __init__(
        self,
        strategy_type: str,
        description: str,
        alternative_target: Optional[str] = None,
        wait_time: Optional[float] = None
    ):
        self.strategy_type = strategy_type
        self.description = description
        self.alternative_target = alternative_target
        self.wait_time = wait_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.strategy_type,
            "description": self.description,
            "alternative_target": self.alternative_target,
            "wait_time": self.wait_time
        }


class RecoveryAgent:
    """
    AI agent that suggests recovery strategies when execution fails.
    Does NOT execute recovery - only provides suggestions.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize recovery agent.
        
        Args:
            api_key: Azure OpenAI API key (uses settings if not provided)
        """
        self.client = AsyncAzureOpenAI(
            api_key=api_key or settings.AZURE_API_KEY,
            api_version=settings.AZURE_API_VERSION,
            azure_endpoint=settings.AZURE_ENDPOINT
        )
        self.model = settings.AZURE_DEPLOYMENT
    
    async def suggest_recovery(
        self,
        failed_action: str,
        failed_target: str,
        error_message: str,
        available_elements: List[str],
        page_context: Optional[Dict[str, Any]] = None
    ) -> List[RecoveryStrategy]:
        """
        Suggest recovery strategies for failed action.
        
        Args:
            failed_action: Action that failed
            failed_target: Target element that was not found
            error_message: Error message from failure
            available_elements: List of available element texts on page
            page_context: Optional page context (URL, title, etc.)
            
        Returns:
            List of recovery strategy suggestions
        """
        logger.info(f"Generating recovery strategies for failed action: {failed_action}")
        
        prompt = self._build_recovery_prompt(
            failed_action,
            failed_target,
            error_message,
            available_elements,
            page_context
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at diagnosing UI automation failures and suggesting recovery strategies."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            strategies = self._parse_strategies(result)
            
            logger.info(f"Generated {len(strategies)} recovery strategies")
            for i, strategy in enumerate(strategies, 1):
                logger.info(f"  Strategy {i}: {strategy.description}")
            
            return strategies
            
        except Exception as e:
            logger.error(f"Failed to generate recovery strategies: {e}")
            return []
    
    def _build_recovery_prompt(
        self,
        failed_action: str,
        failed_target: str,
        error_message: str,
        available_elements: List[str],
        page_context: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for recovery suggestion."""
        context_str = ""
        if page_context:
            context_str = f"\nPage Context:\n- URL: {page_context.get('url', 'unknown')}\n- Title: {page_context.get('title', 'unknown')}"
        
        return f"""
Automation action failed. Suggest recovery strategies.

Failed Action: {failed_action}
Target Element: "{failed_target}"
Error: {error_message}
{context_str}

Available Elements on Page:
{self._format_element_list(available_elements[:20])}

Analyze the failure and suggest recovery strategies.
Return JSON:
{{
  "strategies": [
    {{
      "type": "ALTERNATIVE_TARGET|WAIT_LONGER|SCROLL|REGION_CHANGE|RETRY",
      "description": "explanation of strategy",
      "alternative_target": "alternative element text (if applicable)",
      "wait_time": seconds to wait (if applicable)
    }}
  ]
}}

Consider:
1. Is there a similar element with different text?
2. Does the element need more time to appear?
3. Is the element in a specific region/container?
4. Is scrolling required?
5. Could there be a timing issue?

Provide 2-3 most likely strategies, ranked by probability of success.
"""
    
    def _format_element_list(self, elements: List[str]) -> str:
        """Format element list for prompt."""
        return "\n".join([f"- {elem}" for elem in elements if elem])
    
    def _parse_strategies(self, result_json: Dict[str, Any]) -> List[RecoveryStrategy]:
        """Parse JSON result into RecoveryStrategy objects."""
        strategies = []
        
        for strategy_data in result_json.get("strategies", []):
            strategy = RecoveryStrategy(
                strategy_type=strategy_data.get("type", "RETRY"),
                description=strategy_data.get("description", ""),
                alternative_target=strategy_data.get("alternative_target"),
                wait_time=strategy_data.get("wait_time")
            )
            strategies.append(strategy)
        
        return strategies
    
    async def analyze_failure_pattern(
        self,
        failure_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze patterns in failure history.
        
        Args:
            failure_history: List of recent failures
            
        Returns:
            Analysis of failure patterns
        """
        if not failure_history:
            return {"pattern": "NO_FAILURES", "suggestion": "System working correctly"}
        
        logger.info(f"Analyzing failure pattern from {len(failure_history)} failures")
        
        # Build summary of failures
        failure_summary = []
        for failure in failure_history[-10:]:  # Last 10 failures
            failure_summary.append({
                "action": failure.get("action"),
                "target": failure.get("target"),
                "error": failure.get("error")
            })
        
        prompt = f"""
Analyze this pattern of automation failures:

Recent Failures:
{json.dumps(failure_summary, indent=2)}

Identify:
1. Common patterns (same action failing, same targets, etc.)
2. Root cause categories (timing, selector issues, state problems)
3. Recommended fixes

Return JSON:
{{
  "pattern": "description of pattern",
  "root_cause": "likely root cause",
  "recommendations": ["fix1", "fix2", ...]
}}
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Pattern analysis: {result.get('pattern')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to analyze failure pattern: {e}")
            return {"pattern": "ANALYSIS_FAILED", "error": str(e)}
