"""
Analytics API routes.
Exposes conversation history, latency metrics, and error logs.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Query

from app.services.analytics_service import get_all_entries, get_summary, clear_analytics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/conversations")
async def list_conversations(
    mode: Optional[str] = Query(None, description="Filter by mode: 'chat' or 'voice'"),
    status: Optional[str] = Query(None, description="Filter by status: 'success' or 'error'"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    List all conversation entries with optional filtering.
    Returns entries newest-first with latency breakdowns and error info.
    """
    return get_all_entries(mode=mode, status=status, limit=limit, offset=offset)


@router.get("/summary")
async def analytics_summary():
    """
    Get aggregate analytics summary:
    total conversations, mode breakdown, error rate, average latencies.
    """
    return get_summary()


@router.delete("/clear")
async def clear_all_analytics():
    """Clear all stored analytics data."""
    clear_analytics()
    return {"message": "Analytics data cleared."}
