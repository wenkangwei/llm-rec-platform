"""批处理调度器 — 聚合请求提升 GPU 利用率"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import numpy as np

from pipeline.model_service.base import ModelService
from utils.logger import get_struct_logger

logger = get_struct_logger("batch_processor")


class BatchProcessor:
    """批处理调度器。

    在一个时间窗口内聚合多个推理请求，合并为一个 batch 提交给模型。
    减少模型调用次数，提升吞吐。
    """

    def __init__(
        self,
        model: ModelService,
        max_batch_size: int = 64,
        max_wait_ms: float = 5.0,
    ):
        self._model = model
        self._max_batch_size = max_batch_size
        self._max_wait_ms = max_wait_ms
        self._queue: list[tuple[np.ndarray, asyncio.Future]] = []
        self._running = False

    async def predict(self, features: np.ndarray) -> np.ndarray:
        """提交推理请求，等待批处理结果。"""
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        self._queue.append((features, future))

        if not self._running:
            self._running = True
            asyncio.create_task(self._process_batch())

        return await future

    async def _process_batch(self) -> None:
        """处理一批请求。"""
        await asyncio.sleep(self._max_wait_ms / 1000)

        batch = self._queue[:self._max_batch_size]
        self._queue = self._queue[self._max_batch_size:]

        if not batch:
            self._running = False
            return

        try:
            # 合并特征
            all_features = np.vstack([f for f, _ in batch])
            scores = self._model.predict(all_features)

            # 拆分结果
            offset = 0
            for features, future in batch:
                count = len(features)
                result = scores[offset:offset + count]
                if not future.done():
                    future.set_result(result)
                offset += count
        except Exception as e:
            for _, future in batch:
                if not future.done():
                    future.set_exception(e)

        if self._queue:
            asyncio.create_task(self._process_batch())
        else:
            self._running = False
