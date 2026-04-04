# POST /api/search

搜索推荐接口，附带 LLM 生成摘要。

## 请求

```json
POST /api/search
{
  "user_id": "user_001",
  "query": "人工智能最新进展",
  "page": 0,
  "num": 20
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | 是 | 用户 ID |
| query | string | 是 | 搜索词，1-200 字符 |
| page | int | 否 | 页码，默认 0 |
| num | int | 否 | 每页数量，默认 20，最大 100 |

## 响应

```json
{
  "request_id": "req_abc123",
  "query": "人工智能最新进展",
  "items": [
    {"item_id": "item_001", "score": 0.92, "source": "personalized", "summary": null, "extra": {}}
  ],
  "trace_id": "trace_xyz",
  "total": 15,
  "summary": "为您找到了关于人工智能大模型和多模态技术的最新内容。"
}
```

`summary` 由 LLM 根据前 5 条结果自动生成（max_tokens=128, temperature=0.3）。

## 示例

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"user_id":"user_001","query":"人工智能最新进展"}'
```
