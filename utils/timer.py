"""计时工具 — 上下文管理器和装饰器"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator


@contextmanager
def timer(name: str = "") -> Iterator[float]:
    """同步计时上下文管理器。

    Usage:
        with timer("recall") as get_elapsed:
            do_something()
        print(f"耗时: {get_elapsed()}ms")
    """
    start = time.perf_counter()
    elapsed_holder: list[float] = [0.0]

    def _elapsed() -> float:
        return elapsed_holder[0]

    try:
        yield _elapsed
    finally:
        elapsed_holder[0] = (time.perf_counter() - start) * 1000


@asynccontextmanager
async def async_timer(name: str = "") -> AsyncIterator[float]:
    """异步计时上下文管理器。"""
    start = time.perf_counter()
    elapsed_holder: list[float] = [0.0]

    def _elapsed() -> float:
        return elapsed_holder[0]

    try:
        yield _elapsed
    finally:
        elapsed_holder[0] = (time.perf_counter() - start) * 1000


def timeit(func):
    """同步函数计时装饰器。"""
    import functools

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        print(f"[{func.__name__}] elapsed: {elapsed_ms:.2f}ms")
        return result

    return wrapper
