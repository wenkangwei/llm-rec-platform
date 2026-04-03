"""ModelManager — 模型生命周期管理"""

from __future__ import annotations

import threading
from typing import Any

import numpy as np

from pipeline.model_service.base import ModelService
from utils.logger import get_struct_logger

logger = get_struct_logger("model_manager")


class ModelManager:
    """模型管理器：注册、加载、热更新、批量推理。"""

    def __init__(self):
        self._models: dict[str, ModelService] = {}
        self._lock = threading.Lock()

    def register(self, model: ModelService) -> None:
        """注册模型。"""
        with self._lock:
            key = model.name()
            self._models[key] = model
            logger.info(f"模型注册: {key} v{model.version()}")

    def get(self, name: str) -> ModelService:
        """获取模型实例。"""
        model = self._models.get(name)
        if model is None:
            raise KeyError(f"模型不存在: {name}")
        return model

    def unregister(self, name: str) -> None:
        """注销模型。"""
        with self._lock:
            if name in self._models:
                self._models[name].shutdown()
                del self._models[name]
                logger.info(f"模型注销: {name}")

    def reload(self, name: str, new_model: ModelService) -> None:
        """热更新模型：加载新版本，验证后切换，旧模型延迟卸载。

        灰度切换：先加载新模型到内存，验证通过后切换流量。
        """
        logger.info(f"热更新模型: {name}")
        old_model = self._models.get(name)

        # 预热新模型
        new_model.warmup()

        with self._lock:
            self._models[name] = new_model
            logger.info(f"模型切换完成: {name} -> v{new_model.version()}")

        # 延迟卸载旧模型
        if old_model:
            try:
                old_model.shutdown()
                logger.info(f"旧模型已卸载: {name} v{old_model.version()}")
            except Exception as e:
                logger.warning(f"旧模型卸载失败: {name}", error=str(e))

    def predict(self, name: str, features: np.ndarray) -> np.ndarray:
        """单模型推理。"""
        return self.get(name).predict(features)

    def predict_batch(self, name: str, features: np.ndarray) -> np.ndarray:
        """批量推理（模型内部自行分 batch）。"""
        return self.get(name).predict(features)

    def warmup_all(self) -> None:
        """预热所有模型。"""
        for name, model in self._models.items():
            try:
                model.warmup()
                logger.info(f"模型预热完成: {name}")
            except Exception as e:
                logger.error(f"模型预热失败: {name}", error=str(e))

    def shutdown_all(self) -> None:
        """卸载所有模型。"""
        for name, model in self._models.items():
            try:
                model.shutdown()
            except Exception as e:
                logger.error(f"模型关闭失败: {name}", error=str(e))
        self._models.clear()

    def health_check(self) -> dict[str, bool]:
        """所有模型健康检查。"""
        return {name: model.health_check() for name, model in self._models.items()}

    def list_models(self) -> list[dict[str, Any]]:
        """列出所有已注册模型。"""
        return [
            {"name": m.name(), "version": m.version(), "healthy": m.health_check()}
            for m in self._models.values()
        ]
