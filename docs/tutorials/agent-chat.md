# 智能对话运维

通过自然语言控制推荐系统，由 LLM Agent 执行工具调用。

## 使用方式

```bash
# 创建会话并提问
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"关闭热门召回通道","user_id":"admin"}'
```

## 工作原理

```
用户消息 → LLM 意图识别 → 意图路由 → ReAct Agent → 工具执行 → 结果回复
```

**意图识别**：LLM 语义分类（`intent_classify.txt` 模板），失败降级到关键词匹配。

## 可用工具

| 工具 | 说明 | 示例指令 |
|------|------|----------|
| `pipeline_control` | 启用/关闭通道、调权重 | "关闭热门召回通道" |
| `monitor_query` | 查询延迟/QPS/覆盖率 | "P99延迟多少" |
| `config_update` | 热更新运行时配置 | "修改排序模型版本为v2" |

## 工具调用示例

**查看指标：**

```bash
curl -X POST http://localhost:8000/api/chat \
  -d '{"message":"查看系统QPS和延迟"}'
# → "当前 QPS: 600, P99 延迟: 120ms"
```

**控制通道：**

```bash
curl -X POST http://localhost:8000/api/chat \
  -d '{"message":"将协同过滤通道权重调到0.3"}'
# → "已将 collaborative 通道权重设为 0.3"
```

## SSE 流式对话

```bash
curl -N http://localhost:8000/api/chat/stream \
  -d '{"message":"查看监控指标"}'
```

## WebSocket

```javascript
const ws = new WebSocket("ws://localhost:8000/api/ws/chat");
ws.send(JSON.stringify({user_id: "admin", message: "系统状态"}));
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```
