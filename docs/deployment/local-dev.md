# 本地开发环境

## 前置条件

- Python 3.10+
- Redis（可选，默认 Mock）
- Ollama 或 vLLM（可选，默认 Mock）

## 启动

```bash
# 安装依赖
pip install -e ".[dev]"

# 开发模式启动（自动降级到 Mock）
APP_ENV=development python -m uvicorn server.app:create_app --factory --port 8000 --reload

# 验证
curl http://localhost:8000/api/health
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| APP_ENV | development | 环境名 |
| REDIS_HOST | localhost | Redis 地址 |
| REDIS_PORT | 6379 | Redis 端口 |
| MYSQL_HOST | localhost | MySQL 地址 |
| OPENAI_API_KEY | 空 | OpenAI API Key |

## 开发模式行为

- 存储不可用时自动降级（不影响启动）
- LLM 不可用时降级到 MockBackend
- 热重载：`--reload` 参数
