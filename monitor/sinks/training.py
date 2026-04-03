"""Training Sink — 将训练日志写入专用文件"""

from __future__ import annotations

from monitor.schema import PipelineTrace
from monitor.training_logger import TrainingLogger
from utils.logger import get_struct_logger

logger = get_struct_logger("monitor.sinks.training")


class TrainingSink:
    """将 PipelineTrace 转为训练日志格式写入。"""

    def __init__(self, training_logger: TrainingLogger):
        self._logger = training_logger

    async def write(self, trace: PipelineTrace) -> None:
        for item_trace in trace.item_traces:
            if item_trace.filtered_out_at:
                continue
            entry = {
                "trace_id": trace.trace_id,
                "request_id": trace.request_id,
                "user_id": trace.user_id,
                "item_id": item_trace.item_id,
                "scene": trace.scene,
                "scores": item_trace.scores,
                "positions": item_trace.positions,
                "total_latency_ms": trace.total_latency_ms,
                "timestamp": trace.timestamp,
            }
            await self._logger.log(entry)
