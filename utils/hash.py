"""哈希工具 — 一致性哈希、分桶、ID 生成"""

from __future__ import annotations

import hashlib
import uuid
from typing import Any


def md5_hash(text: str) -> str:
    """返回字符串的 MD5 哈希值。"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def consistent_bucket(key: str, num_buckets: int) -> int:
    """一致性分桶：基于 key 的哈希映射到 [0, num_buckets)。

    用于 A/B 测试流量分桶。
    """
    hash_val = int(hashlib.md5(key.encode("utf-8")).hexdigest(), 16)
    return hash_val % num_buckets


def generate_request_id() -> str:
    """生成唯一请求 ID。"""
    return uuid.uuid4().hex[:16]


def generate_trace_id() -> str:
    """生成链路追踪 ID。"""
    return uuid.uuid4().hex


def fingerprint(data: Any) -> str:
    """生成数据指纹哈希，用于去重。"""
    raw = str(data).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]
