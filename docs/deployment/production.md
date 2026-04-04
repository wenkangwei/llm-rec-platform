# 生产环境部署

## 配置

```bash
APP_ENV=production python -m uvicorn server.app:create_app --factory --port 8000 --workers 4
```

## 生产环境覆盖

```yaml
# configs/environments/production.yaml
server:
  workers: 4
  log_level: WARNING
storage:
  redis:
    host: ${env:REDIS_HOST:redis}
    max_connections: 50
  mysql:
    host: ${env:MYSQL_HOST:mysql}
    pool_size: 20
```

## 性能调优

| 参数 | 建议 | 说明 |
|------|------|------|
| workers | CPU 核数 | uvicorn worker 数 |
| pipeline timeout | 50ms | 总链路延迟上限 |
| recall top_k | 3000 | 召回候选数 |
| rank batch_size | 64 | 排序批大小 |
| embed cache | 10000 | 特征缓存大小 |

## 高可用

- 多实例部署 + Nginx 负载均衡
- Redis Sentinel / Cluster
- MySQL 主从
- ClickHouse 副本
- LLMRouter 自动降级

## 监控告警

- Prometheus 采集 `/api/metrics`
- Grafana 仪表盘（预配置）
- 告警规则：P99 > 200ms、QPS 异常、错误率 > 1%
