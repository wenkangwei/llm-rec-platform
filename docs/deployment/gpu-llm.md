# GPU LLM 部署

## vLLM 部署

```bash
# Docker Compose
docker-compose --profile gpu up -d llm-server

# 手动启动
docker run --gpus all -p 8001:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model qwen2.5-7b-instruct
```

## Ollama 部署

```bash
# 安装
curl -fsSL https://ollama.com/install.sh | sh

# 拉取模型
ollama pull qwen2.5:7b
ollama pull nomic-embed-text

# 启动（默认 11434 端口）
ollama serve
```

## 配置

```yaml
# configs/llm/llm.yaml
providers:
  - name: "ollama"
    type: "openai_compatible"
    base_url: "http://localhost:11434/v1"
    chat_model: "qwen2.5:7b"
    priority: 1

  - name: "vllm"
    type: "openai_compatible"
    base_url: "http://localhost:8001/v1"
    chat_model: "qwen2.5-7b-instruct"
    priority: 2
```

## 资源需求

| 模型 | GPU 显存 | 推荐显卡 |
|------|----------|----------|
| qwen2.5:7b | ~8GB | RTX 4070+ |
| qwen2.5:14b | ~16GB | RTX 4090 |
| nomic-embed-text | ~1GB | CPU 可用 |
