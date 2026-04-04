"""Triton Inference Server 后端 — LLM 推理"""

from __future__ import annotations

from typing import Any, AsyncIterator

import numpy as np

from llm.base import LLMBackend
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.backends.triton")


class TritonLLMBackend(LLMBackend):
    """NVIDIA Triton Inference Server LLM 后端。

    通过 tritonclient 库与 Triton 通信，支持文本生成和 embedding。
    当 tritonclient 不可用时降级为 Mock 行为。
    """

    def __init__(
        self,
        server_url: str = "localhost:8001",  # gRPC 端口
        model_name: str = "llm",
        embed_model_name: str = "embedding",
        protocol: str = "grpc",  # "grpc" or "http"
        timeout_sec: int = 30,
    ):
        self._server_url = server_url
        self._model_name = model_name
        self._embed_model_name = embed_model_name
        self._protocol = protocol
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
            logger.warning("tritonclient 未安装，TritonLLMBackend 降级为 Mock")
            self._triton_available = False
            return None

    async def warmup(self) -> None:
        """初始化 Triton 客户端连接。"""
        triton = self._try_import_triton()
        if triton is None:
            logger.info("Triton 后端降级模式（Mock）")
            return

        try:
            if self._protocol == "grpc":
                self._client = triton.InferenceServerClient(
                    url=self._server_url, timeout=self._timeout
                )
            else:
                self._client = triton.InferenceServerClient(
                    url=self._server_url, timeout=self._timeout
                )
            logger.info(f"Triton LLM 后端初始化完成", url=self._server_url, model=self._model_name)
        except Exception as e:
            logger.error(f"Triton 连接失败", error=str(e))
            self._client = None

    async def generate(self, prompt: str, **kwargs) -> str:
        """同步文本生成。"""
        if self._client is None:
            return ""

        triton = self._try_import_triton()
        if triton is None:
            return ""

        try:
            max_tokens = kwargs.get("max_tokens", 2048)
            temperature = kwargs.get("temperature", 0.7)

            input_text = np.array([prompt.encode("utf-8")], dtype=object)
            inputs = [
                triton.InferInput("text_input", input_text.shape, "BYTES"),
            ]
            inputs[0].set_data_from_numpy(input_text)

            outputs = [
                triton.InferRequestedOutput("text_output"),
            ]

            result = self._client.infer(
                model_name=self._model_name,
                inputs=inputs,
                outputs=outputs,
            )
            output_text = result.as_numpy("text_output")
            return output_text[0].decode("utf-8") if output_text.size > 0 else ""
        except Exception as e:
            logger.error(f"Triton 生成失败", error=str(e))
            return ""

    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """流式文本生成。"""
        # Triton 的流式推理需要特定模型支持
        # 降级为同步生成
        result = await self.generate(prompt, **kwargs)
        if result:
            yield result

    async def embed(self, text: str | list[str]) -> list[list[float]]:
        """生成 embedding。"""
        if self._client is None:
            return [[]]

        triton = self._try_import_triton()
        if triton is None:
            return [[]]

        texts = [text] if isinstance(text, str) else text

        try:
            input_data = np.array([t.encode("utf-8") for t in texts], dtype=object)
            inputs = [
                triton.InferInput("text_input", input_data.shape, "BYTES"),
            ]
            inputs[0].set_data_from_numpy(input_data)

            outputs = [
                triton.InferRequestedOutput("embedding"),
            ]

            result = self._client.infer(
                model_name=self._embed_model_name,
                inputs=inputs,
                outputs=outputs,
            )
            embeddings = result.as_numpy("embedding")
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Triton Embedding 失败", error=str(e))
            return [[]]

    async def health_check(self) -> bool:
        """健康检查。"""
        if self._client is None:
            return False
        try:
            return self._client.is_server_live()
        except Exception:
            return False

    async def shutdown(self) -> None:
        """关闭连接。"""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.debug(f"Triton 降级", error=str(e))
            self._client = None
