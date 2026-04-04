# LLM 多厂商集成

## 配置多 Provider

编辑 `configs/llm/llm.yaml`：

```yaml
providers:
  - name: "ollama"
    type: "openai_compatible"
    base_url: "http://localhost:11434/v1"
    api_key: "EMPTY"
    chat_model: "qwen2.5:7b"
    embed_model: "nomic-embed-text:latest"
    priority: 1           # 数值越小优先级越高

  - name: "openai"
    type: "openai_compatible"
    base_url: "https://api.openai.com/v1"
    api_key: "${env:OPENAI_API_KEY:}"
    chat_model: "gpt-4o-mini"
    priority: 2

routing:
  strategy: "priority"
  health_check_interval: 60
  fallback_on_error: true
```

## 支持的后端类型

| type | 类 | 说明 |
|------|-----|------|
| `openai_compatible` | `VLLMBackend` | 兼容 OpenAI API（vLLM/Ollama/等） |
| `triton` | `TritonLLMBackend` | NVIDIA Triton（gRPC） |
| `mock` | `MockBackend` | 测试用 Mock |

## 自动降级

`LLMRouter` 按 priority 升序排列 Provider：

1. 启动时 warmup 所有 Provider，选第一个可用的作为 active
2. 请求失败自动切换到下一个可用 Provider
3. 后台定期 health check 恢复之前失败的 Provider

## 手动切换

```bash
# 查看状态
curl http://localhost:8000/api/llm/status

# 切换到 ollama
curl -X POST http://localhost:8000/api/llm/select/ollama
```

## 代码中使用

```python
from llm.factory import LLMFactory

# 创建路由器
router = LLMFactory.create_router(llm_config)
await router.warmup()

# 透明使用，和单后端完全一致
response = await router.generate("你好")
embedding = await router.embed(["文本"])
```
