# PipelineExecutor

链路执行器，配置驱动加载和编排推荐阶段。

## 核心接口

```python
from pipeline.executor import PipelineExecutor

executor = PipelineExecutor(experiment_manager=exp_mgr)
executor.load_from_config(stage_configs)  # 从 YAML 加载
await executor.warmup_all()
ctx = await executor.execute(rec_context)
```

## 关键方法

| 方法 | 说明 |
|------|------|
| `register(stage)` | 注册阶段 |
| `load_from_config(configs)` | 从配置动态加载阶段 |
| `execute(ctx)` | 执行完整链路，返回 RecContext |
| `warmup_all()` | 预热所有阶段 |
| `shutdown_all()` | 关闭所有阶段 |
| `health_check()` | 返回 `{stage_name: bool}` |

## 配置驱动加载

```yaml
# configs/pipeline/pipeline.yaml
stages:
  - name: "recall"
    class: "pipeline.recall.merger.RecallMerger"
    timeout_ms: 50
```

`_load_stage` 通过 `importlib` 动态导入类并实例化。

## 执行流程

1. `_resolve_experiment(ctx)` — A/B 分桶，写入 `ctx.experiment_overrides`
2. 逐阶段执行 `stage.process(ctx)`
3. 每阶段记录 `StageMetrics`（延迟/输入输出数量）
4. 异常时标记 `ctx.degraded = True`，继续后续阶段

## 降级机制

单阶段失败不阻塞请求。失败阶段记入 `ctx.degraded_stages`，后续阶段正常执行。
