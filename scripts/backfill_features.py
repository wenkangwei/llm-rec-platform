#!/usr/bin/env python3
"""特征回填脚本 — 对历史数据补算新特征"""

from __future__ import annotations

import argparse
import asyncio

from feature.offline.backfill import FeatureBackfill
from utils.logger import get_struct_logger

logger = get_struct_logger("scripts.backfill")


async def main(
    entity_type: str = "user",
    feature_names: list[str] | None = None,
    batch_size: int = 1000,
):
    backfill = FeatureBackfill()
    feature_names = feature_names or ["long_term_interests", "behavior_stats"]

    logger.info(f"开始特征回填", entity_type=entity_type, features=feature_names)

    # TODO: 从数据库分页读取 entity_ids
    entity_ids: list[str] = []

    count = await backfill.backfill(entity_type, entity_ids, feature_names)
    logger.info(f"特征回填完成", count=count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="特征回填")
    parser.add_argument("--entity-type", default="user", choices=["user", "item"])
    parser.add_argument("--features", nargs="+", default=None)
    args = parser.parse_args()

    asyncio.run(main(entity_type=args.entity_type, feature_names=args.features))
