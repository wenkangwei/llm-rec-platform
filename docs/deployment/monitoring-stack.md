# Prometheus + Grafana 监控栈

## 架构

```
rec-server (/api/metrics) → Prometheus (:9091) → Grafana (:3000)
                               ↑
                         ClickHouse (:8123)
```

## Prometheus 配置

```yaml
# docker/conf/prometheus.yml
scrape_configs:
  - job_name: "rec-server"
    scrape_interval: 15s
    static_configs:
      - targets: ["rec-server:9090"]
```

## Grafana

访问 `http://localhost:3000`（admin/admin）。

预配置数据源：
- Prometheus（指标查询）
- ClickHouse（追踪分析）

## 关键指标

| 指标 | 类型 | 说明 |
|------|------|------|
| `rec_request_duration_ms` | histogram | 请求延迟分布 |
| `rec_request_total` | counter | 请求总数 |
| `rec_stage_duration_ms` | histogram | 各阶段延迟 |
| `rec_recall_coverage` | gauge | 召回覆盖率 |
| `rec_llm_request_duration_ms` | histogram | LLM 调用延迟 |

## 告警规则

```yaml
# Prometheus alert rules
- alert: HighLatency
  expr: histogram_quantile(0.99, rec_request_duration_ms) > 200
  for: 5m
  labels: {severity: warning}
```
