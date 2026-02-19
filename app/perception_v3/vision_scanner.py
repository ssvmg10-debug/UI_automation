"""
Vision Scanner V3 - OCR + bounding boxes from screenshot.
Optional: only used when VISION_ENABLED=true (Tesseract must be installed).
"""
import os
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

VISION_ENABLED = os.getenv("VISION_ENABLED", "false").lower() == "true"


class VisionScannerV3:
    """Extracts visible text regions + bounding boxes from page screenshot."""

    def __init__(self):
        self._available = False
        if VISION_ENABLED:
            try:
                import pytesseract
                from PIL import Image
                self._available = True
                logger.info("[VISION_V3] Tesseract available")
            except ImportError as e:
                logger.warning("[VISION_V3] Vision disabled: %s (set VISION_ENABLED=true and install pytesseract, Pillow, Tesseract)", e)
        else:
            logger.info("[VISION_V3] Vision disabled (VISION_ENABLED=false)")

    @property
    def available(self) -> bool:
        return self._available

    async def scan(self, page) -> List[Dict[str, Any]]:
        """Extract text + bbox from screenshot via OCR."""
        if not self._available:
            return []

        try:
            import pytesseract
            from PIL import Image
            from io import BytesIO

            screenshot_bytes = await page.screenshot(full_page=True)
            image = Image.open(BytesIO(screenshot_bytes))

            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            results = []

            for i in range(len(data["text"])):
                text = (data["text"][i] or "").strip()
                if not text:
                    continue
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                results.append({
                    "text": text,
                    "bbox": {"x": x, "y": y, "width": w, "height": h},
                    "confidence": data["conf"][i],
                })
            return results
        except Exception as e:
            logger.debug("[VISION_V3] Scan failed: %s", e)
            return []
