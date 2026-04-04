"""Triton Inference Server 模型推理后端"""

from __future__ import annotations

from typing import Any

import numpy as np

from pipeline.model_service.base import ModelService
from utils.logger import get_struct_logger

logger = get_struct_logger("triton_model_backend")


class TritonModel(ModelService):
    """NVIDIA Triton Inference Server 模型推理后端。

    通过 tritonclient 库与 Triton 通信，支持 GPU 加速推理。
    当 tritonclient 不可用时降级为零输出。
    """

    def __init__(
        self,
        model_name: str,
        model_version: str = "v1",
        server_url: str = "localhost:8001",
        protocol: str = "grpc",  # "grpc" or "http"
        input_name: str = "input",
        output_name: str = "output",
        timeout_sec: int = 30,
    ):
        self._name = model_name
        self._version = model_version
        self._server_url = server_url
        self._protocol = protocol
        self._input_name = input_name
        self._output_name = output_name
        self._timeout = timeout_sec
        self._client: Any = None
        self._triton_available = False

    def _try_import_triton(self) -> Any:
        """尝试导入 tritonclient。"""
        try:
            if self._protocol == "grpc":
                import tritonclient.grpc as triton
            else:
                import tritonclient.http as triton
            self._triton_available = True
            return triton
        except ImportError:
            self._triton_available = False
            return None

    def name(self) -> str:
        return self._name

    def version(self) -> str:
        return self._version

    def warmup(self) -> None:
        """初始化 Triton 客户端连接。"""
        triton = self._try_import_triton()
        if triton is None:
            logger.warning(f"tritonclient 未安装，TritonModel({self._name}) 降级为零输出")
            return

        try:
            self._client = triton.InferenceServerClient(
                url=self._server_url, timeout=self._timeout
            )
            # 验证模型可用
            if not self._client.is_model_ready(self._name):
                logger.warning(f"Triton 模型未就绪: {self._name}")
                self._client = None
                return
            logger.info(f"Triton 模型后端初始化完成", model=self._name, url=self._server_url)
        except Exception as e:
            logger.error(f"Triton 连接失败: {self._name}", error=str(e))
            self._client = None

    def predict(self, features: np.ndarray) -> np.ndarray:
        """执行模型推理。"""
        if self._client is None:
            return np.zeros(len(features))

        triton = self._try_import_triton()
        if triton is None:
            return np.zeros(len(features))

        try:
            input_data = features.astype(np.float32)
            inputs = [
                triton.InferInput(self._input_name, input_data.shape, "FP32"),
            ]
            inputs[0].set_data_from_numpy(input_data)

            outputs = [
                triton.InferRequestedOutput(self._output_name),
            ]

            result = self._client.infer(
                model_name=self._name,
                inputs=inputs,
                outputs=outputs,
            )
            return result.as_numpy(self._output_name).flatten()
        except Exception as e:
            logger.error(f"Triton 推理失败: {self._name}", error=str(e))
            return np.zeros(len(features))

    def shutdown(self) -> None:
        """关闭连接。"""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.debug(f"Triton 降级", error=str(e))
            self._client = None

    def health_check(self) -> bool:
        """健康检查。"""
        if self._client is None:
            return False
        try:
            return self._client.is_model_ready(self._name)
        except Exception:
            return False
