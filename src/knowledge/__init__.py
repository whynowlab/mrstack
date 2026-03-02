"""Knowledge module — memory indexing and knowledge base management."""

from .manager import KnowledgeItem, KnowledgeManager
from .memory_index import MemoryIndex

__all__ = ["MemoryIndex", "KnowledgeManager", "KnowledgeItem"]
