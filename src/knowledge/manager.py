"""Knowledge base manager — ingest, classify, and search user-provided knowledge.

Triggered only when the user includes "학습" in their message.
Stores summaries in ~/claude-telegram/knowledge/items/{uuid}.md
with a catalog in ~/claude-telegram/knowledge/index.json.
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()


@dataclass
class KnowledgeItem:
    """A single knowledge entry."""

    id: str
    title: str
    category: str
    tags: list[str]
    summary: str
    source_type: str  # "url", "text", "image"
    source_ref: str  # original URL or filename
    created_at: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "tags": self.tags,
            "summary": self.summary,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "created_at": self.created_at,
        }


class KnowledgeManager:
    """Manages knowledge ingestion, storage, and retrieval."""

    CATEGORIES = ["tech", "business", "research", "reference"]

    def __init__(
        self,
        knowledge_dir: str = "~/claude-telegram/knowledge/",
        claude_integration=None,
    ):
        self.knowledge_dir = Path(knowledge_dir).expanduser()
        self.items_dir = self.knowledge_dir / "items"
        self.index_path = self.knowledge_dir / "index.json"
        self.claude = claude_integration
        self._index: list[dict] = []

        # Ensure directories exist
        self.items_dir.mkdir(parents=True, exist_ok=True)
        self._load_index()

    def _load_index(self) -> None:
        """Load catalog from disk."""
        if self.index_path.exists():
            try:
                with open(self.index_path, encoding="utf-8") as f:
                    self._index = json.load(f)
            except Exception:
                self._index = []

    def _save_index(self) -> None:
        """Persist catalog to disk."""
        try:
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump(self._index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Failed to save knowledge index", error=str(e))

    async def ingest_url(self, url: str, working_directory=None) -> KnowledgeItem:
        """Fetch URL content via Claude, summarize, classify, and store."""
        prompt = (
            f"다음 URL의 내용을 분석해주세요: {url}\n\n"
            "1. WebFetch 도구로 URL 내용을 가져와주세요\n"
            "2. 아래 JSON 형식으로만 응답해주세요 (다른 텍스트 없이):\n"
            '```json\n'
            '{\n'
            '  "title": "제목",\n'
            '  "category": "tech|business|research|reference 중 하나",\n'
            '  "tags": ["태그1", "태그2", "태그3"],\n'
            '  "summary": "핵심 내용 3-5문장 요약",\n'
            '  "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"]\n'
            '}\n'
            '```'
        )

        parsed = await self._call_claude_for_classification(prompt, working_directory)
        return self._store_item(parsed, source_type="url", source_ref=url)

    async def ingest_text(
        self, text: str, filename: Optional[str] = None, working_directory=None
    ) -> KnowledgeItem:
        """Summarize and classify text/file content."""
        # Truncate if too long
        if len(text) > 30000:
            text = text[:30000] + "\n... (truncated)"

        source = filename or "direct_text"
        prompt = (
            f"다음 텍스트 내용을 분석해주세요:\n\n{text}\n\n"
            "아래 JSON 형식으로만 응답해주세요 (다른 텍스트 없이):\n"
            '```json\n'
            '{\n'
            '  "title": "제목",\n'
            '  "category": "tech|business|research|reference 중 하나",\n'
            '  "tags": ["태그1", "태그2", "태그3"],\n'
            '  "summary": "핵심 내용 3-5문장 요약",\n'
            '  "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3"]\n'
            '}\n'
            '```'
        )

        parsed = await self._call_claude_for_classification(prompt, working_directory)
        return self._store_item(parsed, source_type="text", source_ref=source)

    async def ingest_image(
        self, image_path: str, caption: str = "", working_directory=None
    ) -> KnowledgeItem:
        """Analyze image via Claude and store as knowledge."""
        prompt = (
            f"이미지를 분석해서 학습 자료로 정리해주세요.\n"
            f"이미지 파일 경로: {image_path}\n"
            f"Read 도구로 이 이미지 파일을 읽어서 분석해주세요.\n"
        )
        if caption:
            prompt += f"사용자 메모: {caption}\n"

        prompt += (
            "\n아래 JSON 형식으로만 응답해주세요 (다른 텍스트 없이):\n"
            '```json\n'
            '{\n'
            '  "title": "제목",\n'
            '  "category": "tech|business|research|reference 중 하나",\n'
            '  "tags": ["태그1", "태그2", "태그3"],\n'
            '  "summary": "이미지 내용 3-5문장 요약",\n'
            '  "key_points": ["핵심 포인트 1", "핵심 포인트 2"]\n'
            '}\n'
            '```'
        )

        parsed = await self._call_claude_for_classification(prompt, working_directory)
        return self._store_item(parsed, source_type="image", source_ref=image_path)

    async def _call_claude_for_classification(
        self, prompt: str, working_directory=None
    ) -> dict:
        """Call Claude once to get classification + summary."""
        if not self.claude:
            logger.warning("No Claude integration for knowledge classification")
            return {
                "title": "Untitled",
                "category": "reference",
                "tags": [],
                "summary": "분류 실패 — Claude 연동 없음",
                "key_points": [],
            }

        try:
            from pathlib import Path

            wd = working_directory or Path.home()
            response = await self.claude.run_command(
                prompt=prompt,
                working_directory=wd,
                user_id=0,
                force_new=True,
                model="sonnet",
            )

            return self._parse_json_response(response.content)
        except Exception as e:
            logger.error("Knowledge classification failed", error=str(e))
            return {
                "title": "Untitled",
                "category": "reference",
                "tags": [],
                "summary": f"분류 실패: {str(e)[:100]}",
                "key_points": [],
            }

    def _parse_json_response(self, text: str) -> dict:
        """Extract JSON from Claude's response."""
        # Try to find JSON block
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try parsing the whole text as JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Fallback: extract what we can
        return {
            "title": text[:50].strip(),
            "category": "reference",
            "tags": [],
            "summary": text[:300].strip(),
            "key_points": [],
        }

    def _store_item(
        self, parsed: dict, source_type: str, source_ref: str
    ) -> KnowledgeItem:
        """Save knowledge item to disk and update index."""
        item_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        # Validate category
        category = parsed.get("category", "reference")
        if category not in self.CATEGORIES:
            category = "reference"

        item = KnowledgeItem(
            id=item_id,
            title=parsed.get("title", "Untitled"),
            category=category,
            tags=parsed.get("tags", []),
            summary=parsed.get("summary", ""),
            source_type=source_type,
            source_ref=source_ref,
            created_at=now,
        )

        # Write detailed item file
        key_points = parsed.get("key_points", [])
        md_content = (
            f"# {item.title}\n\n"
            f"- **Category:** {item.category}\n"
            f"- **Tags:** {', '.join(item.tags)}\n"
            f"- **Source:** {source_type} — {source_ref}\n"
            f"- **Created:** {now}\n\n"
            f"## Summary\n\n{item.summary}\n\n"
        )
        if key_points:
            md_content += "## Key Points\n\n"
            for point in key_points:
                md_content += f"- {point}\n"

        item_path = self.items_dir / f"{item_id}.md"
        try:
            item_path.write_text(md_content, encoding="utf-8")
        except Exception as e:
            logger.error("Failed to write knowledge item", error=str(e))

        # Update index
        self._index.append(item.to_dict())
        self._save_index()

        logger.info(
            "Knowledge item stored",
            id=item_id,
            title=item.title,
            category=item.category,
        )

        return item

    def search(self, query: str, limit: int = 5) -> list[KnowledgeItem]:
        """Search knowledge base by keyword/tag matching (local, zero tokens)."""
        query_lower = query.lower()
        query_words = set(re.findall(r'[a-z가-힣]{2,}', query_lower))

        scored = []
        for entry in self._index:
            score = 0
            # Title match
            if any(w in entry.get("title", "").lower() for w in query_words):
                score += 3
            # Tag match
            for tag in entry.get("tags", []):
                if any(w in tag.lower() for w in query_words):
                    score += 2
            # Summary match
            if any(w in entry.get("summary", "").lower() for w in query_words):
                score += 1
            # Category match
            if any(w in entry.get("category", "").lower() for w in query_words):
                score += 1

            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)

        return [
            KnowledgeItem(**{k: v for k, v in e.items() if k != "key_points"})
            for _, e in scored[:limit]
        ]

    def get_stats(self) -> dict:
        """Return knowledge base statistics."""
        categories: dict[str, int] = {}
        for item in self._index:
            cat = item.get("category", "unknown")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "total_items": len(self._index),
            "categories": categories,
        }
