# LLM-Rec-Platform

**融合大语言模型的智能推荐系统平台** — 面向 10万-100万 用户规模，支持内容推荐 + 社交属性的个性化推荐场景。

---

## Highlights

- **LLM-native 推荐架构** — 将大语言模型深度融入推荐链路：语义 Embedding 生成、新内容冷启动模拟、搜索结果个性化摘要，超越传统 TF-IDF / Word2Vec 的表征能力
- **对话式链路控制** — 通过自然语言对话实时控制推荐策略，支持「关闭热门召回」「把协同过滤权重调到 0.3」「分析用户 123 推荐为什么偏少」等指令
- **完整四阶段推荐漏斗** — 多路召回 → 粗排 → 精排 → 策略重排 → 混排，每层独立可插拔、可降级
- **配置图驱动的特征平台** — 统一特征注册中心 + DSL 引擎 + 特征血缘追踪，线上线下特征一致性保障
- **全链路追踪 + 训练日志闭环** — 每个请求完整的 PipelineTrace，追踪候选物品在各阶段的分数和位置变化，异步落盘 + 延迟标签回填
- **渐进式 Agent 框架** — LangChain 原型 → LangGraph 编排 → DeepAgent 深度推理，按需升级复杂度
- **面向生产的工程实践** — 模型热更新、A/B 实验、多级缓存、熔断降级、Protobuf 协议预留分布式拆分

---

## Architecture

```
用户请求 → RecContext 构建
  → 特征拉取（FeaturePlatform）
  → 推荐链路执行
      ├─ 多路召回（个性化/协同过滤/社交/社区/热门/运营/冷启动）
      ├─ 粗排（LightGBM）
      ├─ 精排（DCN-v2 / DIN / DeepFM）
      ├─ 策略重排（多样性/去重/Fatigue 控制）
      └─ 混排（多类型内容混合输出）
  → 日志追踪（RecTracer）
  → 响应返回 + 异步日志落盘

离线流程：日志采集 → 数据仓库 → 特征工程 → 模型训练 → 模型仓库 → 推送到线上
LLM Agent：自然语言对话 → 意图识别 → 工具调用 → 策略控制/监控查询/调试诊断
```

---

## Tech Stack

| 类别 | 技术 |
|------|------|
| 后端框架 | Python FastAPI + Uvicorn |
| LLM 推理 | vLLM（OpenAI 兼容协议） |
| LLM Agent | LangChain + LangGraph + DeepAgent |
| 深度学习 | PyTorch |
| 树模型 | LightGBM |
| 向量检索 | Faiss |
| 缓存 | Redis |
| OLAP | ClickHouse |
| 关系数据库 | MySQL |
| 监控 | Grafana + Prometheus |
| 日志收集 | Vector |
| 容器化 | Docker Compose |
| 协议 | Protobuf（预留 gRPC）+ Pydantic HTTP |

---

## Project Structure

```
llm-rec-platform/
├── configs/              # 配置中心（图依赖 + 拓扑排序 + 环境覆盖）
├── protocols/            # 协议定义（Protobuf + Pydantic Schema）
├── server/               # FastAPI 服务（中间件 + 路由 + WebSocket Chat）
├── pipeline/             # 推荐链路核心（召回/排序/场景）
├── llm/                  # LLM 融合（后端/Agent/对话界面/任务/Prompt）
├── feature/              # 特征平台（注册/存储/DSL引擎/画像）
├── monitor/              # 监控体系（链路追踪/指标/训练日志落盘）
├── storage/              # 存储后端封装（Redis/MySQL/ClickHouse/Faiss）
├── scripts/              # 训练/离线脚本
├── utils/                # 工具类（日志/计时/哈希/序列化）
├── docker/               # Docker Compose 编排
└── tests/                # 单元/集成/E2E 测试
```

---

## Roadmap

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 项目骨架 + 配置中心 + 协议定义 | ✅ Done |
| Phase 2 | 推荐链路（召回 → 排序 → 混排） | 🚧 In Progress |
| Phase 3 | 特征平台 + 用户/物品画像 | 📋 Planned |
| Phase 4 | LLM 融合（Embedding / 内容生成 / 对话式 Agent） | 📋 Planned |
| Phase 5 | 监控体系 + 链路追踪 + 日志落盘 | 📋 Planned |
| Phase 6 | 模型训练闭环 + A/B 测试 + 部署 | 📋 Planned |

---

## Quick Start

```bash
# 1. 安装依赖
pip install -e .

# 2. 启动服务（开发模式）
APP_ENV=development python -m uvicorn server.app:create_app --factory --reload --port 8000

# 3. 健康检查
curl http://localhost:8000/api/health

# 4. 推荐请求
curl -X POST http://localhost:8000/api/recommend \
  -H "Content-Type: application/json" \
  -d '{"user_id": "u123", "scene": "home_feed", "num": 10}'
```

---

## Performance Targets

| 指标 | 目标值 |
|------|--------|
| 推荐延迟 (P99) | < 200ms |
| 并发 QPS | ≥ 1000 |
| 召回覆盖率 | ≥ 85% |
| 服务可用性 | ≥ 99.9% |
| 日志落盘完整性 | ≥ 99.9% |

---

## License

MIT
