from __future__ import annotations

import hashlib
import json
from typing import Any
from cachetools import TTLCache


class AiMemoryCache:
    """Thread-safe in-memory TTL cache for AI structured responses."""

    def __init__(self, maxsize: int = 1000, ttl: int = 300) -> None:
        self._cache: TTLCache[str, Any] = TTLCache(maxsize=maxsize, ttl=ttl)

    def get(self, key: str) -> Any | None:
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = value

    def clear(self) -> None:
        self._cache.clear()

    @staticmethod
    def hash_key(prefix: str, data: dict[str, Any] | str) -> str:
        if isinstance(data, dict):
            serialized = json.dumps(data, sort_keys=True, default=str)
        else:
            serialized = str(data)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        return f"{prefix}:{digest}"
