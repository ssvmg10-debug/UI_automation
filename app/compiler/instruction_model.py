"""
Instruction model - structured representation of test instructions.
"""
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class ActionType(Enum):
    """Types of automation actions."""
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE = "type"
    SELECT = "select"
    WAIT = "wait"
    ASSERT = "assert"
    SCROLL = "scroll"
    HOVER = "hover"


@dataclass
class Instruction:
    """Single automation instruction."""
    action: ActionType
    target: str
    value: Optional[str] = None
    region: Optional[str] = None
    timeout: Optional[int] = None
    expected_outcome: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action": self.action.value,
            "target": self.target,
            "value": self.value,
            "region": self.region,
            "timeout": self.timeout,
            "expected_outcome": self.expected_outcome
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Instruction':
        """Create from dictionary."""
        return cls(
            action=ActionType(data["action"]),
            target=data["target"],
            value=data.get("value"),
            region=data.get("region"),
            timeout=data.get("timeout"),
            expected_outcome=data.get("expected_outcome")
        )
    
    def __repr__(self) -> str:
        if self.value:
            return f"{self.action.value}('{self.target}', '{self.value}')"
        return f"{self.action.value}('{self.target}')"


@dataclass
class TestCase:
    """Complete test case with metadata."""
    name: str
    description: str
    instructions: List[Instruction]
    tags: List[str] = None
    priority: str = "medium"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "instructions": [i.to_dict() for i in self.instructions],
            "tags": self.tags or [],
            "priority": self.priority
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            instructions=[Instruction.from_dict(i) for i in data["instructions"]],
            tags=data.get("tags", []),
            priority=data.get("priority", "medium")
        )
