# LLM 状态接口

查看和切换 LLM 后端 Provider。

## GET /api/llm/status

```bash
curl http://localhost:8000/api/llm/status
```

**响应（路由器模式）：**

```json
{
  "mode": "router",
  "active": "ollama",
  "providers": [
    {"name": "ollama", "status": "healthy", "is_active": true, "priority": 2},
    {"name": "vllm", "status": "unhealthy", "is_active": false, "priority": 2},
    {"name": "openai", "status": "healthy", "is_active": false, "priority": 1}
  ]
}
```

## POST /api/llm/select/{name}

手动切换到指定 Provider。

```bash
curl -X POST http://localhost:8000/api/llm/select/ollama
# → {"success": true, "active": "ollama"}
```

**错误响应：**

- `404` — `{"detail": "Provider 'xxx' 不存在"}`
- `400` — `{"detail": "当前非路由器模式，不支持手动切换"}`
