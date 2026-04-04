# LLM 后端抽象

## LLMBackend 接口

所有 LLM 后端实现 `LLMBackend` 抽象类：

```python
from llm.base import LLMBackend

class LLMBackend(ABC):
    async def generate(self, prompt: str, **kwargs) -> str
    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]
    async def embed(self, texts: list[str]) -> list[list[float]]
    async def health_check(self) -> bool
    async def warmup(self) -> None
    async def shutdown(self) -> None
```

## 后端实现

| 后端 | 类 | 适用场景 |
|------|-----|----------|
| OpenAI 兼容 | `VLLMBackend` | vLLM、Ollama、OpenAI 等 |
| Triton | `TritonLLMBackend` | NVIDIA Triton（gRPC） |
| Mock | `MockBackend` | 开发测试 |

## VLLMBackend

兼容所有 OpenAI API 协议的服务（vLLM、Ollama、LocalAI 等）。

```python
from llm.backends.vllm_backend import VLLMBackend

backend = VLLMBackend(
    base_url="http://localhost:11434/v1",
    api_key="EMPTY",
    chat_model="qwen2.5:7b",
    embed_model="nomic-embed-text:latest",
    timeout_sec=30
)
```

## 工厂创建

```python
from llm.factory import LLMFactory

# 单后端
backend = LLMFactory.create({"type": "openai_compatible", "base_url": "..."})

# 按 Provider 配置
backend = LLMFactory.create_from_provider(provider_config)

# 多 Provider 路由器
router = LLMFactory.create_router(llm_config)
```
