"""PyTorch 推理后端"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import torch

from pipeline.model_service.base import ModelService
from utils.logger import get_struct_logger

logger = get_struct_logger("torch_backend")


class TorchModel(ModelService):
    """PyTorch 模型推理后端。

    加载 .pt 文件，支持 GPU/CPU 推理。
    """

    def __init__(
        self,
        model_name: str,
        model_version: str = "v1",
        model_path: str = "",
        device: str = "auto",
    ):
        self._name = model_name
        self._version = model_version
        self._model_path = model_path
        self._device = self._resolve_device(device)
        self._model: torch.nn.Module | None = None

    @staticmethod
    def _resolve_device(device: str) -> str:
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device

    def name(self) -> str:
        return self._name

    def version(self) -> str:
        return self._version

    def warmup(self) -> None:
        if not self._model_path or not Path(self._model_path).exists():
            logger.warning(f"模型文件不存在: {self._model_path}，跳过加载")
            return
        self._model = torch.load(self._model_path, map_location=self._device, weights_only=False)
        self._model.eval()
        logger.info(f"PyTorch 模型加载完成: {self._name}", device=self._device)

    def predict(self, features: np.ndarray) -> np.ndarray:
        if self._model is None:
            return np.zeros(len(features))

        with torch.no_grad():
            tensor = torch.from_numpy(features.astype(np.float32)).to(self._device)
            output = self._model(tensor)
            return output.cpu().numpy().flatten()

    def shutdown(self) -> None:
        self._model = None
        if self._device == "cuda":
            torch.cuda.empty_cache()

    def health_check(self) -> bool:
        return self._model is not None
