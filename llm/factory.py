"""LLM 工厂 — 根据配置创建后端实例"""

from __future__ import annotations

from typing import Any

from llm.base import LLMBackend
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.factory")


class LLMFactory:
    """LLM 后端工厂。"""

    @staticmethod
    def create(config: dict[str, Any]) -> LLMBackend:
        """根据配置创建 LLM 后端。配置中必须提供 base_url 等连接参数。"""
        backend_type = config.get("type", "openai_compatible")

        if backend_type == "openai_compatible":
            from llm.backends.vllm_backend import VLLMBackend
            base_url = config.get("base_url")
            if not base_url:
                raise ValueError("LLM 配置缺少 base_url，请在 llm.yaml 或环境变量中配置")
            return VLLMBackend(
                base_url=base_url,
                api_key=config.get("api_key", "EMPTY"),
                chat_model=config.get("chat_model", "qwen2.5-7b-instruct"),
                embed_model=config.get("embed_model", "bge-large-zh-v1.5"),
                timeout_sec=config.get("timeout_sec", 30),
                max_retries=config.get("max_retries", 2),
            )
        elif backend_type == "mock":
            from llm.backends.mock_backend import MockBackend
            return MockBackend()
        else:
            raise ValueError(f"不支持的 LLM 后端类型: {backend_type}")
