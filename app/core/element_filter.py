"""
Element filtering - applies hard constraints to reduce search space.
No AI involved - pure deterministic logic.
"""
from typing import List
from .dom_model import DOMElement, ElementType
import logging

logger = logging.getLogger(__name__)


class ElementFilter:
    """Applies deterministic filtering rules to element lists."""
    
    def __init__(self):
        self.filters_applied = []
    
    def filter_by_action_type(self, elements: List[DOMElement], action_type: str) -> List[DOMElement]:
        """
        Filter elements based on intended action type.
        
        Args:
            elements: List of DOMElement objects
            action_type: Action to perform (CLICK, TYPE, SELECT)
            
        Returns:
            Filtered list of elements
        """
        action_type = action_type.upper()
        
        if action_type == "CLICK":
            filtered = [e for e in elements if e.is_clickable]
        elif action_type == "TYPE":
            filtered = [e for e in elements if e.is_input]
        elif action_type == "SELECT":
            filtered = [e for e in elements if e.element_type == ElementType.SELECT]
        else:
            filtered = elements
        
        logger.debug(f"Filtered by action type {action_type}: {len(filtered)}/{len(elements)}")
        return filtered
    
    def filter_by_visibility(self, elements: List[DOMElement]) -> List[DOMElement]:
        """
        Filter to only visible elements.
        
        Args:
            elements: List of DOMElement objects
            
        Returns:
            Only visible elements
        """
        filtered = [e for e in elements if e.visible]
        logger.debug(f"Filtered by visibility: {len(filtered)}/{len(elements)}")
        return filtered
    
    def filter_by_region(self, elements: List[DOMElement], region_name: str) -> List[DOMElement]:
        """
        Filter elements by container region.
        
        Args:
            elements: List of DOMElement objects
            region_name: Name of container region
            
        Returns:
            Elements within specified region
        """
        filtered = [
            e for e in elements 
            if e.container and region_name.lower() in e.container.lower()
        ]
        
        logger.debug(f"Filtered by region '{region_name}': {len(filtered)}/{len(elements)}")
        return filtered
    
    def filter_by_position(
        self, 
        elements: List[DOMElement], 
        min_y: float = 0, 
        max_y: float = float('inf')
    ) -> List[DOMElement]:
        """
        Filter elements by vertical position on page.
        
        Args:
            elements: List of DOMElement objects
            min_y: Minimum Y coordinate
            max_y: Maximum Y coordinate
            
        Returns:
            Elements within Y range
        """
        filtered = [
            e for e in elements 
            if e.bounding_box and min_y <= e.bounding_box.y <= max_y
        ]
        
        logger.debug(f"Filtered by position: {len(filtered)}/{len(elements)}")
        return filtered
    
    def filter_by_size(
        self, 
        elements: List[DOMElement], 
        min_area: float = 10.0
    ) -> List[DOMElement]:
        """
        Filter out elements that are too small (likely decorative).
        
        Args:
            elements: List of DOMElement objects
            min_area: Minimum element area in pixels
            
        Returns:
            Elements above minimum size
        """
        filtered = [
            e for e in elements 
            if e.bounding_box and e.bounding_box.area >= min_area
        ]
        
        logger.debug(f"Filtered by size: {len(filtered)}/{len(elements)}")
        return filtered
    
    def filter_empty_text(self, elements: List[DOMElement]) -> List[DOMElement]:
        """
        Filter out elements with no text or label.
        
        Args:
            elements: List of DOMElement objects
            
        Returns:
            Elements with text or aria-label
        """
        filtered = [
            e for e in elements 
            if e.text or e.attributes.get("aria_label")
        ]
        
        logger.debug(f"Filtered empty text: {len(filtered)}/{len(elements)}")
        return filtered
    
    def filter_by_tag(self, elements: List[DOMElement], allowed_tags: List[str]) -> List[DOMElement]:
        """
        Filter to only allowed HTML tags.
        
        Args:
            elements: List of DOMElement objects
            allowed_tags: List of allowed tag names
            
        Returns:
            Elements with allowed tags
        """
        allowed_tags_upper = [tag.upper() for tag in allowed_tags]
        filtered = [
            e for e in elements 
            if e.tag.upper() in allowed_tags_upper
        ]
        
        logger.debug(f"Filtered by tags: {len(filtered)}/{len(elements)}")
        return filtered
    
    def apply_standard_filters(
        self, 
        elements: List[DOMElement], 
        action_type: str
    ) -> List[DOMElement]:
        """
        Apply standard filter chain for an action.
        
        Args:
            elements: List of DOMElement objects
            action_type: Action to perform
            
        Returns:
            Filtered elements ready for ranking
        """
        filtered = elements
        
        # Chain filters
        filtered = self.filter_by_visibility(filtered)
        filtered = self.filter_by_action_type(filtered, action_type)
        filtered = self.filter_by_size(filtered)
        
        if action_type.upper() == "CLICK":
            filtered = self.filter_empty_text(filtered)
        
        logger.info(f"Standard filters applied: {len(elements)} -> {len(filtered)} elements")
        return filtered
