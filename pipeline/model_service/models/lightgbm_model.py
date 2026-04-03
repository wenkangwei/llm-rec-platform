"""LightGBM 粗排模型"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.model_service.base import ModelService
from utils.logger import get_struct_logger

logger = get_struct_logger("lightgbm_model")


class LightGBMModel(ModelService):
    """LightGBM 粗排模型：快速打分，从万级降至千级。"""

    def __init__(self, model_name: str = "lightgbm", model_version: str = "v1", model_path: str = ""):
        self._name = model_name
        self._version = model_version
        self._model_path = model_path
        self._model = None

    def name(self) -> str:
        return self._name

    def version(self) -> str:
        return self._version

    def warmup(self) -> None:
        if self._model_path and Path(self._model_path).exists():
            import lightgbm as lgb
            self._model = lgb.Booster(model_file=self._model_path)
            logger.info(f"LightGBM 模型加载完成: {self._name}")
        else:
            logger.warning(f"LightGBM 模型文件不存在: {self._model_path}，使用随机打分降级")

    def predict(self, features: np.ndarray) -> np.ndarray:
        if self._model is None:
            return np.random.random(len(features)).astype(np.float32)
        return self._model.predict(features)

    def shutdown(self) -> None:
        self._model = None

    def health_check(self) -> bool:
        return True  # 降级模式下始终可用
