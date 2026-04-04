# 第一个推荐请求

本页说明如何启动 LLM 推荐系统平台并发送推荐请求和对话请求。

## 启动服务

=== "python -m"

    ```bash
    python -m server.app
    ```

=== "uvicorn"

    ```bash
    uvicorn server.app:create_app --factory --host 0.0.0.0 --port 8000
    ```

启动后会看到类似日志：

```
INFO  服务启动中... host=0.0.0.0 port=8000
INFO  LLM 后端初始化完成
INFO  ExperimentManager 初始化完成 experiments=0
INFO  Pipeline 初始化完成 stages=5
INFO  Redis 连接完成
INFO  服务启动完成
```

!!! warning "存储连接失败"
    如果 Redis / MySQL / ClickHouse 未运行，服务仍可启动（优雅降级模式），
    但部分功能（如多路召回、实验分流）会不可用。建议先通过 [Docker 部署](docker-deploy.md) 启动存储服务。

## 推荐请求

发送首页推荐请求：

```bash
curl -s -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "scene": "home_feed",
    "num": 10
  }' | python -m json.tool
```

响应示例：

```json
{
    "request_id": "req_a1b2c3d4",
    "items": [
        {
            "item_id": "item_1001",
            "score": 0.9523,
            "source": "personalized",
            "summary": null,
            "extra": null
        },
        {
            "item_id": "item_2048",
            "score": 0.8710,
            "source": "hot",
            "summary": null,
            "extra": null
        }
    ],
    "trace_id": "trace_x1y2z3",
    "total": 10,
    "page": 0,
    "has_more": false
}
```

响应字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `request_id` | string | 请求唯一标识 |
| `items` | array | 推荐结果列表 |
| `items[].item_id` | string | 物品 ID |
| `items[].score` | float | 最终排序分数 |
| `items[].source` | string | 来源通道（personalized / hot / social 等） |
| `trace_id` | string | 全链路追踪 ID |
| `total` | int | 结果总数 |
| `has_more` | bool | 是否有更多结果 |

## 对话请求

通过自然语言与系统交互，查询监控指标、调整推荐策略：

```bash
curl -s -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "查看系统延迟指标"
  }' | python -m json.tool
```

响应示例：

```json
{
    "session_id": "sess_abc123",
    "reply": "当前系统状态：Pipeline 共 5 个阶段..."
}
```

!!! info "LLM Agent"
    对话功能基于 ReAct Agent 实现。如需使用完整 Agent 能力，请配置至少一个 LLM 后端（参见 [LLM 配置](../architecture/llm-module.md)）。

## 健康检查

```bash
curl http://localhost:8000/api/health | python -m json.tool
```

响应示例：

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

当部分组件不可用时，`status` 为 `"degraded"`，对应的组件值为 `false`。

## 更多接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/recommend` | 推荐请求 |
| POST | `/api/search` | 搜索推荐 |
| POST | `/api/chat` | 对话（HTTP） |
| POST | `/api/chat/stream` | 对话（SSE 流式） |
| WS | `/api/ws/chat` | 对话（WebSocket） |
| POST | `/api/track` | 行为上报 |
| GET | `/api/health` | 健康检查 |
| GET | `/api/metrics` | Prometheus 指标 |

## 下一步

- [Docker 部署](docker-deploy.md) — 启动完整的存储和监控服务栈
- [系统总览](../architecture/overview.md) — 了解平台整体架构设计
