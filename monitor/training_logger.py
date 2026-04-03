"""训练日志落盘 — 异步写入 Parquet 文件"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from utils.logger import get_struct_logger

logger = get_struct_logger("monitor.training_logger")


class TrainingLogger:
    """训练日志异步落盘。

    1. 推荐请求完成后，异步写入实时日志（JSON Lines）
    2. 用户行为上报后，延迟回填 label 字段
    3. 离线 T+1 合并特征 + 标签，生成训练样本
    """

    def __init__(self, output_dir: str = "data/training", flush_interval: int = 100):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._flush_interval = flush_interval
        self._buffer: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    async def log(self, entry: dict[str, Any]) -> None:
        """异步写入一条训练日志。"""
        entry["log_time"] = time.time()
        async with self._lock:
            self._buffer.append(entry)
            if len(self._buffer) >= self._flush_interval:
                await self._flush()

    async def log_batch(self, entries: list[dict[str, Any]]) -> None:
        """批量写入。"""
        for entry in entries:
            await self.log(entry)

    async def _flush(self) -> None:
        """将缓冲区写入文件。"""
        if not self._buffer:
            return

        buffer = self._buffer.copy()
        self._buffer.clear()

        # 按日期分文件
        date_str = time.strftime("%Y%m%d")
        filepath = self._output_dir / f"training_log_{date_str}.jsonl"

        try:
            with open(filepath, "a", encoding="utf-8") as f:
                for entry in buffer:
                    f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            logger.debug(f"训练日志落盘: {len(buffer)} 条", file=str(filepath))
        except Exception as e:
            logger.error(f"训练日志落盘失败", error=str(e))

    async def close(self) -> None:
        """关闭时 flush 剩余日志。"""
        async with self._lock:
            await self._flush()

    async def backfill_labels(self, request_id: str, item_id: str, labels: dict[str, Any]) -> None:
        """延迟回填标签。

        在用户行为上报时调用，找到对应的训练日志并补充 label。
        生产环境应使用 ClickHouse/Parquet 的 UPDATE 能力。
        """
        # 简化实现：追加一条 label 回填日志
        await self.log({
            "type": "label_backfill",
            "request_id": request_id,
            "item_id": item_id,
            **labels,
        })
