"""特征统计分析 — 覆盖率、空值率、分布"""

from __future__ import annotations

from typing import Any

from utils.logger import get_struct_logger

logger = get_struct_logger("feature.offline.stats")


class FeatureStats:
    """特征统计分析：覆盖率、空值率、分布。

    支持从已加载的特征数据中计算统计指标。
    """

    def __init__(self):
        self._feature_data: dict[str, list[Any]] = {}  # feature_name → values

    def load_samples(self, feature_name: str, values: list[Any]) -> int:
        """加载特征采样数据。

        Args:
            feature_name: 特征名称
            values: 采样值列表

        Returns:
            加载的样本数
        """
        self._feature_data[feature_name] = values
        logger.info(f"特征采样加载", feature=feature_name, count=len(values))
        return len(values)

    def compute_coverage(self, feature_name: str, sample_size: int = 10000) -> dict[str, Any]:
        """计算特征覆盖率。

        Returns:
            {"feature": str, "coverage": float, "null_rate": float, "sample_size": int}
        """
        values = self._feature_data.get(feature_name)
        if not values:
            logger.warning(f"特征无采样数据: {feature_name}")
            return {"feature": feature_name, "coverage": 0.0, "null_rate": 1.0, "sample_size": 0}

        total = len(values)
        non_null = sum(1 for v in values if v is not None and v != "")
        null_count = total - non_null
        coverage = non_null / total if total > 0 else 0.0

        return {
            "feature": feature_name,
            "coverage": round(coverage, 4),
            "null_rate": round(1.0 - coverage, 4),
            "sample_size": total,
        }

    def compute_distribution(self, feature_name: str) -> dict[str, Any]:
        """计算特征分布。

        Returns:
            {"feature": str, "mean": float, "std": float, "min": float, "max": float,
             "median": float, "p25": float, "p75": float}
        """
        values = self._feature_data.get(feature_name)
        if not values:
            return {"feature": feature_name, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

        # 过滤非数值
        numeric_values = []
        for v in values:
            if v is not None:
                try:
                    numeric_values.append(float(v))
                except (ValueError, TypeError):
                    continue

        if not numeric_values:
            return {"feature": feature_name, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}

        n = len(numeric_values)
        sorted_v = sorted(numeric_values)
        mean_val = sum(sorted_v) / n
        variance = sum((x - mean_val) ** 2 for x in sorted_v) / n
        std_val = variance ** 0.5

        def percentile(data: list[float], p: float) -> float:
            """最近秩法百分位计算。"""
            if not data:
                return 0.0
            idx = int((len(data) - 1) * p / 100)
            return data[min(idx, len(data) - 1)]

        return {
            "feature": feature_name,
            "mean": round(mean_val, 4),
            "std": round(std_val, 4),
            "min": sorted_v[0],
            "max": sorted_v[-1],
            "median": percentile(sorted_v, 50),
            "p25": percentile(sorted_v, 25),
            "p75": percentile(sorted_v, 75),
            "count": n,
        }

    def compute_multi_stats(self, feature_names: list[str]) -> list[dict[str, Any]]:
        """批量计算多个特征的统计。"""
        results = []
        for name in feature_names:
            coverage = self.compute_coverage(name)
            distribution = self.compute_distribution(name)
            results.append({**coverage, **distribution})
        return results

    def clear(self) -> None:
        """清除已加载的数据。"""
        self._feature_data.clear()
