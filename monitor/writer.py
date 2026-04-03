"""日志 Writer — 统一写入接口"""

from __future__ import annotations

from monitor.schema import PipelineTrace


class TraceWriter:
    """链路追踪 Writer 基类。"""

    async def write(self, trace: PipelineTrace) -> None:
        raise NotImplementedError
