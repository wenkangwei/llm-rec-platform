# Docker Compose 部署

## 服务列表

| 服务 | 端口 | 说明 |
|------|------|------|
| rec-server | 8000 | 推荐服务 API |
| redis | 6379 | 缓存/特征存储 |
| mysql | 3306 | 用户/内容数据 |
| clickhouse | 8123/9000 | 追踪/分析 |
| prometheus | 9091 | 指标采集 |
| grafana | 3000 | 监控面板 |

## 启动

```bash
cd docker

# 基础启动（不含 GPU LLM）
docker-compose up -d

# 含 GPU LLM
docker-compose --profile gpu up -d

# 查看日志
docker-compose logs -f rec-server
```

## 数据持久化

| Volume | 服务 | 说明 |
|--------|------|------|
| redis-data | Redis | 缓存数据 |
| mysql-data | MySQL | 业务数据 |
| ch-data | ClickHouse | 分析数据 |
| model-cache | vLLM | HuggingFace 模型缓存 |

## 验证

```bash
curl http://localhost:8000/api/health
# → {"status": "ok", "components": {...}}

# Grafana
open http://localhost:3000  # admin/admin
```
