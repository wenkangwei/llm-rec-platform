"""ONNX Runtime 推理后端"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from pipeline.model_service.base import ModelService
from utils.logger import get_struct_logger

logger = get_struct_logger("onnx_backend")


class ONNXModel(ModelService):
    """ONNX Runtime 推理后端，适合生产部署优化。"""

    def __init__(self, model_name: str, model_version: str = "v1", model_path: str = ""):
        self._name = model_name
        self._version = model_version
        self._model_path = model_path
        self._session = None

    def name(self) -> str:
        return self._name

    def version(self) -> str:
        return self._version

    def warmup(self) -> None:
        if not self._model_path or not Path(self._model_path).exists():
            logger.warning(f"ONNX 模型文件不存在: {self._model_path}，跳过加载")
            return
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self._session = ort.InferenceSession(self._model_path, opts)
        logger.info(f"ONNX 模型加载完成: {self._name}")

    def predict(self, features: np.ndarray) -> np.ndarray:
        if self._session is None:
            return np.zeros(len(features))

        input_name = self._session.get_inputs()[0].name
        output = self._session.run(None, {input_name: features.astype(np.float32)})
        return output[0].flatten()

    def shutdown(self) -> None:
        self._session = None

    def health_check(self) -> bool:
        return self._session is not None
