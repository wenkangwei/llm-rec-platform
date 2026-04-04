"""离线特征生成 — T+1 批量计算特征"""

from __future__ import annotations

from typing import Any

import numpy as np

from utils.logger import get_struct_logger

logger = get_struct_logger("feature.offline.feature_gen")


class OfflineFeatureGenerator:
    """离线特征生成：T+1 批量计算特征。

    支持从 Parquet/CSV 文件读取原始数据，计算统计特征后输出。
    生产环境通常由 Airflow/DolphinScheduler 调度执行。
    """

    def __init__(self, data_source: str = "parquet"):
        self._data_source = data_source
        self._raw_data: dict[str, list[dict[str, Any]]] = {}  # entity_type → records

    def load_data(self, entity_type: str, records: list[dict[str, Any]]) -> int:
        """加载原始数据（替代 Hive/Parquet 读取）。

        Args:
            entity_type: "user" / "item"
            records: 原始行为记录列表

        Returns:
            加载的记录数
        """
        self._raw_data[entity_type] = records
        logger.info(f"离线数据加载", entity_type=entity_type, count=len(records))
        return len(records)

    def load_from_parquet(self, entity_type: str, path: str) -> int:
        """从 Parquet 文件加载数据。"""
        try:
            import pandas as pd
            df = pd.read_parquet(path)
            records = df.to_dict("records")
            return self.load_data(entity_type, records)
        except ImportError:
            logger.warning("pandas/pyarrow 未安装，无法读取 Parquet")
            return 0
        except FileNotFoundError:
            logger.warning(f"Parquet 文件不存在: {path}")
            return 0

    def generate_user_features(self, user_ids: list[str]) -> list[dict[str, Any]]:
        """批量生成用户特征。

        基于原始行为数据计算：
        - 活跃天数、最近活跃时间
        - 点击/收藏/分享次数统计
        - 类目偏好分布
        """
        logger.info(f"离线特征生成: {len(user_ids)} 用户")
        raw_records = self._raw_data.get("user", [])

        if not raw_records:
            # 无数据时返回空特征
            return []

        # 按 user_id 分组统计
        user_stats: dict[str, dict[str, Any]] = {}
        for record in raw_records:
            uid = record.get("user_id", "")
            if uid not in user_ids:
                continue
            if uid not in user_stats:
                user_stats[uid] = {
                    "click_count": 0,
                    "collect_count": 0,
                    "share_count": 0,
                    "category_dist": {},
                }
            stats = user_stats[uid]
            action = record.get("action", "")
            if action == "click":
                stats["click_count"] += 1
            elif action == "collect":
                stats["collect_count"] += 1
            elif action == "share":
                stats["share_count"] += 1

            category = record.get("category", "")
            if category:
                stats["category_dist"][category] = stats["category_dist"].get(category, 0) + 1

        results = []
        for uid in user_ids:
            if uid in user_stats:
                stats = user_stats[uid]
                results.append({
                    "entity_id": uid,
                    "click_count": stats["click_count"],
                    "collect_count": stats["collect_count"],
                    "share_count": stats["share_count"],
                    "top_category": max(stats["category_dist"], key=stats["category_dist"].get)
                    if stats["category_dist"] else "",
                    "activity_score": min(1.0, (stats["click_count"] + stats["collect_count"] * 2 + stats["share_count"] * 3) / 100),
                })
        return results

    def generate_item_features(self, item_ids: list[str]) -> list[dict[str, Any]]:
        """批量生成物品特征。

        基于原始数据计算：
        - 曝光/点击/收藏次数
        - CTR (Click-Through Rate)
        - 热度分数
        """
        logger.info(f"离线特征生成: {len(item_ids)} 物品")
        raw_records = self._raw_data.get("item", [])

        if not raw_records:
            return []

        item_stats: dict[str, dict[str, Any]] = {}
        for record in raw_records:
            iid = record.get("item_id", "")
            if iid not in item_ids:
                continue
            if iid not in item_stats:
                item_stats[iid] = {"expose_count": 0, "click_count": 0, "collect_count": 0}
            stats = item_stats[iid]
            action = record.get("action", "")
            if action == "expose":
                stats["expose_count"] += 1
            elif action == "click":
                stats["click_count"] += 1
            elif action == "collect":
                stats["collect_count"] += 1

        results = []
        for iid in item_ids:
            if iid in item_stats:
                stats = item_stats[iid]
                ctr = stats["click_count"] / max(stats["expose_count"], 1)
                results.append({
                    "entity_id": iid,
                    "expose_count": stats["expose_count"],
                    "click_count": stats["click_count"],
                    "collect_count": stats["collect_count"],
                    "ctr": round(ctr, 4),
                    "popularity_score": min(1.0, (stats["click_count"] * 2 + stats["collect_count"] * 3) / 100),
                })
        return results

    def generate_cross_features(self, user_id: str, item_ids: list[str]) -> list[dict[str, Any]]:
        """生成交叉特征（用户-物品）。

        基于用户历史行为和物品属性计算交叉特征。
        """
        if not item_ids:
            return []

        raw_records = self._raw_data.get("cross", [])
        user_history: set[str] = set()
        for record in raw_records:
            if record.get("user_id") == user_id and record.get("action") == "click":
                user_history.add(record.get("item_id", ""))

        results = []
        for iid in item_ids:
            results.append({
                "user_id": user_id,
                "item_id": iid,
                "has_interacted": iid in user_history,
                "interaction_strength": 1.0 if iid in user_history else 0.0,
            })
        return results
