"""Dashboard Mini App API for Telegram Web App.

Serves a single-page dashboard and JSON APIs for:
- Usage statistics
- Scheduled jobs (list, toggle, run)
- Memory status
- Recent activity timeline
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

logger = structlog.get_logger()

dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Path to dashboard HTML template
_TEMPLATE_DIR = Path(__file__).parent / "templates"


@dashboard_router.get("/", response_class=HTMLResponse)
async def serve_dashboard() -> HTMLResponse:
    """Serve the dashboard HTML."""
    template_path = _TEMPLATE_DIR / "dashboard.html"
    if not template_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard template not found")
    return HTMLResponse(content=template_path.read_text(encoding="utf-8"))


@dashboard_router.get("/api/stats")
async def get_stats(request: Request) -> Dict[str, Any]:
    """Return usage statistics."""
    db_manager = request.app.state.db_manager
    if not db_manager:
        return {"error": "Database not available"}

    try:
        async with db_manager.get_connection() as conn:
            # Total interactions today
            today = datetime.now().strftime("%Y-%m-%d")
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM claude_interactions "
                "WHERE created_at >= ?",
                (today,),
            )
            row = await cursor.fetchone()
            today_count = row[0] if row else 0

            # Total sessions
            cursor = await conn.execute(
                "SELECT COUNT(DISTINCT session_id) FROM claude_interactions"
            )
            row = await cursor.fetchone()
            total_sessions = row[0] if row else 0

            # Active jobs count
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM scheduled_jobs WHERE is_active = 1"
            )
            row = await cursor.fetchone()
            active_jobs = row[0] if row else 0

            return {
                "today_interactions": today_count,
                "total_sessions": total_sessions,
                "active_jobs": active_jobs,
                "timestamp": datetime.now().isoformat(),
            }
    except Exception as e:
        logger.error("Failed to get stats", error=str(e))
        return {"error": str(e)}


@dashboard_router.get("/api/jobs")
async def get_jobs(request: Request) -> List[Dict[str, Any]]:
    """Return scheduled jobs list."""
    db_manager = request.app.state.db_manager
    if not db_manager:
        return []

    try:
        async with db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT job_name, cron_expression, is_active, "
                "last_run_at, next_run_at "
                "FROM scheduled_jobs ORDER BY job_name"
            )
            rows = await cursor.fetchall()

        return [
            {
                "name": row[0],
                "cron": row[1],
                "active": bool(row[2]),
                "last_run": row[3],
                "next_run": row[4],
            }
            for row in rows
        ]
    except Exception as e:
        logger.error("Failed to get jobs", error=str(e))
        return []


@dashboard_router.post("/api/jobs/{name}/toggle")
async def toggle_job(name: str, request: Request) -> Dict[str, Any]:
    """Toggle a scheduled job on/off."""
    db_manager = request.app.state.db_manager
    if not db_manager:
        raise HTTPException(status_code=500, detail="Database not available")

    try:
        async with db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT is_active FROM scheduled_jobs WHERE job_name = ?",
                (name,),
            )
            row = await cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail=f"Job not found: {name}")

            new_state = not bool(row[0])
            await conn.execute(
                "UPDATE scheduled_jobs SET is_active = ? WHERE job_name = ?",
                (int(new_state), name),
            )
            await conn.commit()

        return {"name": name, "active": new_state}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@dashboard_router.post("/api/jobs/{name}/run")
async def run_job(name: str, request: Request) -> Dict[str, Any]:
    """Trigger immediate job execution."""
    event_bus = getattr(request.app.state, "event_bus", None)
    if not event_bus:
        raise HTTPException(status_code=500, detail="Event bus not available")

    from ..events.types import ScheduledEvent

    settings = getattr(request.app.state, "settings", None)
    working_dir = Path(".")
    chat_ids: list = []
    if settings:
        working_dir = settings.approved_directory
        chat_ids = settings.notification_chat_ids or []

    event = ScheduledEvent(
        job_name=name,
        working_directory=working_dir,
        target_chat_ids=chat_ids,
    )
    await event_bus.publish(event)

    return {"name": name, "status": "triggered"}


@dashboard_router.get("/api/memory")
async def get_memory(request: Request) -> Dict[str, Any]:
    """Return memory system status."""
    memory_dir = Path.home() / "claude-telegram" / "memory"
    if not memory_dir.exists():
        return {"status": "not_configured", "files": []}

    files = []
    for p in sorted(memory_dir.rglob("*.md")):
        rel = p.relative_to(memory_dir)
        files.append({
            "path": str(rel),
            "size": p.stat().st_size,
            "modified": datetime.fromtimestamp(p.stat().st_mtime).isoformat(),
        })

    patterns_file = memory_dir / "patterns" / "interactions.jsonl"
    interaction_count = 0
    if patterns_file.exists():
        interaction_count = sum(1 for _ in patterns_file.open())

    return {
        "status": "active",
        "file_count": len(files),
        "files": files[:20],
        "interaction_count": interaction_count,
    }


@dashboard_router.get("/api/activity")
async def get_activity(request: Request) -> List[Dict[str, Any]]:
    """Return recent interaction timeline."""
    db_manager = request.app.state.db_manager
    if not db_manager:
        return []

    try:
        async with db_manager.get_connection() as conn:
            cursor = await conn.execute(
                "SELECT prompt, session_id, created_at "
                "FROM claude_interactions "
                "ORDER BY created_at DESC LIMIT 20"
            )
            rows = await cursor.fetchall()

        return [
            {
                "prompt": row[0][:100] if row[0] else "",
                "session_id": row[1][:8] if row[1] else "",
                "timestamp": row[2],
            }
            for row in rows
        ]
    except Exception as e:
        logger.error("Failed to get activity", error=str(e))
        return []
