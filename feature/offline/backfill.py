"""特征回填"""

from __future__ import annotations

from typing import Any

from utils.logger import get_struct_logger

logger = get_struct_logger("feature.offline.backfill")


class FeatureBackfill:
    """特征回填：对历史数据补算新特征。"""

    async def backfill(self, entity_type: str, entity_ids: list[str], feature_names: list[str]) -> int:
        """回填特征。"""
        logger.info(f"特征回填: {entity_type}", count=len(entity_ids), features=feature_names)
        # TODO: 读取历史数据，计算特征，写回存储
        return 0
