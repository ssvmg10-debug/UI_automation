"""
Flow optimization: fragment reuse, URL shortcuts, state shortcuts, step dedup.
No XPath/CSS/handles stored; only action intent, URLs, DOM hash.
"""
from .state_signature import generate_state_signature
from .fragment_model import FlowFragment
from .fragment_store import FragmentStore
from .fragment_matcher import FragmentMatcher
from .url_shortcut_registry import URLShortcutRegistry
from .state_shortcut import StateShortcutRegistry
from .step_dedup import deduplicate_steps
from .optimizer_engine import OptimizerEngine

__all__ = [
    "generate_state_signature",
    "FlowFragment",
    "FragmentStore",
    "FragmentMatcher",
    "URLShortcutRegistry",
    "StateShortcutRegistry",
    "deduplicate_steps",
    "OptimizerEngine",
]
