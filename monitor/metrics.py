"""Prometheus 指标定义"""

from __future__ import annotations

from typing import Any

from utils.logger import get_struct_logger

logger = get_struct_logger("monitor.metrics")


class RecMetrics:
    """推荐系统 Prometheus 指标。

    指标列表:
    - rec_request_latency_ms: 请求延迟 (histogram)
    - rec_request_total: 请求总数 (counter)
    - rec_stage_latency_ms: 各阶段延迟 (histogram)
    - rec_recall_count: 召回数量 (histogram)
    - rec_items_exposed: 曝光物品数 (counter)
    - rec_model_inference_ms: 模型推理耗时 (histogram)
    """

    def __init__(self):
        self._counters: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}

    def record_latency(self, label: str, value_ms: float) -> None:
        """记录延迟。"""
        key = f"latency:{label}"
        self._histograms.setdefault(key, []).append(value_ms)

    def record_count(self, label: str, value: float = 1.0) -> None:
        """记录计数。"""
        key = f"count:{label}"
        self._counters[key] = self._counters.get(key, 0) + value

    def record_histogram(self, name: str, value: float) -> None:
        """记录直方图。"""
        self._histograms.setdefault(name, []).append(value)

    def get_counter(self, label: str) -> float:
        return self._counters.get(f"count:{label}", 0)

    def get_histogram_summary(self, name: str) -> dict[str, float]:
        """获取直方图摘要（p50/p99/max）。"""
        values = self._histograms.get(name, [])
        if not values:
            return {"p50": 0, "p99": 0, "max": 0, "count": 0}
        sorted_v = sorted(values)
        return {
            "p50": sorted_v[len(sorted_v) // 2],
            "p99": sorted_v[int(len(sorted_v) * 0.99)],
            "max": sorted_v[-1],
            "count": len(sorted_v),
        }

    def get_all_metrics(self) -> dict[str, Any]:
        """获取所有指标快照。"""
        result: dict[str, Any] = {"counters": dict(self._counters)}
        for name, values in self._histograms.items():
            result[name] = self.get_histogram_summary(name)
        return result

    def format_prometheus(self) -> str:
        """输出 Prometheus 文本格式。"""
        lines = []
        for key, value in self._counters.items():
            name = key.replace(":", "_").replace(".", "_")
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")
        for key, values in self._histograms.items():
            name = key.replace(":", "_").replace(".", "_")
            summary = self.get_histogram_summary(key)
            lines.append(f"# TYPE {name} summary")
            for quantile, val in summary.items():
                lines.append(f'{name}_{{quantile="{quantile}"}} {val}')
        return "\n".join(lines)


# 全局单例
_metrics: RecMetrics | None = None


def get_metrics() -> RecMetrics:
    global _metrics
    if _metrics is None:
        _metrics = RecMetrics()
    return _metrics
