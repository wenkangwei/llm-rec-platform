# A/B 实验框架

## ExperimentManager

实验生命周期管理 + 分桶 + 指标收集。

```python
from experiment.manager import ExperimentManager

mgr = ExperimentManager()
mgr.create(exp_id="exp_1", name="排序V2", variants=[...])
mgr.start("exp_1")
variant = mgr.get_variant("exp_1", "user_001")
results = mgr.get_results("exp_1")
```

## 分桶算法

```python
bucket = md5(f"{layer}:{exp_id}:{user_id}").hexdigest()
bucket_num = int(bucket, 16) % 100
```

- 确定性：同一用户始终分到同一变体
- 多层互不干扰：不同 `layer` 的实验独立分桶

## 实验状态

```
DRAFT → RUNNING → COMPLETED
         ↕
       PAUSED
```

| 操作 | 方法 | API |
|------|------|-----|
| 创建 | `create()` | `POST /api/experiments` |
| 启动 | `start()` | `POST /{id}/start` |
| 暂停 | `pause()` | `POST /{id}/pause` |
| 停止 | `stop()` | `POST /{id}/stop` |
| 查分桶 | `get_variant()` | `GET /{id}/variant?user_id=` |
| 查结果 | `get_results()` | `GET /{id}/results` |
