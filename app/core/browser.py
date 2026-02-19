"""
Browser management layer using Playwright.
Handles browser lifecycle and session management.
"""
from playwright.async_api import async_playwright, Browser, Page, Playwright
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages browser lifecycle and page sessions."""
    
    def __init__(self, headless: bool = True, timeout: int = 30000):
        """
        Initialize browser manager.
        
        Args:
            headless: Run browser in headless mode
            timeout: Default timeout for operations in milliseconds
        """
        self.headless = headless
        self.timeout = timeout
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
    async def start(self) -> Page:
        """
        Start browser and create new page.
        
        Returns:
            Playwright Page object
        """
        try:
            logger.info("Starting browser...")
            self.playwright = await async_playwright().start()
            
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--start-maximized']
            )
            
            self.page = await self.browser.new_page(
                viewport={'width': 1920, 'height': 1080}
            )
            
            # Set default timeout
            self.page.set_default_timeout(self.timeout)
            
            logger.info("Browser started successfully")
            return self.page
            
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise
    
    async def navigate(self, url: str) -> None:
        """
        Navigate to URL.
        
        Args:
            url: Target URL
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        logger.info(f"Navigating to: {url}")
        await self.page.goto(url, wait_until="domcontentloaded")
        
    async def close(self) -> None:
        """Close browser and cleanup resources."""
        try:
            if self.browser:
                await self.browser.close()
                logger.info("Browser closed")
                
            if self.playwright:
                await self.playwright.stop()
                logger.info("Playwright stopped")
                
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
            raise
    
    async def screenshot(self, path: str) -> None:
        """
        Take screenshot of current page.
        
        Args:
            path: File path to save screenshot
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        
        await self.page.screenshot(path=path, full_page=True)
        logger.info(f"Screenshot saved to: {path}")
    
    async def get_page(self) -> Page:
        """
        Get current page object.
        
        Returns:
            Playwright Page object
        """
        if not self.page:
            raise RuntimeError("Browser not started")
        return self.page


class SessionManager:
    """Manages multiple browser sessions for parallel execution."""
    
    def __init__(self):
        self.sessions: dict[str, BrowserManager] = {}
    
    async def create_session(self, session_id: str, headless: bool = True) -> BrowserManager:
        """
        Create new browser session.
        
        Args:
            session_id: Unique session identifier
            headless: Run in headless mode
            
        Returns:
            BrowserManager instance
        """
        if session_id in self.sessions:
            raise ValueError(f"Session {session_id} already exists")
        
        manager = BrowserManager(headless=headless)
        await manager.start()
        self.sessions[session_id] = manager
        
        logger.info(f"Created session: {session_id}")
        return manager
    
    async def get_session(self, session_id: str) -> Optional[BrowserManager]:
        """Get existing session."""
        return self.sessions.get(session_id)
    
    async def close_session(self, session_id: str) -> None:
        """Close and remove session."""
        if session_id in self.sessions:
            await self.sessions[session_id].close()
            del self.sessions[session_id]
            logger.info(f"Closed session: {session_id}")
    
    async def close_all(self) -> None:
        """Close all sessions."""
        for session_id in list(self.sessions.keys()):
            await self.close_session(session_id)
