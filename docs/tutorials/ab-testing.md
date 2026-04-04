# A/B 实验配置

## 创建实验

```bash
curl -X POST http://localhost:8000/api/experiments \
  -H "Content-Type: application/json" \
  -d '{
    "id": "exp_recall_weight",
    "name": "召回权重调优",
    "layer": "recall",
    "variants": [
      {"name": "control", "traffic_percent": 50.0, "config": {}},
      {"name": "test_high_personalized", "traffic_percent": 50.0,
       "config": {"personalized_weight": 0.4}}
    ]
  }'
```

## 启动实验

```bash
curl -X POST http://localhost:8000/api/experiments/exp_recall_weight/start
```

## 查看结果

```bash
curl http://localhost:8000/api/experiments/exp_recall_weight/results
```

## 分桶原理

```
bucket = md5("recall:exp_recall_weight:user_001") % 100
variant = bucket < 50 ? "control" : "test_high_personalized"
```

- 确定性：同一用户始终分配到同一变体
- 支持多层实验：不同 layer 的实验互不干扰
- 支持暂停/恢复：`POST /{id}/pause`，`POST /{id}/start`

## 在 Pipeline 中生效

`PipelineExecutor._resolve_experiment()` 在执行阶段前：

1. 遍历所有运行中实验
2. 计算用户分桶
3. 将变体 config 写入 `ctx.experiment_overrides`
4. 各 stage 读取 overrides 调整行为
