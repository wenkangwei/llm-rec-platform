# POST /api/track

用户行为追踪，支持点击/点赞/分享/评论/停留时长。

## 请求

```json
POST /api/track
{
  "user_id": "user_001",
  "item_id": "item_123",
  "action": "click",
  "scene": "home_feed",
  "request_id": "req_abc",
  "dwell_time_sec": 5.2
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 用户 ID |
| item_id | string | 是 | 物品 ID |
| action | string | 是 | `click` / `like` / `share` / `comment` / `dwell` / `expose` |
| scene | string | 否 | 场景标识 |
| request_id | string | 否 | 关联推荐请求 ID |
| dwell_time_sec | float | 否 | 停留时长（秒） |
| extra | dict | 否 | 扩展字段 |

## 响应

```json
{"success": true, "message": "tracked"}
```

追踪事件会异步回填训练标签（通过 `TrainingLogger.backfill_labels`）。

## 示例

```bash
curl -X POST http://localhost:8000/api/track \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u001","item_id":"i123","action":"click","scene":"home_feed"}'
```
