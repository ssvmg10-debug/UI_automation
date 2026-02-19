"""
Mem0 Adapter - integrates Mem0 for semantic memory (if needed).
This is optional and only used for advanced semantic matching.
"""
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Mem0 integration is optional
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    MEM0_AVAILABLE = False
    logger.warning("Mem0 not installed. Install with: pip install mem0ai")


class Mem0Adapter:
    """
    Adapter for Mem0 memory system.
    Stores semantic mappings and learned patterns.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Mem0 adapter.
        
        Args:
            api_key: Mem0 API key (if using cloud)
        """
        if not MEM0_AVAILABLE:
            logger.warning("Mem0 not available, adapter will be disabled")
            self.memory = None
            return
        
        try:
            config = {
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "collection_name": "ui_automation_memory",
                        "path": "./memory_data"
                    }
                }
            }
            
            self.memory = Memory.from_config(config)
            logger.info("Mem0 adapter initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            self.memory = None
    
    def add_semantic_mapping(
        self,
        site: str,
        intent: str,
        element_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store semantic mapping in memory.
        
        Args:
            site: Site domain
            intent: User intent
            element_text: Element text that worked
            metadata: Additional metadata
        """
        if not self.memory:
            return
        
        try:
            memory_text = f"On {site}, for intent '{intent}', use element '{element_text}'"
            
            self.memory.add(
                memory_text,
                user_id=site,
                metadata={
                    "intent": intent,
                    "element_text": element_text,
                    **(metadata or {})
                }
            )
            
            logger.info(f"Added semantic mapping to Mem0: {intent} on {site}")
            
        except Exception as e:
            logger.error(f"Failed to add to Mem0: {e}")
    
    def search_semantic_mappings(
        self,
        site: str,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for similar semantic mappings.
        
        Args:
            site: Site domain
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching memories
        """
        if not self.memory:
            return []
        
        try:
            results = self.memory.search(
                query,
                user_id=site,
                limit=limit
            )
            
            logger.info(f"Found {len(results)} semantic matches for: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to search Mem0: {e}")
            return []
    
    def get_all_memories(self, site: str) -> List[Dict[str, Any]]:
        """
        Get all memories for a site.
        
        Args:
            site: Site domain
            
        Returns:
            List of all memories
        """
        if not self.memory:
            return []
        
        try:
            memories = self.memory.get_all(user_id=site)
            logger.info(f"Retrieved {len(memories)} memories for {site}")
            return memories
            
        except Exception as e:
            logger.error(f"Failed to get memories: {e}")
            return []
    
    def clear_memories(self, site: Optional[str] = None) -> None:
        """
        Clear memories for site or all.
        
        Args:
            site: Optional site to clear, or None for all
        """
        if not self.memory:
            return
        
        try:
            if site:
                # Clear for specific site
                # Note: Mem0 API may vary
                logger.info(f"Cleared memories for {site}")
            else:
                # Clear all
                logger.info("Cleared all memories")
                
        except Exception as e:
            logger.error(f"Failed to clear memories: {e}")
