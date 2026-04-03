"""监控数据采集器 — 汇聚 tracer + metrics + training"""

from __future__ import annotations

import asyncio
from typing import Any

from monitor.metrics import RecMetrics, get_metrics
from monitor.schema import PipelineTrace
from monitor.tracer import RecTracer
from monitor.training_logger import TrainingLogger
from utils.logger import get_struct_logger

logger = get_struct_logger("monitor.collector")


class MonitorCollector:
    """监控采集器：汇聚链路追踪、指标、训练日志。"""

    def __init__(self, training_logger: TrainingLogger | None = None):
        self._metrics = get_metrics()
        self._training_logger = training_logger
        self._sinks: list = []

    def add_sink(self, sink: Any) -> None:
        """添加日志输出 sink。"""
        self._sinks.append(sink)

    async def collect(self, tracer: RecTracer, ctx: Any = None) -> PipelineTrace:
        """采集一次请求的完整追踪数据。"""
        # 1. 生成 PipelineTrace
        trace = tracer.finalize()

        # 2. 更新 Prometheus 指标
        self._metrics.record_latency("request", trace.total_latency_ms)
        self._metrics.record_count("request")
        for stage in trace.stages:
            self._metrics.record_latency(f"stage.{stage.stage_name}", stage.latency_ms)

        # 3. 训练日志落盘
        if self._training_logger and ctx:
            await self._write_training_log(trace, ctx)

        # 4. 分发到各 sink
        for sink in self._sinks:
            try:
                await sink.write(trace)
            except Exception as e:
                logger.error(f"Sink 写入失败: {sink}", error=str(e))

        return trace

    async def _write_training_log(self, trace: PipelineTrace, ctx: Any) -> None:
        """从 trace 和 ctx 生成训练日志。"""
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
                "recall_sources": item_trace.recall_sources,
                "total_latency_ms": trace.total_latency_ms,
                "timestamp": trace.timestamp,
                # 标签延迟回填
                "label_clicked": None,
                "label_liked": None,
                "label_shared": None,
                "label_commented": None,
                "dwell_time_sec": None,
            }
            await self._training_logger.log(entry)
