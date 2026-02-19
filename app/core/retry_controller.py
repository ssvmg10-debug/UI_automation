"""
Retry controller - intelligent retry logic with backoff.
"""
import asyncio
import logging
from typing import Callable, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 10.0
    exponential_backoff: bool = True


class RetryController:
    """Manages retry logic with exponential backoff."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize retry controller.
        
        Args:
            config: Retry configuration
        """
        self.config = config or RetryConfig()
    
    async def execute_with_retry(
        self,
        action_func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            action_func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception if all retries fail
        """
        last_exception = None
        delay = self.config.initial_delay
        
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                logger.info(f"Attempt {attempt}/{self.config.max_attempts}")
                result = await action_func(*args, **kwargs)
                
                # Check if result indicates success
                if hasattr(result, 'success') and result.success:
                    logger.info(f"✓ Action succeeded on attempt {attempt}")
                    return result
                elif not hasattr(result, 'success'):
                    # If no success attribute, assume success
                    return result
                
                # Result indicates failure
                logger.warning(f"Attempt {attempt} failed, will retry...")
                last_exception = Exception(f"Action failed: {result.error if hasattr(result, 'error') else 'Unknown'}")
                
            except Exception as e:
                logger.warning(f"Attempt {attempt} raised exception: {e}")
                last_exception = e
            
            # Wait before retry (except on last attempt)
            if attempt < self.config.max_attempts:
                await asyncio.sleep(min(delay, self.config.max_delay))
                
                if self.config.exponential_backoff:
                    delay *= self.config.backoff_factor
        
        # All attempts failed
        logger.error(f"All {self.config.max_attempts} attempts failed")
        raise last_exception or Exception("All retry attempts failed")
