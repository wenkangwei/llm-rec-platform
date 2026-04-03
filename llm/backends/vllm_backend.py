"""vLLM 后端 — OpenAI 兼容协议"""

from __future__ import annotations

from typing import Any, AsyncIterator

from llm.base import LLMBackend
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.backends.vllm")


class VLLMBackend(LLMBackend):
    """vLLM 后端，通过 OpenAI 兼容 API 调用。

    支持任何兼容 OpenAI 协议的服务：vLLM / Ollama / Triton 等。
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8001/v1",
        api_key: str = "EMPTY",
        chat_model: str = "qwen2.5-7b-instruct",
        embed_model: str = "bge-large-zh-v1.5",
        timeout_sec: int = 30,
        max_retries: int = 2,
    ):
        self._base_url = base_url
        self._api_key = api_key
        self._chat_model = chat_model
        self._embed_model = embed_model
        self._timeout = timeout_sec
        self._max_retries = max_retries
        self._client = None

    async def warmup(self) -> None:
        """初始化 OpenAI 客户端。"""
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(
            base_url=self._base_url,
            api_key=self._api_key,
            timeout=self._timeout,
            max_retries=self._max_retries,
        )
        logger.info("vLLM 后端初始化完成", base_url=self._base_url)

    async def generate(self, prompt: str, **kwargs) -> str:
        """同步生成。"""
        if self._client is None:
            await self.warmup()

        model = kwargs.get("model", self._chat_model)
        max_tokens = kwargs.get("max_tokens", 2048)
        temperature = kwargs.get("temperature", 0.7)

        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM 生成失败", error=str(e))
            return ""

    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """流式生成。"""
        if self._client is None:
            await self.warmup()

        model = kwargs.get("model", self._chat_model)
        max_tokens = kwargs.get("max_tokens", 2048)
        temperature = kwargs.get("temperature", 0.7)

        try:
            stream = await self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"LLM 流式生成失败", error=str(e))
            yield f"[Error: {e}]"

    async def embed(self, text: str | list[str]) -> list[list[float]]:
        """生成 embedding。"""
        if self._client is None:
            await self.warmup()

        texts = [text] if isinstance(text, str) else text

        try:
            response = await self._client.embeddings.create(
                model=self._embed_model,
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"LLM Embedding 失败", error=str(e))
            return [[]]

    async def health_check(self) -> bool:
        """健康检查。"""
        try:
            if self._client is None:
                return False
            await self._client.models.list()
            return True
        except Exception:
            return False

    async def shutdown(self) -> None:
        """关闭客户端。"""
        if self._client:
            await self._client.close()
            self._client = None
