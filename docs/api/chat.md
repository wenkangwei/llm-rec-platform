# 对话接口

提供 3 种对话方式：HTTP 同步、SSE 流式、WebSocket 实时。

## POST /api/chat — HTTP 同步

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"查看系统延迟指标","user_id":"admin"}'
```

**请求：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| message | string | 是 | 用户消息 |
| user_id | string | 否 | 默认 "admin" |
| session_id | string | 否 | 传空则自动创建 |

**响应：** `{"session_id": "sess_xxx", "reply": "当前 P99 延迟 120ms..."}`

## POST /api/chat/stream — SSE 流式

```bash
curl -N http://localhost:8000/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"查看系统延迟指标"}'
```

**SSE 事件：**

```
event: session_id
data: {"session_id": "sess_xxx"}

event: chunk
data: {"content": "当前 P99..."}

event: done
data: {}
```

## WebSocket /api/ws/chat

连接 `ws://localhost:8000/api/ws/chat`，发送/接收 JSON：

```json
// 发送
{"user_id": "admin", "message": "查看延迟"}

// 接收
{"type": "session_created", "session_id": "sess_xxx"}
{"type": "reply", "content": "当前 P99 延迟 120ms..."}
```

## 意图类型

| 意图 | 说明 | 触发示例 |
|------|------|----------|
| strategy | 策略控制 | "关闭热门召回通道" |
| monitor | 监控查询 | "P99延迟多少" |
| debug | 调试诊断 | "分析推荐结果" |
| config | 配置管理 | "修改排序参数" |
| unknown | 闲聊/无关 | "你好" |

unknown 意图直接由 LLM 回答，其余通过 ReAct Agent 执行工具。
