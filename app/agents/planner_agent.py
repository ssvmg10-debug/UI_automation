"""
Planner Agent - converts natural language to structured execution plans.
Does NOT execute - only plans.
"""
from openai import AsyncAzureOpenAI
from typing import List, Dict, Any, Optional
import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class ExecutionStep:
    """Represents a single execution step."""
    
    def __init__(
        self,
        action: str,
        target: str,
        value: Optional[str] = None,
        region: Optional[str] = None
    ):
        self.action = action
        self.target = target
        self.value = value
        self.region = region
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action": self.action,
            "target": self.target,
            "value": self.value,
            "region": self.region
        }
    
    def __repr__(self) -> str:
        if self.value:
            return f"{self.action}('{self.target}', '{self.value}')"
        return f"{self.action}('{self.target}')"


class PlannerAgent:
    """
    AI agent that converts natural language instructions to structured plans.
    This agent does NOT execute actions - it only plans.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize planner agent.
        
        Args:
            api_key: Azure OpenAI API key (uses settings if not provided)
        """
        self.client = AsyncAzureOpenAI(
            api_key=api_key or settings.AZURE_API_KEY,
            api_version=settings.AZURE_API_VERSION,
            azure_endpoint=settings.AZURE_ENDPOINT
        )
        self.model = settings.AZURE_DEPLOYMENT
    
    async def plan(self, instruction_text: str) -> List[ExecutionStep]:
        """
        Convert natural language instruction to structured execution plan.
        
        Args:
            instruction_text: Natural language test instruction
            
        Returns:
            List of ExecutionStep objects
        """
        logger.info("Planning execution from natural language instruction")
        
        prompt = self._build_planning_prompt(instruction_text)
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert test automation planner. Convert natural language test cases into structured execution steps."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result_text = response.choices[0].message.content
            result_json = json.loads(result_text)
            
            steps = self._parse_plan(result_json)
            
            logger.info(f"Generated plan with {len(steps)} steps")
            for i, step in enumerate(steps, 1):
                logger.info(f"  Step {i}: {step}")
            
            return steps
            
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            raise
    
    def _build_planning_prompt(self, instruction_text: str) -> str:
        """Build prompt for planning."""
        return f"""
Convert this test case into structured execution steps.

Test Case:
{instruction_text}

Return a JSON object with this structure:
{{
  "steps": [
    {{
      "action": "NAVIGATE|CLICK|TYPE|WAIT|SELECT",
      "target": "element text or URL",
      "value": "text to type (for TYPE action only)",
      "region": "optional container region"
    }}
  ]
}}

Guidelines:
- Use NAVIGATE for going to URLs
- Use CLICK for clicking buttons/links
- Use TYPE for entering text in inputs
- Use WAIT for waiting for elements to appear
- Use SELECT for dropdown selections
- Be specific with target text
- Extract exact button/link text when possible

Example:
Input: "Go to example.com, click Login, enter email test@test.com, click Submit"
Output:
{{
  "steps": [
    {{"action": "NAVIGATE", "target": "https://example.com"}},
    {{"action": "CLICK", "target": "Login"}},
    {{"action": "TYPE", "target": "Email", "value": "test@test.com"}},
    {{"action": "CLICK", "target": "Submit"}}
  ]
}}
"""
    
    def _parse_plan(self, plan_json: Dict[str, Any]) -> List[ExecutionStep]:
        """Parse JSON plan into ExecutionStep objects."""
        steps = []
        
        for step_data in plan_json.get("steps", []):
            step = ExecutionStep(
                action=step_data.get("action", "").upper(),
                target=step_data.get("target", ""),
                value=step_data.get("value"),
                region=step_data.get("region")
            )
            steps.append(step)
        
        return steps
    
    async def expand_synonyms(self, target_text: str) -> List[str]:
        """
        Generate alternative phrasings for target text.
        Useful for matching elements with different labels.
        
        Args:
            target_text: Original target text
            
        Returns:
            List of alternative phrasings
        """
        logger.info(f"Generating synonyms for: '{target_text}'")
        
        prompt = f"""
Generate 3-5 alternative phrasings or synonyms for this UI element text:
"{target_text}"

Return ONLY a JSON object with this structure:
{{
  "alternatives": ["alternative1", "alternative2", ...]
}}

Consider:
- Common UI patterns (e.g., "Login" vs "Sign In")
- Abbreviations (e.g., "FAQ" vs "Frequently Asked Questions")
- Formal vs casual language
- Action vs noun forms
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            alternatives = result.get("alternatives", [])
            
            logger.info(f"Generated {len(alternatives)} alternatives: {alternatives}")
            return alternatives
            
        except Exception as e:
            logger.error(f"Failed to generate synonyms: {e}")
            return []
    
    async def refine_target_text(
        self, 
        target_text: str, 
        available_elements: List[str],
        context: str = ""
    ) -> str:
        """
        Refine target text based on available elements.
        
        Args:
            target_text: Original target text
            available_elements: List of available element texts
            context: Optional context about the action
            
        Returns:
            Refined target text
        """
        logger.info(f"Refining target text: '{target_text}'")
        
        prompt = f"""
Given the target: "{target_text}"
And available elements: {available_elements}

Select the BEST matching element text from the available list.
Consider semantic meaning, not just exact text match.

Context: {context}

Return ONLY a JSON object:
{{
  "best_match": "exact text from available elements"
}}
"""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            best_match = result.get("best_match", target_text)
            
            logger.info(f"Refined target: '{target_text}' -> '{best_match}'")
            return best_match
            
        except Exception as e:
            logger.error(f"Failed to refine target: {e}")
            return target_text
