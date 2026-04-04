# 监控追踪

## 核心组件

| 组件 | 文件 | 职责 |
|------|------|------|
| RecTracer | `monitor/tracer.py` | 每个 request 的阶段追踪 |
| RecMetrics | `monitor/metrics.py` | Prometheus 指标 |
| MonitorCollector | `monitor/collector.py` | 聚合 tracer + metrics |
| TrainingLogger | `monitor/training_logger.py` | JSONL 训练日志 + 标签回填 |
| TraceWriter | `monitor/writer.py` | 追踪写入抽象 |

## 追踪数据结构

```python
@dataclass
class PipelineTrace:
    request_id: str
    user_id: str
    stages: list[StageTrace]       # 每阶段延迟
    item_traces: dict[str, dict]   # item_id → {stage: score}
    total_latency_ms: float
```

## Sinks

| Sink | 类 | 输出 |
|------|-----|------|
| FileSink | `monitor.sinks.file.FileSink` | JSONL 文件（按日期轮转） |
| ClickHouseSink | `monitor.sinks.clickhouse.ClickHouseSink` | ClickHouse 批量写入 |
| TrainingSink | `monitor.sinks.training.TrainingSink` | 转为训练日志格式 |
| StdoutSink | `monitor.sinks.stdout.StdoutSink` | 控制台输出 |

## 配置

```yaml
# configs/monitor/monitor.yaml
enabled: true
sinks:
  - type: file
    path: "data/traces"
  - type: clickhouse
metrics:
  latency_buckets: [10, 50, 100, 200, 500, 1000]
```
