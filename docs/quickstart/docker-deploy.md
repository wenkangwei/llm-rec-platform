# Docker 部署

使用 Docker Compose 一键启动完整的 LLM 推荐系统平台，包括推荐服务、存储后端和监控栈。

## 服务概览

| 服务 | 端口 | 镜像 | 说明 |
|------|------|------|------|
| `rec-server` | 8000 (HTTP), 9090 (Metrics) | 自定义构建 | 推荐服务主进程 |
| `redis` | 6379 | `redis:7-alpine` | 缓存 / 召回通道数据 |
| `mysql` | 3306 | `mysql:8.0` | 用户特征 / 物品元数据 |
| `clickhouse` | 8123 (HTTP), 9000 (Native) | `clickhouse/clickhouse-server:24.1` | 链路追踪 / 监控数据 |
| `prometheus` | 9091 | `prom/prometheus:v2.50.0` | 指标采集 |
| `grafana` | 3000 | `grafana/grafana:10.3.0` | 可视化监控面板 |

## 快速启动

```bash
cd docker
docker-compose up -d
```

等待所有服务健康（约 30 秒）：

```bash
docker-compose ps
# 确认所有服务状态为 healthy / running
```

### 验证服务

```bash
# 推荐服务健康检查
curl http://localhost:8000/api/health | python -m json.tool
```

预期响应：

```json
{
    "status": "ok",
    "version": "0.1.0",
    "components": {
        "recall": true,
        "prerank": true,
        "rank": true,
        "rerank": true,
        "mixer": true,
        "redis": true,
        "mysql": true,
        "clickhouse": true
    }
}
```

### 发送推荐请求

```bash
curl -s -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user_001", "scene": "home_feed", "num": 10}' \
  | python -m json.tool
```

## GPU LLM 推理（可选）

如需启用本地 LLM 推理（用于 Agent 对话和智能运维），可通过 `gpu` profile 启动 vLLM 服务：

```bash
docker-compose --profile gpu up -d
```

!!! warning "GPU 前提条件"
    - 需要 NVIDIA GPU 及已安装 [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/)
    - 默认使用 `qwen2.5-7b-instruct` 模型，需约 16GB 显存
    - vLLM 服务映射到宿主机 `8001` 端口

启动后，`rec-server` 会自动检测 vLLM 服务并加入 LLM 路由（priority=2）。

## Grafana 监控面板

访问 [http://localhost:3000](http://localhost:3000)：

| 项目 | 值 |
|------|-----|
| 用户名 | `admin` |
| 密码 | `admin` |

Grafana 已预配置 Prometheus 和 ClickHouse 数据源，可查看推荐请求延迟、召回覆盖率、各阶段耗时等指标。

## 服务管理

```bash
# 查看日志
docker-compose logs -f rec-server

# 查看所有服务状态
docker-compose ps

# 停止所有服务
docker-compose down

# 停止并清除数据卷
docker-compose down -v
```

## Docker Compose 配置说明

```yaml
# docker/docker-compose.yaml 核心结构
services:
  rec-server:
    build:
      context: ..                           # 项目根目录
      dockerfile: docker/Dockerfile
    environment:
      - APP_ENV=production                  # 生产环境配置
      - REDIS_HOST=redis                    # 服务间通过容器名通信
      - MYSQL_HOST=mysql
      - CLICKHOUSE_HOST=clickhouse
    deploy:
      resources:
        limits:
          cpus: "4"
          memory: 8G
```

存储服务均配置了健康检查，`rec-server` 通过 `depends_on.condition: service_healthy` 确保存储就绪后才启动。

## 数据持久化

Docker Compose 使用命名卷持久化数据：

| 卷名 | 用途 |
|------|------|
| `redis-data` | Redis 数据 |
| `mysql-data` | MySQL 数据 |
| `ch-data` | ClickHouse 数据 |
| `model-cache` | HuggingFace 模型缓存 |

## 下一步

- [系统总览](../architecture/overview.md) — 了解各模块的架构设计
- [推荐流水线](../architecture/pipeline.md) — 5 级漏斗的详细说明
