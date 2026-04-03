"""ClickHouse Sink — 将 PipelineTrace 写入 ClickHouse OLAP"""

from __future__ import annotations

from typing import Any

from monitor.schema import PipelineTrace
from utils.logger import get_struct_logger

logger = get_struct_logger("monitor.sinks.clickhouse")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS rec_traces (
    trace_id String,
    request_id String,
    user_id String,
    scene String,
    total_latency_ms Float64,
    stage_count UInt32,
    item_count UInt32,
    timestamp Float64,
    created_at DateTime DEFAULT now()
) ENGINE = MergeTree()
ORDER BY (trace_id, timestamp)
"""


class ClickHouseSink:
    """将 PipelineTrace 批量写入 ClickHouse。"""

    def __init__(self, client: Any = None, table: str = "rec_traces",
                 batch_size: int = 1000, flush_interval_sec: int = 5):
        self._client = client
        self._table = table
        self._batch_size = batch_size
        self._flush_interval = flush_interval_sec
        self._buffer: list[dict] = []

    async def write(self, trace: PipelineTrace) -> None:
        row = {
            "trace_id": trace.trace_id,
            "request_id": trace.request_id,
            "user_id": trace.user_id,
            "scene": trace.scene,
            "total_latency_ms": trace.total_latency_ms,
            "stage_count": len(trace.stages),
            "item_count": len(trace.item_traces),
            "timestamp": trace.timestamp,
        }
        self._buffer.append(row)

        if len(self._buffer) >= self._batch_size:
            await self._flush()

    async def _flush(self) -> None:
        if not self._buffer:
            return
        if not self._client:
            self._buffer.clear()
            return
        try:
            columns = list(self._buffer[0].keys())
            rows = [tuple(row[c] for c in columns) for row in self._buffer]
            self._client.insert(self._table, rows, column_names=columns)
            logger.debug(f"ClickHouse 写入 {len(rows)} 条")
            self._buffer.clear()
        except Exception as e:
            logger.error(f"ClickHouse 写入失败", error=str(e))

    async def close(self) -> None:
        await self._flush()

    def init_table(self) -> None:
        """初始化 ClickHouse 表。"""
        if self._client:
            self._client.execute(_CREATE_TABLE_SQL)
            logger.info("ClickHouse 表初始化完成")
