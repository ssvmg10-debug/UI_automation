"""
Pattern Registry - stores proven successful element interactions.
Helps improve future matching by remembering what worked.
"""
from typing import Dict, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class SuccessPattern:
    """Represents a successful interaction pattern."""
    site: str
    intent: str  # What user wanted to do
    canonical_label: str  # Text that worked
    alternative_labels: Set[str] = field(default_factory=set)
    success_count: int = 0
    last_success: datetime = field(default_factory=datetime.now)
    transition_signature: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "site": self.site,
            "intent": self.intent,
            "canonical_label": self.canonical_label,
            "alternative_labels": list(self.alternative_labels),
            "success_count": self.success_count,
            "last_success": self.last_success.isoformat(),
            "transition_signature": self.transition_signature
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SuccessPattern':
        """Create from dictionary."""
        return cls(
            site=data["site"],
            intent=data["intent"],
            canonical_label=data["canonical_label"],
            alternative_labels=set(data.get("alternative_labels", [])),
            success_count=data.get("success_count", 0),
            last_success=datetime.fromisoformat(data["last_success"]),
            transition_signature=data.get("transition_signature")
        )


class PatternRegistry:
    """
    Registry of successful automation patterns.
    NOT for storing raw selectors - stores semantic patterns.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize pattern registry.
        
        Args:
            storage_path: Optional path to persist patterns
        """
        self.patterns: Dict[str, SuccessPattern] = {}
        self.storage_path = storage_path
        
        if storage_path:
            self._load_patterns()
    
    def _make_key(self, site: str, intent: str) -> str:
        """Create unique key for pattern."""
        return f"{site}::{intent}".lower()
    
    def record_success(
        self,
        site: str,
        intent: str,
        label_used: str,
        transition_signature: Optional[str] = None
    ) -> None:
        """
        Record successful interaction.
        
        Args:
            site: Site domain (e.g., "lg.com")
            intent: User intent (e.g., "checkout_as_guest")
            label_used: Element text that worked
            transition_signature: Optional signature of state transition
        """
        key = self._make_key(site, intent)
        
        if key in self.patterns:
            # Update existing pattern
            pattern = self.patterns[key]
            pattern.success_count += 1
            pattern.last_success = datetime.now()
            pattern.alternative_labels.add(label_used)
            
            logger.info(f"Updated pattern: {intent} on {site} (count: {pattern.success_count})")
        else:
            # Create new pattern
            pattern = SuccessPattern(
                site=site,
                intent=intent,
                canonical_label=label_used,
                success_count=1,
                transition_signature=transition_signature
            )
            pattern.alternative_labels.add(label_used)
            self.patterns[key] = pattern
            
            logger.info(f"Created new pattern: {intent} on {site}")
        
        if self.storage_path:
            self._save_patterns()
    
    def get_pattern(self, site: str, intent: str) -> Optional[SuccessPattern]:
        """
        Get stored pattern for site and intent.
        
        Args:
            site: Site domain
            intent: User intent
            
        Returns:
            SuccessPattern if found, None otherwise
        """
        key = self._make_key(site, intent)
        pattern = self.patterns.get(key)
        
        if pattern:
            logger.info(
                f"Found pattern: {intent} on {site} "
                f"(success_count: {pattern.success_count})"
            )
        
        return pattern
    
    def get_known_labels(self, site: str, intent: str) -> List[str]:
        """
        Get all known working labels for site/intent.
        
        Args:
            site: Site domain
            intent: User intent
            
        Returns:
            List of known working labels
        """
        pattern = self.get_pattern(site, intent)
        
        if pattern:
            return [pattern.canonical_label] + list(pattern.alternative_labels)
        
        return []
    
    def get_patterns_for_site(self, site: str) -> List[SuccessPattern]:
        """
        Get all patterns for a specific site.
        
        Args:
            site: Site domain
            
        Returns:
            List of patterns for site
        """
        return [
            pattern for key, pattern in self.patterns.items()
            if pattern.site.lower() == site.lower()
        ]
    
    def get_top_patterns(self, limit: int = 10) -> List[SuccessPattern]:
        """
        Get top patterns by success count.
        
        Args:
            limit: Maximum patterns to return
            
        Returns:
            List of top patterns
        """
        sorted_patterns = sorted(
            self.patterns.values(),
            key=lambda p: p.success_count,
            reverse=True
        )
        return sorted_patterns[:limit]
    
    def _save_patterns(self) -> None:
        """Persist patterns to storage."""
        if not self.storage_path:
            return
        
        try:
            data = {
                key: pattern.to_dict()
                for key, pattern in self.patterns.items()
            }
            
            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.debug(f"Saved {len(data)} patterns to {self.storage_path}")
            
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")
    
    def _load_patterns(self) -> None:
        """Load patterns from storage."""
        if not self.storage_path:
            return
        
        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
            
            self.patterns = {
                key: SuccessPattern.from_dict(pattern_data)
                for key, pattern_data in data.items()
            }
            
            logger.info(f"Loaded {len(self.patterns)} patterns from {self.storage_path}")
            
        except FileNotFoundError:
            logger.info("No existing pattern file found, starting fresh")
        except Exception as e:
            logger.error(f"Failed to load patterns: {e}")
    
    def clear(self) -> None:
        """Clear all patterns."""
        self.patterns.clear()
        logger.info("Pattern registry cleared")
