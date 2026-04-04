# 实验接口

A/B 实验管理 CRUD，路径前缀 `/api/experiments`。

## 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/experiments` | 列出实验（可选 `?status=running` 过滤） |
| POST | `/api/experiments` | 创建实验（DRAFT 状态） |
| POST | `/api/experiments/{id}/start` | 启动实验 |
| POST | `/api/experiments/{id}/stop` | 停止实验 |
| POST | `/api/experiments/{id}/pause` | 暂停实验 |
| GET | `/api/experiments/{id}/results` | 获取结果分析 |
| GET | `/api/experiments/{id}/variant?user_id=xxx` | 查询用户分桶 |

## 创建实验

```bash
curl -X POST http://localhost:8000/api/experiments \
  -H "Content-Type: application/json" \
  -d '{
    "id": "exp_rank_v2",
    "name": "排序模型V2测试",
    "layer": "ranking",
    "variants": [
      {"name": "control", "traffic_percent": 50.0, "config": {}},
      {"name": "experiment", "traffic_percent": 50.0, "config": {"rank_model": "din"}}
    ]
  }'
```

## 启动实验

```bash
curl -X POST http://localhost:8000/api/experiments/exp_rank_v2/start
```

## 查询用户分桶

```bash
curl "http://localhost:8000/api/experiments/exp_rank_v2/variant?user_id=user_001"
# → {"experiment_id": "exp_rank_v2", "variant": "experiment", "config": {"rank_model": "din"}}
```

## 实验生命周期

```
DRAFT → RUNNING → COMPLETED
         ↕
       PAUSED
```

分桶算法：`md5(layer:exp_id:user_id) % 100 < traffic_percent`，确定性哈希保证同一用户始终分配到同一变体。
