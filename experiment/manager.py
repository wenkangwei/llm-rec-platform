"""实验管理器 — 流量分桶、实验生命周期、指标收集"""

from __future__ import annotations

import hashlib
import time
from typing import Any

from experiment.models import Experiment, ExperimentStatus, ExperimentVariant
from utils.logger import get_struct_logger

logger = get_struct_logger("experiment.manager")


class ExperimentManager:
    """A/B 实验管理器。

    功能：
    - 创建/暂停/恢复/停止实验
    - 基于用户 ID 的确定性流量分桶
    - 实验指标收集和结果分析
    - 支持多层正交实验
    """

    def __init__(self):
        self._experiments: dict[str, Experiment] = {}
        self._layer_salt: dict[str, str] = {}  # layer_name → salt（正交分桶用）

    def create_experiment(self, experiment: Experiment) -> None:
        """创建实验。"""
        if experiment.id in self._experiments:
            raise ValueError(f"实验已存在: {experiment.id}")
        if not experiment.variants:
            raise ValueError("实验至少需要一个变体")

        total_traffic = sum(v.traffic_percent for v in experiment.variants)
        if abs(total_traffic - 100.0) > 0.01:
            raise ValueError(f"变体流量总和必须为 100，当前为 {total_traffic}")

        experiment.status = ExperimentStatus.DRAFT
        self._experiments[experiment.id] = experiment
        logger.info(f"实验创建: {experiment.id}", name=experiment.name)

    def start_experiment(self, experiment_id: str) -> None:
        """启动实验。"""
        exp = self._get_experiment(experiment_id)
        if exp.status == ExperimentStatus.RUNNING:
            logger.warning(f"实验已在运行: {experiment_id}")
            return
        exp.status = ExperimentStatus.RUNNING
        exp.started_at = time.time()
        logger.info(f"实验启动: {experiment_id}")

    def pause_experiment(self, experiment_id: str) -> None:
        """暂停实验。"""
        exp = self._get_experiment(experiment_id)
        exp.status = ExperimentStatus.PAUSED
        logger.info(f"实验暂停: {experiment_id}")

    def resume_experiment(self, experiment_id: str) -> None:
        """恢复实验。"""
        exp = self._get_experiment(experiment_id)
        if exp.status != ExperimentStatus.PAUSED:
            raise ValueError(f"只能恢复暂停状态的实验，当前: {exp.status}")
        exp.status = ExperimentStatus.RUNNING
        logger.info(f"实验恢复: {experiment_id}")

    def stop_experiment(self, experiment_id: str) -> None:
        """停止实验。"""
        exp = self._get_experiment(experiment_id)
        exp.status = ExperimentStatus.COMPLETED
        exp.ended_at = time.time()
        logger.info(f"实验停止: {experiment_id}")

    def cancel_experiment(self, experiment_id: str) -> None:
        """取消实验。"""
        exp = self._get_experiment(experiment_id)
        exp.status = ExperimentStatus.CANCELLED
        exp.ended_at = time.time()
        logger.info(f"实验取消: {experiment_id}")

    def get_variant(
        self, experiment_id: str, user_id: str, layer: str = "default"
    ) -> ExperimentVariant | None:
        """获取用户在实验中所属的分组。

        使用确定性哈希分桶，同一用户永远进入同一分组。
        支持 layer 参数实现正交实验（不同 layer 独立分桶）。

        Args:
            experiment_id: 实验 ID
            user_id: 用户 ID
            layer: 实验层（用于正交分桶）

        Returns:
            用户所属的变体，实验未运行时返回 None
        """
        exp = self._get_experiment(experiment_id)
        if exp.status != ExperimentStatus.RUNNING:
            return None

        # 确定性分桶：hash(layer + experiment_id + user_id) % 100
        bucket = self._hash_bucket(f"{layer}:{experiment_id}:{user_id}")

        cumulative = 0.0
        for variant in exp.variants:
            cumulative += variant.traffic_percent
            if bucket < cumulative:
                return variant

        # 兜底返回最后一个
        return exp.variants[-1]

    def get_config_override(
        self, experiment_id: str, user_id: str, layer: str = "default"
    ) -> dict[str, Any]:
        """获取实验配置覆盖。

        返回用户所在分组的策略配置覆盖 dict。
        """
        variant = self.get_variant(experiment_id, user_id, layer)
        if variant:
            return variant.config
        return {}

    def record_metric(
        self, experiment_id: str, variant_name: str, metric_name: str, value: float
    ) -> None:
        """记录实验指标。

        Args:
            experiment_id: 实验 ID
            variant_name: 变体名称
            metric_name: 指标名称（如 "click_rate", "conversion_rate"）
            value: 指标值
        """
        exp = self._get_experiment(experiment_id)

        if variant_name not in exp.metrics:
            exp.metrics[variant_name] = {}
        if metric_name not in exp.metrics[variant_name]:
            exp.metrics[variant_name][metric_name] = []

        exp.metrics[variant_name][metric_name].append(value)

    def get_results(self, experiment_id: str) -> dict[str, Any]:
        """获取实验结果分析。

        Returns:
            各变体的指标统计（均值/标准差/样本数）
        """
        exp = self._get_experiment(experiment_id)
        results = {}

        for variant_name, metrics in exp.metrics.items():
            variant_results = {}
            for metric_name, values in metrics.items():
                if not values:
                    variant_results[metric_name] = {"mean": 0, "std": 0, "count": 0}
                    continue
                n = len(values)
                mean = sum(values) / n
                variance = sum((x - mean) ** 2 for x in values) / n
                variant_results[metric_name] = {
                    "mean": round(mean, 6),
                    "std": round(variance ** 0.5, 6),
                    "count": n,
                }
            results[variant_name] = variant_results

        return {
            "experiment_id": experiment_id,
            "status": exp.status.value,
            "variants": results,
        }

    def list_experiments(self, status: ExperimentStatus | None = None) -> list[dict[str, Any]]:
        """列出所有实验。"""
        experiments = []
        for exp in self._experiments.values():
            if status is None or exp.status == status:
                experiments.append({
                    "id": exp.id,
                    "name": exp.name,
                    "status": exp.status.value,
                    "variants": [v.name for v in exp.variants],
                })
        return experiments

    def delete_experiment(self, experiment_id: str) -> None:
        """删除实验。"""
        if experiment_id not in self._experiments:
            raise KeyError(f"实验不存在: {experiment_id}")
        del self._experiments[experiment_id]
        logger.info(f"实验删除: {experiment_id}")

    def _get_experiment(self, experiment_id: str) -> Experiment:
        """获取实验，不存在则抛出 KeyError。"""
        if experiment_id not in self._experiments:
            raise KeyError(f"实验不存在: {experiment_id}")
        return self._experiments[experiment_id]

    @staticmethod
    def _hash_bucket(key: str) -> float:
        """确定性哈希分桶，返回 0-99.99 的值。"""
        digest = hashlib.md5(key.encode()).hexdigest()
        # 取前 8 位 hex 转为 int，再映射到 0-100
        value = int(digest[:8], 16)
        return (value % 10000) / 100.0
