"""
DOM extraction and element discovery.
Converts raw Playwright elements to structured DOMElement objects.
"""
from playwright.async_api import Page, Locator
from typing import List, Optional
import logging
from .dom_model import DOMElement, BoundingBox

logger = logging.getLogger(__name__)


class DOMExtractor:
    """Extracts and structures DOM elements for deterministic processing."""
    
    def __init__(self):
        self.element_cache: dict = {}
    
    async def extract_clickables(self, page: Page) -> List[DOMElement]:
        """
        Extract all clickable elements from page.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of structured DOMElement objects
        """
        elements = []
        
        # Selector for clickable elements
        selector = "button, a, [role='button'], [role='link'], input[type='submit'], input[type='button']"
        
        try:
            locator = page.locator(selector)
            count = await locator.count()
            
            logger.info(f"Found {count} potential clickable elements")
            
            for i in range(count):
                element = await self._extract_element(locator.nth(i))
                if element and element.visible:
                    elements.append(element)
            
            logger.info(f"Extracted {len(elements)} visible clickable elements")
            
        except Exception as e:
            logger.error(f"Error extracting clickables: {e}")
        
        return elements
    
    async def extract_inputs(self, page: Page) -> List[DOMElement]:
        """
        Extract all input elements from page.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of structured DOMElement objects
        """
        elements = []
        
        selector = "input, textarea, select"
        
        try:
            locator = page.locator(selector)
            count = await locator.count()
            
            logger.info(f"Found {count} potential input elements")
            
            for i in range(count):
                element = await self._extract_element(locator.nth(i))
                if element and element.visible:
                    elements.append(element)
            
            logger.info(f"Extracted {len(elements)} visible input elements")
            
        except Exception as e:
            logger.error(f"Error extracting inputs: {e}")
        
        return elements
    
    async def extract_all_interactive(self, page: Page) -> List[DOMElement]:
        """
        Extract all interactive elements from page.
        
        Args:
            page: Playwright page object
            
        Returns:
            List of all interactive DOMElement objects
        """
        clickables = await self.extract_clickables(page)
        inputs = await self.extract_inputs(page)
        
        # Combine and deduplicate
        all_elements = clickables + inputs
        
        logger.info(f"Total interactive elements: {len(all_elements)}")
        return all_elements
    
    async def _extract_element(self, locator: Locator) -> Optional[DOMElement]:
        """
        Extract single element with full metadata.
        
        Args:
            locator: Playwright locator
            
        Returns:
            Structured DOMElement or None
        """
        try:
            # Check visibility first
            is_visible = await locator.is_visible()
            if not is_visible:
                return None
            
            # Extract basic properties
            tag = await locator.evaluate("el => el.tagName")
            text = await locator.text_content() or ""
            role = await locator.get_attribute("role")
            
            # Extract bounding box
            bbox_data = await locator.bounding_box()
            bbox = None
            if bbox_data:
                bbox = BoundingBox(
                    x=bbox_data["x"],
                    y=bbox_data["y"],
                    width=bbox_data["width"],
                    height=bbox_data["height"]
                )
            
            # Extract attributes
            attributes = {
                "aria_label": await locator.get_attribute("aria-label"),
                "data_testid": await locator.get_attribute("data-testid"),
                "id": await locator.get_attribute("id"),
                "class": await locator.get_attribute("class"),
                "type": await locator.get_attribute("type"),
                "name": await locator.get_attribute("name"),
                "placeholder": await locator.get_attribute("placeholder"),
                "title": await locator.get_attribute("title"),
                "href": await locator.get_attribute("href"),
            }
            
            # Remove None values
            attributes = {k: v for k, v in attributes.items() if v is not None}
            
            # Extract parent context
            parent_text = await locator.evaluate(
                "el => el.parentElement ? el.parentElement.textContent : null"
            )
            
            # Extract container
            container = await locator.evaluate(
                "el => el.closest('div[class*=\"container\"], section, article, nav, header, footer')?.className || null"
            )
            
            return DOMElement(
                tag=tag,
                text=text.strip(),
                role=role,
                visible=is_visible,
                bounding_box=bbox,
                attributes=attributes,
                parent_text=parent_text,
                container=container
            )
            
        except Exception as e:
            logger.debug(f"Failed to extract element: {e}")
            return None
    
    async def extract_by_region(self, page: Page, region_selector: str) -> List[DOMElement]:
        """
        Extract elements within a specific region.
        
        Args:
            page: Playwright page object
            region_selector: CSS selector for region container
            
        Returns:
            List of DOMElement objects within region
        """
        elements = []
        
        try:
            region = page.locator(region_selector).first
            if not await region.is_visible():
                logger.warning(f"Region not visible: {region_selector}")
                return elements
            
            # Extract clickables within region
            clickables = region.locator("button, a, [role='button']")
            count = await clickables.count()
            
            for i in range(count):
                element = await self._extract_element(clickables.nth(i))
                if element and element.visible:
                    elements.append(element)
            
            logger.info(f"Extracted {len(elements)} elements from region")
            
        except Exception as e:
            logger.error(f"Error extracting from region: {e}")
        
        return elements
    
    def clear_cache(self) -> None:
        """Clear element cache."""
        self.element_cache.clear()
        logger.debug("Element cache cleared")
