"""RecTracer — 每请求全链路追踪"""

from __future__ import annotations

import time
from typing import Any

from monitor.schema import (
    ItemTrace,
    PipelineTrace,
    RecallCoverage,
    StageTrace,
)
from utils.hash import generate_trace_id
from utils.logger import get_struct_logger

logger = get_struct_logger("monitor.tracer")


class RecTracer:
    """每请求全链路追踪。

    用法:
        tracer = RecTracer(request_id, user_id, scene)
        tracer.start_stage("recall")
        # ... 执行召回 ...
        tracer.end_stage("recall", input_count=0, output_count=500)
        trace = tracer.finalize()
    """

    def __init__(self, request_id: str, user_id: str, scene: str):
        self._trace_id = generate_trace_id()
        self._request_id = request_id
        self._user_id = user_id
        self._scene = scene
        self._start_time = time.perf_counter()
        self._stage_timers: dict[str, float] = {}
        self._stages: list[StageTrace] = []
        self._item_traces: dict[str, ItemTrace] = {}
        self._recall_coverages: list[RecallCoverage] = []

    @property
    def trace_id(self) -> str:
        return self._trace_id

    def start_stage(self, stage_name: str) -> None:
        """标记阶段开始。"""
        self._stage_timers[stage_name] = time.perf_counter()

    def end_stage(
        self,
        stage_name: str,
        input_count: int = 0,
        output_count: int = 0,
        error: str = "",
    ) -> None:
        """标记阶段结束，记录指标。"""
        start = self._stage_timers.pop(stage_name, time.perf_counter())
        latency_ms = (time.perf_counter() - start) * 1000
        self._stages.append(StageTrace(
            stage_name=stage_name,
            latency_ms=latency_ms,
            input_count=input_count,
            output_count=output_count,
            error=error,
        ))

    def record_item_score(self, item_id: str, stage: str, score: float, position: int = -1) -> None:
        """记录物品在某阶段的分数和位置。"""
        if item_id not in self._item_traces:
            self._item_traces[item_id] = ItemTrace(item_id=item_id)
        trace = self._item_traces[item_id]
        trace.scores[stage] = score
        if position >= 0:
            trace.positions[stage] = position

    def record_filter_out(self, item_id: str, stage: str, reason: str = "") -> None:
        """记录物品被过滤。"""
        if item_id not in self._item_traces:
            self._item_traces[item_id] = ItemTrace(item_id=item_id)
        self._item_traces[item_id].filtered_out_at = stage
        self._item_traces[item_id].filter_reason = reason

    def record_recall_source(self, source: str, recalled_count: int) -> None:
        """记录召回通道召回数量。"""
        self._recall_coverages.append(RecallCoverage(
            source=source,
            recalled_count=recalled_count,
            survived_count=0,
            final_exposed=0,
        ))

    def update_recall_survival(self, source: str, survived: int, exposed: int) -> None:
        """更新召回通道存活/曝光数。"""
        for cov in self._recall_coverages:
            if cov.source == source:
                cov.survived_count = survived
                cov.final_exposed = exposed

    def finalize(self) -> PipelineTrace:
        """生成完整链路追踪。"""
        total_latency_ms = (time.perf_counter() - self._start_time) * 1000
        trace = PipelineTrace(
            trace_id=self._trace_id,
            request_id=self._request_id,
            user_id=self._user_id,
            scene=self._scene,
            total_latency_ms=total_latency_ms,
            stages=self._stages,
            item_traces=list(self._item_traces.values()),
            recall_coverages=self._recall_coverages,
            timestamp=time.time(),
        )
        logger.debug(
            f"链路追踪完成",
            trace_id=self._trace_id,
            total_ms=f"{total_latency_ms:.1f}",
            stages=len(self._stages),
        )
        return trace
