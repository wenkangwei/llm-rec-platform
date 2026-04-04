# POST /api/recommend

主推荐接口，支持首页/关注/社区场景。

## 请求

```json
POST /api/recommend
Content-Type: application/json

{
  "user_id": "user_001",
  "scene": "home_feed",
  "page": 0,
  "num": 20,
  "context": {}
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 用户 ID |
| scene | string | 否 | 场景：`home_feed`（默认）/ `follow_feed` / `community_feed` |
| page | int | 否 | 页码，默认 0 |
| num | int | 否 | 每页数量，默认 20，最大 100 |
| context | dict | 否 | 附加上下文特征 |

## 响应

```json
{
  "request_id": "req_abc123",
  "items": [
    {"item_id": "item_001", "score": 0.95, "source": "collaborative", "summary": null, "extra": {}}
  ],
  "trace_id": "trace_xyz",
  "total": 200,
  "page": 0,
  "has_more": true
}
```

## 示例

```bash
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_001","scene":"home_feed","num":10}'
```
