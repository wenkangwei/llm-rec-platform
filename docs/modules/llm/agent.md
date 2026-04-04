# Agent 框架

基于 ReAct（Reasoning + Acting）模式的智能运维 Agent。

## 核心类

| 类 | 说明 |
|-----|------|
| `Agent` (ABC) | 基类，`run(task) -> AgentResult` |
| `Tool` (ABC) | 工具基类，`execute(params) -> Any` |
| `ReActAgent` | ReAct 循环实现 |
| `PlannerAgent` | 策略分析 |
| `CriticAgent` | 结果评估 |

## ReAct 循环

```
Thought: 分析用户需求
  → Action: tool_name
  → Action Input: {"key": "value"}
  → Observation: 工具返回结果
  → Thought: 继续分析或得到答案
  → Answer: 最终回复
```

`max_iterations=5`，超出后从最后一个成功的工具结果构造回复。

## 工具

| 工具 | 类 | 功能 |
|------|-----|------|
| pipeline_control | `PipelineControlTool` | 启用/关闭通道、调权重 |
| monitor_query | `MonitorQueryTool` | 查询延迟/QPS/覆盖率（支持中英文指标名） |
| config_update | `ConfigUpdateTool` | 热更新运行时配置 |

## 使用

```python
from llm.agent.executor import ReActAgent

agent = ReActAgent(llm_backend, tools=[PipelineControlTool(), ...])
result = await agent.run(AgentTask(task_id="t1", description="关闭热门通道"))
print(result.answer)   # 最终回复
print(result.steps)     # 执行步骤列表
```
