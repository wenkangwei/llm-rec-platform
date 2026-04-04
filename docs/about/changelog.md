# 更新日志

## v0.1.0 (当前)

### 推荐流水线
- 5 级漏斗：Recall → PreRank → Rank → ReRank → Mixer
- 7 个召回通道：个性化/协同过滤/社交/社区/热门/运营/冷启动
- 3 级排序：LightGBM 粗排、DCN/DIN 精排、业务重排
- 4 个场景：首页/搜索/关注/社区

### LLM 模块
- 多厂商路由器（Ollama/vLLM/OpenAI/Triton）+ 自动降级
- ReAct Agent 框架 + 3 个运维工具
- LLM 语义意图识别（关键词兜底）
- Prompt 模板管理

### 特征平台
- 特征注册/存储/引擎/画像
- 4 种存储后端、7 个特征组

### A/B 实验
- 确定性分桶、多层实验
- CRUD API + 结果分析

### 监控
- 全链路追踪、Prometheus 指标
- 4 种 Sink、训练日志
