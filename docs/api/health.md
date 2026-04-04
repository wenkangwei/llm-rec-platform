# 健康检查接口

## GET /api/health

```bash
curl http://localhost:8000/api/health
```

**响应：**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "components": {
    "pipeline": true,
    "redis": true,
    "mysql": false,
    "clickhouse": true
  }
}
```

- `status`: `"ok"`（全组件正常）或 `"degraded"`（部分组件不可用）
- `components`: 各组件健康状态，单组件不可用不影响服务

## GET /api/metrics

Prometheus 格式指标。

```bash
curl http://localhost:8000/api/metrics
# → text/plain, Prometheus exposition format
```

可用于 Prometheus 抓取（默认端口 9090 或 `/api/metrics`）。
