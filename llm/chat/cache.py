"""查询缓存 — LRU + TTL 策略，避免重复查询"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from utils.logger import get_struct_logger

logger = get_struct_logger("llm.chat.cache")


@dataclass
class _CacheEntry:
    reply: str
    timestamp: float


class QueryCache:
    """LRU + TTL 查询缓存。

    - LRU: 超容量时淘汰最旧条目
    - TTL: 超时条目自动失效
    - Key: 归一化后的用户消息（strip + lower）
    """

    def __init__(self, max_size: int = 200, ttl_seconds: int = 300):
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    def get(self, message: str) -> str | None:
        """查询缓存，命中返回回复，未命中返回 None。"""
        key = message.strip().lower()
        entry = self._cache.get(key)
        if entry is None:
            self._misses += 1
            return None

        # TTL 检查
        if time.time() - entry.timestamp > self._ttl:
            del self._cache[key]
            self._misses += 1
            return None

        # 命中：移到末尾（LRU）
        self._cache.move_to_end(key)
        self._hits += 1
        logger.debug(f"缓存命中: {key[:50]}...")
        return entry.reply

    def put(self, message: str, reply: str) -> None:
        """写入缓存。"""
        if not reply:
            return
        key = message.strip().lower()
        # 已存在则更新
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = _CacheEntry(reply=reply, timestamp=time.time())
        # 超容量淘汰
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def invalidate(self, message: str) -> bool:
        """使指定消息的缓存失效。"""
        key = message.strip().lower()
        if key in self._cache:
            del self._cache[key]
            return True
        return False

    def clear(self) -> int:
        """清空缓存，返回清除条目数。"""
        n = len(self._cache)
        self._cache.clear()
        return n

    def stats(self) -> dict[str, Any]:
        """缓存统计。"""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
            "hit_rate": round(self._hits / total, 3) if total > 0 else 0.0,
        }
