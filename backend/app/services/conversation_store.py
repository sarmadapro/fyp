"""
Conversation history store.

Backends:
- Redis (default in production) — survives restarts, works across
  multiple workers/replicas, has TTL so memory doesn't grow forever.
- In-memory dict (fallback) — used if Redis is unreachable, so local
  dev and CI still work without a running Redis.

Messages are stored as JSON in a Redis list per conversation_id:
  key:   conv:{conversation_id}
  value: LPUSH'd JSON blobs  {"role": "user"|"assistant", "content": "..."}

We keep the list trimmed to MAX_MESSAGES and set a TTL of CONV_TTL_SECONDS
that refreshes on every append, so idle conversations are auto-evicted.
"""

import os
import json
import logging
from typing import Optional

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

logger = logging.getLogger(__name__)

MAX_MESSAGES = 20            # how many messages we keep per conversation
CONV_TTL_SECONDS = 60 * 60 * 24  # 24h idle expiry


class _MemoryBackend:
    """Process-local fallback. Not for production multi-worker deployments."""

    def __init__(self):
        self._data: dict[str, list[dict]] = {}

    def append(self, conv_id: str, role: str, content: str) -> None:
        self._data.setdefault(conv_id, []).append({"role": role, "content": content})
        self._data[conv_id] = self._data[conv_id][-MAX_MESSAGES:]

    def get(self, conv_id: str) -> list[dict]:
        return list(self._data.get(conv_id, []))

    def clear(self, conv_id: str) -> None:
        self._data.pop(conv_id, None)

    def clear_many(self, conv_ids: list[str]) -> None:
        for cid in conv_ids:
            self._data.pop(cid, None)


class _RedisBackend:
    """Redis-backed store. One list per conversation, trimmed + TTL refreshed on write."""

    def __init__(self, client):
        self._r = client

    @staticmethod
    def _key(conv_id: str) -> str:
        return f"conv:{conv_id}"

    def append(self, conv_id: str, role: str, content: str) -> None:
        key = self._key(conv_id)
        blob = json.dumps({"role": role, "content": content})
        pipe = self._r.pipeline()
        pipe.rpush(key, blob)
        pipe.ltrim(key, -MAX_MESSAGES, -1)
        pipe.expire(key, CONV_TTL_SECONDS)
        pipe.execute()

    def get(self, conv_id: str) -> list[dict]:
        raw = self._r.lrange(self._key(conv_id), 0, -1)
        out = []
        for blob in raw:
            try:
                # redis-py returns bytes by default; decode if needed
                if isinstance(blob, bytes):
                    blob = blob.decode("utf-8")
                out.append(json.loads(blob))
            except Exception:
                continue
        return out

    def clear(self, conv_id: str) -> None:
        self._r.delete(self._key(conv_id))

    def clear_many(self, conv_ids: list[str]) -> None:
        if not conv_ids:
            return
        self._r.delete(*[self._key(c) for c in conv_ids])


class ConversationStore:
    """Public facade. Picks a backend at construction time."""

    def __init__(self):
        self._backend = self._init_backend()

    def _init_backend(self):
        url = os.getenv("REDIS_URL")
        if not url:
            logger.warning(
                "REDIS_URL not set. Using in-memory conversation store "
                "(history will NOT survive restarts or scale across workers)."
            )
            return _MemoryBackend()
        try:
            import redis
            client = redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
            client.ping()
            logger.info(f"Conversation store: Redis @ {url}")
            return _RedisBackend(client)
        except Exception as e:
            logger.warning(f"Redis unreachable ({e}). Falling back to in-memory store.")
            return _MemoryBackend()

    # ── Public API ────────────────────────────────────────────────────

    def append_user(self, conv_id: str, content: str) -> None:
        self._backend.append(conv_id, "user", content)

    def append_assistant(self, conv_id: str, content: str) -> None:
        self._backend.append(conv_id, "assistant", content)

    def get_messages(self, conv_id: str) -> list[BaseMessage]:
        """Return history as LangChain message objects, ready for the prompt."""
        raw = self._backend.get(conv_id)
        msgs: list[BaseMessage] = []
        for m in raw:
            if m["role"] == "user":
                msgs.append(HumanMessage(content=m["content"]))
            elif m["role"] == "assistant":
                msgs.append(AIMessage(content=m["content"]))
        return msgs

    def get_raw(self, conv_id: str) -> list[dict]:
        """Return raw {role, content} dicts — useful for query rewriting."""
        return self._backend.get(conv_id)

    def clear(self, conv_id: str) -> None:
        self._backend.clear(conv_id)

    def clear_many(self, conv_ids: list[str]) -> None:
        self._backend.clear_many(conv_ids)


# Module-level singleton
conversation_store = ConversationStore()