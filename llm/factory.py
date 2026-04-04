"""LLM 工厂 — 根据配置创建后端实例，支持多 provider 路由"""

from __future__ import annotations

from typing import Any

from llm.base import LLMBackend
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.factory")


class LLMFactory:
    """LLM 后端工厂。"""

    @staticmethod
    def create(config: dict[str, Any]) -> LLMBackend:
        """根据配置创建单个 LLM 后端（向后兼容）。"""
        backend_type = config.get("type", "openai_compatible")

        if backend_type == "openai_compatible":
            from llm.backends.vllm_backend import VLLMBackend
            base_url = config.get("base_url")
            if not base_url:
                raise ValueError("LLM 配置缺少 base_url，请在 llm.yaml 或环境变量中配置")
            return VLLMBackend(
                base_url=base_url,
                api_key=config.get("api_key", "EMPTY"),
                chat_model=config.get("chat_model", config.get("model", "qwen2.5:7b")),
                embed_model=config.get("embed_model", ""),
                timeout_sec=config.get("timeout_sec", 30),
                max_retries=config.get("max_retries", 2),
            )
        elif backend_type == "triton":
            from llm.backends.triton_backend import TritonLLMBackend
            return TritonLLMBackend(
                server_url=config.get("base_url", "localhost:8001"),
                model_name=config.get("chat_model", "llm"),
                embed_model_name=config.get("embed_model", "embedding"),
                protocol=config.get("protocol", "grpc"),
                timeout_sec=config.get("timeout_sec", 30),
            )
        elif backend_type == "mock":
            from llm.backends.mock_backend import MockBackend
            return MockBackend()
        else:
            raise ValueError(f"不支持的 LLM 后端类型: {backend_type}")

    @staticmethod
    def create_from_provider(provider: dict[str, Any]) -> LLMBackend:
        """根据单个 provider 配置创建后端实例。"""
        return LLMFactory.create(provider)

    @staticmethod
    def create_router(config: dict[str, Any]) -> Any:
        """从配置创建 LLMRouter（多 provider 路由器）。

        config 需包含:
        - providers: list[dict] — provider 配置列表
        - routing: dict — 路由策略配置（可选）
        """
        from llm.router import LLMRouter

        providers = config.get("providers", [])
        routing = config.get("routing", {})

        if not providers:
            raise ValueError("providers 列表为空，请在 llm.yaml 中配置至少一个 LLM provider")

        return LLMRouter(providers=providers, routing=routing)
