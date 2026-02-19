"""
DOM element model and structured representation.
Never use raw DOM - always convert to structured objects.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ElementType(Enum):
    """Types of interactive elements."""
    BUTTON = "button"
    LINK = "link"
    INPUT = "input"
    SELECT = "select"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    TEXTAREA = "textarea"
    UNKNOWN = "unknown"


@dataclass
class BoundingBox:
    """Element position and dimensions."""
    x: float
    y: float
    width: float
    height: float
    
    @property
    def center_x(self) -> float:
        """Get center X coordinate."""
        return self.x + self.width / 2
    
    @property
    def center_y(self) -> float:
        """Get center Y coordinate."""
        return self.y + self.height / 2
    
    @property
    def area(self) -> float:
        """Get element area."""
        return self.width * self.height


@dataclass
class DOMElement:
    """
    Structured representation of a DOM element.
    This is the ONLY way we interact with page elements.
    """
    tag: str
    text: str
    role: Optional[str]
    visible: bool
    bounding_box: Optional[BoundingBox]
    attributes: Dict[str, Any]
    parent_text: Optional[str] = None
    container: Optional[str] = None
    xpath: Optional[str] = None
    css_selector: Optional[str] = None
    
    @property
    def element_type(self) -> ElementType:
        """Determine element type from tag and role."""
        tag_lower = self.tag.lower()
        
        if tag_lower == "button" or self.role == "button":
            return ElementType.BUTTON
        elif tag_lower == "a":
            return ElementType.LINK
        elif tag_lower == "input":
            input_type = self.attributes.get("type", "text")
            if input_type == "checkbox":
                return ElementType.CHECKBOX
            elif input_type == "radio":
                return ElementType.RADIO
            return ElementType.INPUT
        elif tag_lower == "select":
            return ElementType.SELECT
        elif tag_lower == "textarea":
            return ElementType.TEXTAREA
        
        return ElementType.UNKNOWN
    
    @property
    def is_clickable(self) -> bool:
        """Check if element is clickable."""
        return self.element_type in [
            ElementType.BUTTON,
            ElementType.LINK
        ]
    
    @property
    def is_input(self) -> bool:
        """Check if element accepts text input."""
        return self.element_type in [
            ElementType.INPUT,
            ElementType.TEXTAREA
        ]
    
    @property
    def display_name(self) -> str:
        """Get best display name for element."""
        if self.text and self.text.strip():
            return self.text.strip()
        
        aria_label = self.attributes.get("aria_label")
        if aria_label:
            return aria_label
        
        title = self.attributes.get("title")
        if title:
            return title
        
        placeholder = self.attributes.get("placeholder")
        if placeholder:
            return placeholder
        
        return f"{self.tag}_{self.attributes.get('id', 'unknown')}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "tag": self.tag,
            "text": self.text,
            "role": self.role,
            "visible": self.visible,
            "bounding_box": {
                "x": self.bounding_box.x,
                "y": self.bounding_box.y,
                "width": self.bounding_box.width,
                "height": self.bounding_box.height
            } if self.bounding_box else None,
            "attributes": self.attributes,
            "element_type": self.element_type.value,
            "display_name": self.display_name
        }
