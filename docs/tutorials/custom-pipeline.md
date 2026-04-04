# 自定义推荐链路

## PipelineStage 接口

所有链路模块实现 `PipelineStage` 抽象类：

```python
from pipeline.base import PipelineStage
from protocols.schemas.context import RecContext

class MyStage(PipelineStage):
    def name(self) -> str:
        return "my_stage"

    def process(self, ctx: RecContext) -> RecContext:
        # 在 ctx.candidates 上做处理
        ctx.candidates = [item for item in ctx.candidates if item.score > 0.5]
        return ctx

    def warmup(self) -> None:
        # 加载模型等
        pass
```

## 注册到链路

**方式一：配置文件**（推荐）

```yaml
# configs/pipeline/pipeline.yaml
stages:
  - name: "recall"
    class: "pipeline.recall.merger.RecallMerger"
  - name: "my_stage"
    class: "my_package.my_module.MyStage"
    timeout_ms: 20
```

**方式二：代码注册**

```python
executor = PipelineExecutor()
executor.register(MyStage())
```

## 执行流程

`PipelineExecutor.execute(ctx)` 按 stages 列表顺序执行，每阶段：

1. 记录输入候选数量
2. 调用 `stage.process(ctx)`
3. 记录耗时和输出数量
4. 异常时标记 `ctx.degraded = True`，继续下一阶段

## 现有阶段

| 阶段 | 类 | 说明 |
|------|-----|------|
| recall | `RecallMerger` | 多通道并行召回+去重 |
| prerank | `PreRankStage` | LightGBM 粗排 |
| rank | `RankStage` | DCN/DIN 精排 |
| rerank | `ReRankStage` | 多样性+疲劳度+业务加权 |
| mixer | `MixerStage` | 加权轮询混排 |
