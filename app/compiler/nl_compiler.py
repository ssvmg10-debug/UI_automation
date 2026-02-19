"""
Natural language compiler - converts text to structured instructions.
"""
import re
from typing import List, Optional
import logging

from .instruction_model import Instruction, TestCase, ActionType

logger = logging.getLogger(__name__)


class NaturalLanguageCompiler:
    """
    Compiles natural language test cases into structured instructions.
    Basic rule-based compiler (can be enhanced with AI).
    """
    
    # Pattern matching rules
    PATTERNS = {
        ActionType.NAVIGATE: [
            r"go to (.+)",
            r"navigate to (.+)",
            r"open (.+)",
            r"visit (.+)"
        ],
        ActionType.CLICK: [
            r"click (?:on )?['\"]?(.+?)['\"]?(?:\s+button|\s+link)?",
            r"tap (?:on )?['\"]?(.+?)['\"]?",
            r"press ['\"]?(.+?)['\"]?"
        ],
        ActionType.TYPE: [
            r"type ['\"]?(.+?)['\"]? (?:in|into) ['\"]?(.+?)['\"]?",
            r"enter ['\"]?(.+?)['\"]? (?:in|into) ['\"]?(.+?)['\"]?",
            r"fill ['\"]?(.+?)['\"]? with ['\"]?(.+?)['\"]?"
        ],
        ActionType.WAIT: [
            r"wait for ['\"]?(.+?)['\"]?",
            r"wait until ['\"]?(.+?)['\"]? (?:appears|is visible)"
        ],
        ActionType.ASSERT: [
            r"verify ['\"]?(.+?)['\"]? (?:is|contains) ['\"]?(.+?)['\"]?",
            r"assert ['\"]?(.+?)['\"]?",
            r"check ['\"]?(.+?)['\"]?"
        ]
    }
    
    def compile(self, text: str, name: Optional[str] = None) -> TestCase:
        """
        Compile natural language test case.
        
        Args:
            text: Natural language test description
            name: Optional test name
            
        Returns:
            Structured TestCase object
        """
        logger.info("Compiling natural language test case")
        
        # Split into lines/steps
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        # Extract name if present
        if not name and lines:
            first_line = lines[0]
            if first_line.startswith('#') or first_line.lower().startswith('test:'):
                name = first_line.lstrip('#').replace('Test:', '').strip()
                lines = lines[1:]
        
        # Compile each line to instruction
        instructions = []
        for line in lines:
            instruction = self._compile_line(line)
            if instruction:
                instructions.append(instruction)
        
        test_case = TestCase(
            name=name or "Unnamed Test",
            description=text,
            instructions=instructions
        )
        
        logger.info(f"Compiled test case with {len(instructions)} instructions")
        return test_case
    
    def _compile_line(self, line: str) -> Optional[Instruction]:
        """
        Compile single line to instruction.
        
        Args:
            line: Single line of test description
            
        Returns:
            Instruction or None if line doesn't match patterns
        """
        line_lower = line.lower().strip()
        
        # Try to match against patterns
        for action_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                match = re.match(pattern, line_lower)
                if match:
                    return self._create_instruction(action_type, match.groups(), line)
        
        logger.warning(f"Could not compile line: {line}")
        return None
    
    def _create_instruction(
        self, 
        action_type: ActionType, 
        groups: tuple,
        original_line: str
    ) -> Instruction:
        """
        Create instruction from matched groups.
        
        Args:
            action_type: Type of action
            groups: Regex match groups
            original_line: Original line text
            
        Returns:
            Instruction object
        """
        if action_type == ActionType.TYPE:
            # For TYPE: groups are (value, target) or (target, value)
            # Our pattern is "type VALUE in TARGET"
            if len(groups) >= 2:
                return Instruction(
                    action=action_type,
                    target=groups[1],  # target field
                    value=groups[0]    # value to type
                )
        
        elif action_type == ActionType.ASSERT:
            # For ASSERT: can have expected value
            if len(groups) >= 2:
                return Instruction(
                    action=action_type,
                    target=groups[0],
                    expected_outcome=groups[1]
                )
        
        # Default: first group is target
        target = groups[0] if groups else original_line
        
        return Instruction(
            action=action_type,
            target=target
        )
    
    def compile_from_file(self, file_path: str) -> List[TestCase]:
        """
        Compile test cases from file.
        
        Args:
            file_path: Path to test file
            
        Returns:
            List of compiled test cases
        """
        logger.info(f"Compiling test cases from file: {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Split by test case markers (e.g., "## Test:" or "---")
        test_blocks = re.split(r'(?:^|\n)(?:##\s*Test:|\-{3,})', content)
        
        test_cases = []
        for block in test_blocks:
            if block.strip():
                test_case = self.compile(block.strip())
                test_cases.append(test_case)
        
        logger.info(f"Compiled {len(test_cases)} test cases from file")
        return test_cases
