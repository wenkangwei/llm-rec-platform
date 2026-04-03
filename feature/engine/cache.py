"""特征缓存 — 本地缓存 + TTL"""

from __future__ import annotations

import time
from typing import Any

from utils.logger import get_struct_logger

logger = get_struct_logger("feature.engine.cache")


class FeatureCache:
    """特征缓存：内存级 LRU 缓存。"""

    def __init__(self, max_size: int = 10000, default_ttl: int = 60):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cache: dict[str, tuple[Any, float]] = {}  # key → (value, expire_at)

    def get(self, key: str) -> Any | None:
        """获取缓存。"""
        entry = self._cache.get(key)
        if entry is None:
            return None
        value, expire_at = entry
        if time.time() < expire_at:
            return value
        del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """设置缓存。"""
        if len(self._cache) >= self._max_size:
            self._evict()
        expire_at = time.time() + (ttl or self._default_ttl)
        self._cache[key] = (value, expire_at)

    def _evict(self) -> None:
        """LRU 淘汰。"""
        now = time.time()
        expired = [k for k, (_, exp) in self._cache.items() if now > exp]
        if expired:
            for k in expired:
                del self._cache[k]
        elif self._cache:
            oldest = min(self._cache, key=lambda k: self._cache[k][1])
            del self._cache[oldest]

    def clear(self) -> None:
        self._cache.clear()
