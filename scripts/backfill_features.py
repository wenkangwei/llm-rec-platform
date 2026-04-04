#!/usr/bin/env python3
"""特征回填脚本 — 对历史数据补算新特征"""

from __future__ import annotations

import argparse
import asyncio

from feature.offline.backfill import FeatureBackfill
from feature.offline.feature_gen import OfflineFeatureGenerator
from utils.logger import get_struct_logger

logger = get_struct_logger("scripts.backfill")


async def main(
    entity_type: str = "user",
    feature_names: list[str] | None = None,
    batch_size: int = 1000,
    data_source: str = "data/backfill/",
):
    backfill = FeatureBackfill(batch_size=batch_size)
    generator = OfflineFeatureGenerator()
    backfill.configure(generator=generator)

    feature_names = feature_names or ["long_term_interests", "behavior_stats"]

    logger.info(f"开始特征回填", entity_type=entity_type, features=feature_names)

    # 从数据源读取 entity_ids
    entity_ids = _load_entity_ids(entity_type, data_source)

    if not entity_ids:
        logger.warning(f"未找到 {entity_type} 实体数据，跳过回填")
        return

    count = await backfill.backfill(entity_type, entity_ids, feature_names)
    logger.info(f"特征回填完成", count=count)


def _load_entity_ids(entity_type: str, data_source: str) -> list[str]:
    """从数据源加载实体 ID 列表。

    支持从文本文件（每行一个 ID）或 Parquet 文件加载。
    """
    import os

    # 尝试文本文件
    txt_path = os.path.join(data_source, f"{entity_type}_ids.txt")
    if os.path.exists(txt_path):
        with open(txt_path) as f:
            ids = [line.strip() for line in f if line.strip()]
        logger.info(f"从文本文件加载 {len(ids)} 个实体 ID", path=txt_path)
        return ids

    # 尝试 Parquet 文件
    parquet_path = os.path.join(data_source, f"{entity_type}_ids.parquet")
    if os.path.exists(parquet_path):
        try:
            import pandas as pd
            df = pd.read_parquet(parquet_path)
            id_col = "entity_id" if "entity_id" in df.columns else df.columns[0]
            ids = df[id_col].astype(str).tolist()
            logger.info(f"从 Parquet 加载 {len(ids)} 个实体 ID", path=parquet_path)
            return ids
        except Exception as e:
            logger.error(f"Parquet 加载失败", error=str(e))
            return []

    # 无数据文件时，生成示例 ID 用于测试
    logger.warning(f"数据源目录不存在: {data_source}，生成示例 ID")
    return [f"{entity_type}_{i}" for i in range(100)]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="特征回填")
    parser.add_argument("--entity-type", default="user", choices=["user", "item"])
    parser.add_argument("--features", nargs="+", default=None)
    parser.add_argument("--data-source", default="data/backfill/")
    args = parser.parse_args()

    asyncio.run(main(entity_type=args.entity_type, feature_names=args.features, data_source=args.data_source))
