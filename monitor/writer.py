"""日志 Writer — 统一写入接口"""

from __future__ import annotations

from abc import ABC, abstractmethod

from monitor.schema import PipelineTrace


class TraceWriter(ABC):
    """链路追踪 Writer 基类。"""

    @abstractmethod
    async def write(self, trace: PipelineTrace) -> None:
        """写入一条链路追踪记录。"""
        ...
