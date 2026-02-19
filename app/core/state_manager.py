"""
State management - tracks UI state transitions as a graph.
This enables validation and prevents state drift.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .outcome_validator import PageState

logger = logging.getLogger(__name__)


@dataclass
class StateTransition:
    """Represents a transition between two states."""
    from_state: PageState
    to_state: PageState
    action: str
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    element_used: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "from_state": self.from_state.to_dict(),
            "to_state": self.to_state.to_dict(),
            "action": self.action,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "element_used": self.element_used
        }


class StateGraph:
    """
    Manages state graph for UI automation.
    Tracks valid transitions and enables state validation.
    """
    
    def __init__(self, max_history: int = 100):
        """
        Initialize state graph.
        
        Args:
            max_history: Maximum number of states to keep in history
        """
        self.states: List[PageState] = []
        self.transitions: List[StateTransition] = []
        self.max_history = max_history
        self.valid_transition_patterns: Dict[str, set] = {}
    
    def add_state(self, state: PageState) -> None:
        """
        Add new state to graph.
        
        Args:
            state: PageState to add
        """
        self.states.append(state)
        
        # Trim history if needed
        if len(self.states) > self.max_history:
            self.states = self.states[-self.max_history:]
        
        logger.debug(f"Added state: {state}")
    
    def add_transition(
        self, 
        from_state: PageState,
        to_state: PageState,
        action: str,
        success: bool = True,
        element_used: Optional[str] = None
    ) -> None:
        """
        Record state transition.
        
        Args:
            from_state: Source state
            to_state: Destination state
            action: Action that caused transition
            success: Whether transition was successful
            element_used: Element that was interacted with
        """
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            action=action,
            success=success,
            element_used=element_used
        )
        
        self.transitions.append(transition)
        
        # Record valid pattern
        if success:
            pattern_key = f"{from_state.url}_{action}"
            if pattern_key not in self.valid_transition_patterns:
                self.valid_transition_patterns[pattern_key] = set()
            self.valid_transition_patterns[pattern_key].add(to_state.url)
        
        logger.info(
            f"Recorded transition: {from_state.url} --[{action}]--> {to_state.url}"
        )
    
    def get_current_state(self) -> Optional[PageState]:
        """Get most recent state."""
        return self.states[-1] if self.states else None
    
    def get_previous_state(self) -> Optional[PageState]:
        """Get previous state."""
        return self.states[-2] if len(self.states) >= 2 else None
    
    def get_state_history(self, limit: int = 10) -> List[PageState]:
        """
        Get recent state history.
        
        Args:
            limit: Maximum number of states to return
            
        Returns:
            List of recent states
        """
        return self.states[-limit:]
    
    def get_transition_history(self, limit: int = 10) -> List[StateTransition]:
        """
        Get recent transition history.
        
        Args:
            limit: Maximum number of transitions to return
            
        Returns:
            List of recent transitions
        """
        return self.transitions[-limit:]
    
    def is_valid_transition(self, from_state: PageState, action: str, to_url: str) -> bool:
        """
        Check if transition matches known valid pattern.
        
        Args:
            from_state: Source state
            action: Action being performed
            to_url: Expected destination URL
            
        Returns:
            True if transition matches known valid pattern
        """
        pattern_key = f"{from_state.url}_{action}"
        
        if pattern_key in self.valid_transition_patterns:
            valid_destinations = self.valid_transition_patterns[pattern_key]
            return to_url in valid_destinations
        
        return False
    
    def get_successful_transitions_for_action(self, action: str) -> List[StateTransition]:
        """
        Get all successful transitions for a specific action.
        
        Args:
            action: Action name
            
        Returns:
            List of successful transitions
        """
        return [
            t for t in self.transitions 
            if t.action == action and t.success
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state graph to dictionary."""
        return {
            "states": [s.to_dict() for s in self.states],
            "transitions": [t.to_dict() for t in self.transitions],
            "valid_patterns": {
                k: list(v) for k, v in self.valid_transition_patterns.items()
            }
        }


class StateManager:
    """
    High-level state management for automation session.
    Combines state graph with current page tracking.
    """
    
    def __init__(self):
        """Initialize state manager."""
        self.graph = StateGraph()
        self.current_page = None
    
    async def record_state(
        self, 
        page,
        action: Optional[str] = None,
        element_used: Optional[str] = None
    ) -> PageState:
        """
        Record current page state.
        
        Args:
            page: Playwright page object
            action: Optional action that led to this state
            element_used: Optional element that was used
            
        Returns:
            Captured PageState
        """
        from .outcome_validator import OutcomeValidator
        
        validator = OutcomeValidator()
        state = await validator.capture_state(page)
        
        # Check if this is a transition
        previous_state = self.graph.get_current_state()
        
        if previous_state and action:
            # Record transition
            self.graph.add_transition(
                from_state=previous_state,
                to_state=state,
                action=action,
                success=True,
                element_used=element_used
            )
        
        # Add state to graph
        self.graph.add_state(state)
        
        return state
    
    def get_execution_trace(self) -> List[Dict[str, Any]]:
        """
        Get complete execution trace.
        
        Returns:
            List of transition dictionaries
        """
        return [t.to_dict() for t in self.graph.transitions]
    
    def get_current_state(self) -> Optional[PageState]:
        """Get current state."""
        return self.graph.get_current_state()
    
    def clear_history(self) -> None:
        """Clear state history."""
        self.graph = StateGraph()
        logger.info("State history cleared")
