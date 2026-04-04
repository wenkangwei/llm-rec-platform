# 对话系统

## ChatSessionManager

管理会话 + 意图识别 + Agent 调度。

```python
from llm.chat.manager import ChatSessionManager

mgr = ChatSessionManager(llm=llm_backend, pipeline_state={})
session = mgr.create_session(user_id="admin")
reply = await mgr.chat(session.session_id, "查看P99延迟")
```

## 意图识别

**LLM 语义识别**（主路径）：使用 `intent_classify.txt` 模板，LLM 返回 JSON：

```json
{"intent": "monitor", "confidence": 0.95, "reason": "查询延迟指标"}
```

**关键词匹配**（降级）：LLM 失败时使用关键词字典兜底。

| 意图 | 路由 |
|------|------|
| strategy/monitor/debug/config | → ReAct Agent（工具执行） |
| unknown | → LLM 直接回答 |

## 会话管理

- TTL 3600 秒自动过期
- 最大 1000 并发会话，超出淘汰最旧
- 支持多轮对话（消息历史）
