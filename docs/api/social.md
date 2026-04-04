# 社交接口

## GET /api/social/{user_id}

获取用户社交图谱。

```bash
curl http://localhost:8000/api/social/user_001
```

**响应：**

```json
{
  "following": ["user_002", "user_003"],
  "followers": ["user_004"],
  "mutual": ["user_002"],
  "communities": ["tech_ai", "ml_enth"]
}
```

数据源：优先从 FeaturePlatform 获取，回退到 Redis `social:{user_id}`。

## POST /api/social/follow

关注用户。

```bash
curl -X POST http://localhost:8000/api/social/follow \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_001","target_user_id":"user_002"}'
```

**响应：** `{"success": true, "persisted": true}`

`persisted` 为 `true` 表示成功写入 Redis，`false` 表示内存暂存。
