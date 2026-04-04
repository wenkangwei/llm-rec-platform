# Prompt 管理

## PromptManager

全局单例，加载和渲染 `.txt` 模板。

```python
from llm.prompt.manager import get_prompt_manager

pm = get_prompt_manager()
prompt = pm.render("executor", user_request="关闭热门通道", tools=tools_desc)
```

## 模板语法

使用 `{{variable}}` 占位符：

```
用户消息: {{user_message}}
请严格按以下 JSON 格式回复：
{"intent": "...", "confidence": 0.0-1.0}
```

## 模板列表

| 模板 | 文件 | 用途 |
|------|------|------|
| chat_assistant | `chat_assistant.txt` | 通用对话 |
| executor | `executor.txt` | ReAct Agent 执行 |
| intent_classify | `intent_classify.txt` | 意图识别（JSON 输出） |
| planner | `planner.txt` | 策略规划 |
| critic | `critic.txt` | 结果评估 |
| monitor_agent | `monitor_agent.txt` | 监控分析 |
| content_gen | `content_gen.txt` | 冷启动内容生成 |
| query_expand | `query_expand.txt` | 搜索 query 扩展 |
| rerank_summary | `rerank_summary.txt` | 搜索摘要生成 |

## 自定义模板

在 `llm/prompt/templates/` 下新建 `.txt` 文件即可，`PromptManager` 启动时自动扫描加载。
