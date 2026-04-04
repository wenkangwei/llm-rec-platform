"""监控查询工具"""

from __future__ import annotations

import time
from typing import Any

from llm.agent.base import Tool
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.agent.tools.monitor")


class MonitorQueryTool(Tool):
    """监控查询工具：查询链路指标、延迟、召回覆盖率。"""

    def __init__(self, metrics_store: dict[str, Any] | None = None):
        self._metrics = metrics_store or {}

    def name(self) -> str:
        return "monitor_query"

    def description(self) -> str:
        return "查询推荐系统监控指标：延迟、QPS、召回覆盖率、模型推理耗时。参数: metric(指标名), time_range(时间范围)"

    async def execute(self, params: dict[str, Any]) -> Any:
        metric = params.get("metric", "all")
        time_range = params.get("time_range", "1h")

        # 中文 metric 名映射
        metric_map = {
            "延迟": "latency", "延迟": "latency",
            "QPS": "qps", "qps": "qps",
            "召回覆盖率": "recall_coverage", "覆盖率": "recall_coverage",
            "模型推理耗时": "latency", "推理耗时": "latency",
            "全部": "all", "所有": "all",
            "latency": "latency", "recall_coverage": "recall_coverage",
        }
        metric = metric_map.get(metric, metric)

        if metric == "all":
            return self._get_all_metrics(time_range)
        elif metric == "latency":
            return self._get_latency()
        elif metric == "recall_coverage":
            return self._get_recall_coverage()
        elif metric == "qps":
            return self._get_qps()
        else:
            # 兜底：返回全部指标
            return self._get_all_metrics(time_range)

    def _get_all_metrics(self, time_range: str) -> dict:
        result = {
            "latency_p99_ms": self._metrics.get("latency_p99_ms", 150),
            "qps": self._metrics.get("qps", 500),
            "recall_coverage": self._metrics.get("recall_coverage", 0.92),
            "model_inference_ms": self._metrics.get("model_inference_ms", 30),
            "time_range": time_range,
            "timestamp": time.time(),
        }
        # 注入运行时指标
        if "components_health" in self._metrics:
            result["components"] = self._metrics["components_health"]
        if "pipeline_health" in self._metrics:
            result["pipeline_health"] = self._metrics["pipeline_health"]
        if "active_experiments" in self._metrics:
            result["active_experiments"] = self._metrics["active_experiments"]
        return result

    def _get_latency(self) -> dict:
        return {
            "p50_ms": self._metrics.get("latency_p50_ms", 80),
            "p99_ms": self._metrics.get("latency_p99_ms", 150),
            "p999_ms": self._metrics.get("latency_p999_ms", 200),
        }

    def _get_recall_coverage(self) -> dict:
        return {
            "overall": self._metrics.get("recall_coverage", 0.92),
            "by_channel": self._metrics.get("recall_by_channel", {}),
        }

    def _get_qps(self) -> dict:
        return {
            "current": self._metrics.get("qps", 500),
            "peak": self._metrics.get("qps_peak", 800),
        }

    def schema(self) -> dict:
        return {
            "metric": {"type": "string", "enum": ["all", "latency", "recall_coverage", "qps"]},
            "time_range": {"type": "string", "default": "1h"},
        }
