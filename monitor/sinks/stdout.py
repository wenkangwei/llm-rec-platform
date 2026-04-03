"""Stdout Sink — 控制台输出追踪日志"""

from __future__ import annotations

import json

from monitor.schema import PipelineTrace
from utils.logger import get_struct_logger

logger = get_struct_logger("monitor.sinks.stdout")


class StdoutSink:
    """将 PipelineTrace 输出到标准日志。"""

    async def write(self, trace: PipelineTrace) -> None:
        summary = {
            "trace_id": trace.trace_id,
            "request_id": trace.request_id,
            "user_id": trace.user_id,
            "scene": trace.scene,
            "total_ms": round(trace.total_latency_ms, 1),
            "stages": [
                {"name": s.stage_name, "ms": round(s.latency_ms, 1), "in": s.input_count, "out": s.output_count}
                for s in trace.stages
            ],
            "items_traced": len(trace.item_traces),
        }
        logger.info(f"[Trace] {json.dumps(summary, ensure_ascii=False)}")
