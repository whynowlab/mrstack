"""Memory index for efficient context retrieval.

Scans ~/claude-telegram/memory/ and builds a keyword index so that
only relevant memory snippets are injected into Claude's system prompt,
instead of dumping all memory files every call.
"""

import json
import os
import re
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()


class MemoryIndex:
    """Indexes memory files and retrieves relevant context by keyword match."""

    SCAN_DIRS = ["people", "projects", "preferences", "knowledge", "decisions"]

    def __init__(self, memory_dir: str = "~/claude-telegram/memory/"):
        self.memory_dir = Path(memory_dir).expanduser()
        self.index_path = self.memory_dir / "index.json"
        self.knowledge_dir = Path("~/claude-telegram/knowledge/").expanduser()
        self.knowledge_index_path = self.knowledge_dir / "index.json"
        self._index: list[dict] = []
        self._knowledge_index: list[dict] = []

    def rebuild_index(self) -> list[dict]:
        """Scan all memory files and build index.json with summaries."""
        entries = []

        for subdir in self.SCAN_DIRS:
            dir_path = self.memory_dir / subdir
            if not dir_path.is_dir():
                continue

            for md_file in dir_path.glob("*.md"):
                try:
                    text = md_file.read_text(encoding="utf-8", errors="ignore")
                    lines = [l.strip() for l in text.splitlines() if l.strip()]
                    summary = " ".join(lines[:5])[:300]
                    keywords = self._extract_keywords(text)

                    entries.append({
                        "path": str(md_file.relative_to(self.memory_dir)),
                        "category": subdir,
                        "summary": summary,
                        "keywords": keywords,
                    })
                except Exception as e:
                    logger.debug("Failed to index memory file", path=str(md_file), error=str(e))

        self._index = entries

        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("Failed to write memory index", error=str(e))

        # Also load knowledge index if it exists
        self._load_knowledge_index()

        logger.info("Memory index rebuilt", entry_count=len(entries))
        return entries

    def _load_knowledge_index(self) -> None:
        """Load knowledge base index for combined search."""
        if self.knowledge_index_path.exists():
            try:
                with open(self.knowledge_index_path, encoding="utf-8") as f:
                    self._knowledge_index = json.load(f)
            except Exception:
                self._knowledge_index = []

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text (local, no LLM call)."""
        text_lower = text.lower()
        # Remove markdown headers, links, formatting
        text_clean = re.sub(r'[#*\[\]()>`_~|]', ' ', text_lower)
        # Split and filter
        words = re.findall(r'[a-z가-힣]{2,}', text_clean)
        # Count frequency, keep top keywords
        freq: dict[str, int] = {}
        stop_words = {
            "the", "and", "for", "that", "this", "with", "from", "have",
            "are", "was", "were", "been", "will", "not", "but", "all",
            "can", "has", "had", "its", "you", "your", "they", "what",
            "에서", "으로", "에서", "하는", "있는", "하고", "그리고",
            "또는", "대한", "위한", "통해", "에서의", "것을",
        }
        for w in words:
            if w not in stop_words and len(w) > 1:
                freq[w] = freq.get(w, 0) + 1

        sorted_kw = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [kw for kw, _ in sorted_kw[:20]]

    def get_relevant_context(self, query: str, max_tokens: int = 500) -> str:
        """Return memory snippets relevant to the query.

        Uses keyword matching against the index (no LLM call, zero tokens).
        """
        if not self._index:
            # Try loading from disk
            if self.index_path.exists():
                try:
                    with open(self.index_path, encoding="utf-8") as f:
                        self._index = json.load(f)
                except Exception:
                    return ""
            if not self._index:
                return ""

        query_keywords = set(self._extract_keywords(query))
        if not query_keywords:
            return ""

        # Score each entry by keyword overlap
        scored = []
        for entry in self._index:
            overlap = query_keywords & set(entry.get("keywords", []))
            if overlap:
                scored.append((len(overlap), entry))

        # Also search knowledge index
        knowledge_matches = []
        if self._knowledge_index:
            for item in self._knowledge_index:
                item_text = f"{item.get('title', '')} {item.get('summary', '')} {' '.join(item.get('tags', []))}"
                item_keywords = set(self._extract_keywords(item_text))
                overlap = query_keywords & item_keywords
                if overlap:
                    knowledge_matches.append((len(overlap), item))

        if not scored and not knowledge_matches:
            return ""

        # Build context string within token budget (approx 4 chars per token)
        char_budget = max_tokens * 4
        parts = []

        # Memory context
        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            parts.append("[Memory Context]")
            for _, entry in scored[:3]:
                snippet = f"- [{entry['category']}] {entry['summary']}"
                parts.append(snippet)

        # Knowledge context
        if knowledge_matches:
            knowledge_matches.sort(key=lambda x: x[0], reverse=True)
            parts.append("\n[Knowledge]")
            for _, item in knowledge_matches[:3]:
                snippet = f"- [{item.get('category', '?')}] {item.get('title', '?')}: {item.get('summary', '')[:150]}"
                parts.append(snippet)

        result = "\n".join(parts)
        if len(result) > char_budget:
            result = result[:char_budget] + "..."

        return result

    def load_index(self) -> None:
        """Load existing index from disk (called at startup)."""
        if self.index_path.exists():
            try:
                with open(self.index_path, encoding="utf-8") as f:
                    self._index = json.load(f)
                logger.info("Memory index loaded", entry_count=len(self._index))
            except Exception as e:
                logger.warning("Failed to load memory index", error=str(e))
                self._index = []
        self._load_knowledge_index()
