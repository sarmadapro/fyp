"""
Analytics service — In-memory conversation and latency tracking.

Captures:
- Every conversation exchange (user query → AI response)
- Mode (chat vs voice)
- Per-pipeline-stage latency breakdown
- Errors that occurred during inference
"""

import time
import uuid
import logging
from datetime import datetime, timezone
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PipelineLatency:
    """Latency breakdown for each stage in the pipeline."""
    stt_transcription_ms: Optional[float] = None       # Speech → text time
    retrieval_ms: Optional[float] = None                # FAISS vector search time
    llm_generation_ms: Optional[float] = None           # LLM first-token / full generation
    tts_first_audio_ms: Optional[float] = None          # Text → first audio chunk
    total_round_trip_ms: Optional[float] = None         # End-to-end time


@dataclass
class ConversationEntry:
    """A single exchange in a conversation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    conversation_id: str = ""
    mode: str = "chat"                                  # "chat" | "voice"
    user_query: str = ""
    ai_response: str = ""
    latency: PipelineLatency = field(default_factory=PipelineLatency)
    errors: list[str] = field(default_factory=list)
    status: str = "success"                             # "success" | "error" | "partial"

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


# ---------------------------------------------------------------------------
#  In-Memory Store (will be DB-backed in SaaS phase)
# ---------------------------------------------------------------------------

_entries: list[ConversationEntry] = []
_active_traces: dict[str, dict] = {}  # trace_id -> timing context


def start_trace(conversation_id: str, mode: str, user_query: str) -> str:
    """Begin timing a pipeline execution. Returns a trace_id."""
    trace_id = str(uuid.uuid4())
    _active_traces[trace_id] = {
        "conversation_id": conversation_id,
        "mode": mode,
        "user_query": user_query,
        "start_time": time.perf_counter(),
        "stt_start": None,
        "stt_end": None,
        "retrieval_start": None,
        "retrieval_end": None,
        "llm_start": None,
        "llm_end": None,
        "tts_start": None,
        "tts_end": None,
        "errors": [],
    }
    logger.info(f"[Analytics] Trace started: {trace_id} (mode={mode})")
    return trace_id


def mark(trace_id: str, stage: str, event: str = "start"):
    """Mark a timing event: mark(trace_id, 'stt', 'start') / mark(trace_id, 'stt', 'end')."""
    trace = _active_traces.get(trace_id)
    if not trace:
        return
    key = f"{stage}_{event}"
    trace[key] = time.perf_counter()


def record_error(trace_id: str, error_message: str):
    """Attach an error to the current trace."""
    trace = _active_traces.get(trace_id)
    if not trace:
        return
    trace["errors"].append(error_message)
    logger.warning(f"[Analytics] Error recorded on trace {trace_id}: {error_message}")


def finish_trace(trace_id: str, ai_response: str = "") -> Optional[ConversationEntry]:
    """
    Finalize a trace, compute latencies, and store the entry.
    Returns the completed ConversationEntry.
    """
    trace = _active_traces.pop(trace_id, None)
    if not trace:
        logger.warning(f"[Analytics] finish_trace called for unknown trace: {trace_id}")
        return None

    now = time.perf_counter()

    def _ms(start_key: str, end_key: str) -> Optional[float]:
        s = trace.get(start_key)
        e = trace.get(end_key)
        if s is not None and e is not None:
            return round((e - s) * 1000, 2)
        return None

    latency = PipelineLatency(
        stt_transcription_ms=_ms("stt_start", "stt_end"),
        retrieval_ms=_ms("retrieval_start", "retrieval_end"),
        llm_generation_ms=_ms("llm_start", "llm_end"),
        tts_first_audio_ms=_ms("tts_start", "tts_end"),
        total_round_trip_ms=round((now - trace["start_time"]) * 1000, 2),
    )

    errors = trace.get("errors", [])
    status = "error" if errors else "success"

    entry = ConversationEntry(
        conversation_id=trace["conversation_id"],
        mode=trace["mode"],
        user_query=trace["user_query"],
        ai_response=ai_response,
        latency=latency,
        errors=errors,
        status=status,
    )

    _entries.append(entry)
    logger.info(
        f"[Analytics] Trace finished: {trace_id} | "
        f"total={latency.total_round_trip_ms}ms | status={status}"
    )
    return entry


# ---------------------------------------------------------------------------
#  Query Functions
# ---------------------------------------------------------------------------

def get_all_entries(
    mode: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Return conversation entries with optional filters, newest first."""
    filtered = list(reversed(_entries))

    if mode:
        filtered = [e for e in filtered if e.mode == mode]
    if status:
        filtered = [e for e in filtered if e.status == status]

    total = len(filtered)
    page = filtered[offset:offset + limit]

    return {
        "entries": [e.to_dict() for e in page],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def get_summary() -> dict:
    """Return aggregate analytics summary."""
    if not _entries:
        return {
            "total_conversations": 0,
            "chat_count": 0,
            "voice_count": 0,
            "error_count": 0,
            "avg_latency_ms": 0,
            "avg_stt_ms": 0,
            "avg_llm_ms": 0,
            "avg_tts_ms": 0,
            "avg_retrieval_ms": 0,
        }

    total = len(_entries)
    chat_count = sum(1 for e in _entries if e.mode == "chat")
    voice_count = sum(1 for e in _entries if e.mode == "voice")
    error_count = sum(1 for e in _entries if e.status == "error")

    def _avg(values: list[float]) -> float:
        return round(sum(values) / len(values), 2) if values else 0

    total_latencies = [e.latency.total_round_trip_ms for e in _entries if e.latency.total_round_trip_ms is not None]
    stt_latencies = [e.latency.stt_transcription_ms for e in _entries if e.latency.stt_transcription_ms is not None]
    llm_latencies = [e.latency.llm_generation_ms for e in _entries if e.latency.llm_generation_ms is not None]
    tts_latencies = [e.latency.tts_first_audio_ms for e in _entries if e.latency.tts_first_audio_ms is not None]
    retrieval_latencies = [e.latency.retrieval_ms for e in _entries if e.latency.retrieval_ms is not None]

    return {
        "total_conversations": total,
        "chat_count": chat_count,
        "voice_count": voice_count,
        "error_count": error_count,
        "avg_latency_ms": _avg(total_latencies),
        "avg_stt_ms": _avg(stt_latencies),
        "avg_llm_ms": _avg(llm_latencies),
        "avg_tts_ms": _avg(tts_latencies),
        "avg_retrieval_ms": _avg(retrieval_latencies),
    }


def clear_analytics():
    """Clear all stored analytics data."""
    global _entries, _active_traces
    _entries = []
    _active_traces = {}
    logger.info("[Analytics] All analytics data cleared")
