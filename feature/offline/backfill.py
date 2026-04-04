"""特征回填 — 对历史数据补算新特征"""

from __future__ import annotations

from typing import Any

from utils.logger import get_struct_logger

logger = get_struct_logger("feature.offline.backfill")


class FeatureBackfill:
    """特征回填：对历史数据补算新特征。

    读取历史实体数据，使用 OfflineFeatureGenerator 计算特征，
    写入特征存储（Redis/MySQL）。
    """

    def __init__(self, batch_size: int = 1000):
        self._batch_size = batch_size
        self._store: Any = None
        self._generator: Any = None

    def configure(self, store: Any = None, generator: Any = None) -> None:
        """配置特征存储和生成器。

        Args:
            store: 特征存储后端（需支持 async set 方法）
            generator: OfflineFeatureGenerator 实例
        """
        self._store = store
        self._generator = generator

    async def backfill(
        self,
        entity_type: str,
        entity_ids: list[str],
        feature_names: list[str],
    ) -> int:
        """回填特征。

        按批次处理：读取 → 计算 → 写回。

        Args:
            entity_type: "user" / "item"
            entity_ids: 需要回填的实体 ID 列表
            feature_names: 需要回填的特征名列表

        Returns:
            成功回填的实体数
        """
        if not entity_ids:
            logger.warning("回填实体列表为空")
            return 0

        logger.info(f"特征回填: {entity_type}", count=len(entity_ids), features=feature_names)
        total_written = 0

        # 按批处理
        for i in range(0, len(entity_ids), self._batch_size):
            batch_ids = entity_ids[i : i + self._batch_size]

            # 生成特征
            features_list = self._compute_features(entity_type, batch_ids, feature_names)
            if not features_list:
                continue

            # 写回存储
            written = await self._write_features(entity_type, features_list)
            total_written += written

            logger.info(
                f"回填批次完成",
                batch=i // self._batch_size + 1,
                batch_size=len(batch_ids),
                written=written,
            )

        logger.info(f"特征回填完成", entity_type=entity_type, total=total_written)
        return total_written

    def _compute_features(
        self,
        entity_type: str,
        entity_ids: list[str],
        feature_names: list[str],
    ) -> list[dict[str, Any]]:
        """计算一批实体的特征。"""
        if self._generator is None:
            logger.warning("特征生成器未配置，跳过计算")
            return []

        try:
            if entity_type == "user":
                return self._generator.generate_user_features(entity_ids)
            elif entity_type == "item":
                return self._generator.generate_item_features(entity_ids)
            else:
                logger.warning(f"未知实体类型: {entity_type}")
                return []
        except Exception as e:
            logger.error(f"特征计算失败", error=str(e))
            return []

    async def _write_features(self, entity_type: str, features_list: list[dict[str, Any]]) -> int:
        """将特征写入存储。"""
        if self._store is None:
            # 无存储时只记录
            logger.debug(f"无存储后端，跳过写入 {len(features_list)} 条")
            return len(features_list)

        written = 0
        for feat_dict in features_list:
            entity_id = feat_dict.pop("entity_id", None)
            if not entity_id:
                continue
            try:
                await self._store.set(entity_id, feat_dict)
                written += 1
            except Exception as e:
                logger.error(f"写入失败: {entity_id}", error=str(e))

        return written
