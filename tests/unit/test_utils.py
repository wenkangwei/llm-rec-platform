"""utils 模块单元测试"""

from __future__ import annotations

import pytest

from utils.hash import consistent_bucket, fingerprint, generate_request_id, generate_trace_id, md5_hash
from utils.logger import get_logger, get_struct_logger
from utils.timer import timer, async_timer


class TestHash:
    """哈希工具测试。"""

    def test_md5_hash_deterministic(self):
        assert md5_hash("hello") == md5_hash("hello")

    def test_md5_hash_different_inputs(self):
        assert md5_hash("a") != md5_hash("b")

    def test_consistent_bucket_range(self):
        for key in ["user1", "user2", "abc", "xyz", "123"]:
            b = consistent_bucket(key, 10)
            assert 0 <= b < 10

    def test_consistent_bucket_deterministic(self):
        assert consistent_bucket("test", 100) == consistent_bucket("test", 100)

    def test_generate_request_id_unique(self):
        ids = {generate_request_id() for _ in range(100)}
        assert len(ids) == 100

    def test_generate_request_id_length(self):
        assert len(generate_request_id()) == 16

    def test_generate_trace_id_unique(self):
        ids = {generate_trace_id() for _ in range(100)}
        assert len(ids) == 100

    def test_generate_trace_id_length(self):
        assert len(generate_trace_id()) == 32

    def test_fingerprint_deterministic(self):
        assert fingerprint({"a": 1}) == fingerprint({"a": 1})

    def test_fingerprint_different(self):
        assert fingerprint("a") != fingerprint("b")


class TestLogger:
    """日志工具测试。"""

    def test_get_logger(self):
        logger = get_logger("test")
        assert logger.name == "test"

    def test_get_struct_logger(self):
        adapter = get_struct_logger("test_struct")
        assert adapter is not None

    def test_struct_logger_bind(self):
        adapter = get_struct_logger("test_bind")
        bound = adapter.bind(request_id="abc")
        assert bound._extra["request_id"] == "abc"


class TestTimer:
    """计时器测试。"""

    def test_timer_context(self):
        import time

        with timer("test") as get_elapsed:
            time.sleep(0.01)
        assert get_elapsed() >= 5

    def test_async_timer(self):
        import asyncio
        import time

        async def _run():
            async with async_timer("test") as get_elapsed:
                await asyncio.sleep(0.01)
            assert get_elapsed() >= 5

        asyncio.get_event_loop().run_until_complete(_run())
