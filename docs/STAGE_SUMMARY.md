# LLM-Rec-Platform 阶段性工作总结

> 更新时间: 2026-04-03

---

## 一、项目概况

融合大语言模型的智能推荐系统平台，面向 10万-100万 用户规模，支持内容推荐 + 社交属性的个性化推荐场景。

- **仓库地址**: git@github.com:wenkangwei/llm-rec-platform.git
- **分支**: main
- **Python 文件数**: 187
- **测试**: 115 passed, 2 skipped (需 fastapi)

---

## 二、已完成工作

### Phase 1 — 项目骨架 + 配置中心 + 协议定义

| 模块 | 内容 |
|------|------|
| `utils/` | 日志(structlog)、计时上下文、一致性哈希、序列化 |
| `configs/` | YAML 图依赖加载 + `${path:key}` 引用解析 + 拓扑排序 + 环境覆盖 |
| `configs/settings.py` | Pydantic Settings 全局单例 |
| `configs/schema.py` | AppConfig Schema 校验（server/storage/models/pipeline/features/llm/monitor） |
| `protocols/schemas/` | RecContext + Item + StageMetrics（内部）<br>RecRequest/SearchRequest/TrackEvent（HTTP 入参）<br>RecResponse/SearchResponse/HealthResponse（HTTP 出参）<br>converters 实现双向转换 |
| `pipeline/base.py` | PipelineStage ABC（invoke/ainvoke/process_grpc） |
| `pipeline/context.py` | RecContext 工具函数（create_context/dedup_items/sort_by_score 等） |
| `server/` | FastAPI 应用工厂 + 5 个中间件 + 6 个路由模块 + 生命周期管理 |
| `pyproject.toml` | 完整依赖管理 |

### Phase 2 — 推荐链路核心

| 模块 | 内容 |
|------|------|
| `pipeline/executor.py` | PipelineExecutor（配置驱动，错误隔离，指标记录） |
| `pipeline/recall/merger.py` | RecallMerger（多路并行召回 + 去重 + 通道隔离） |
| `pipeline/recall/hot.py` | 热门召回（Redis + 内存缓存 fallback） |
| `pipeline/recall/collaborative.py` | 协同过滤召回（Redis 相似度矩阵 fallback） |
| `pipeline/recall/community.py` | 社区召回（Redis 社区热门 fallback） |
| `pipeline/recall/social.py` | 社交召回（Redis 关注关系 fallback） |
| `pipeline/recall/cold_start.py` | 冷启动召回（新用户探索 + 新内容扶持） |
| `pipeline/recall/personalized.py` | 双塔向量召回 |
| `pipeline/recall/operator.py` | 运营召回 |
| `pipeline/ranking/prerank.py` | 粗排（LightGBM） |
| `pipeline/ranking/rank.py` | 精排（DNN） |
| `pipeline/ranking/rerank.py` | 策略重排（MMR 多样性 + Fatigue 控制 + Author/Tag 限制） |
| `pipeline/ranking/mixer.py` | 混排（weighted_round_robin 按内容类型混合） |
| `pipeline/scene/` | 4 个场景入口（home_feed/search_feed/follow_feed/community_feed） |
| `pipeline/model_service/` | 模型服务框架（PyTorch/ONNX/BatchProcessor）+ 4 个模型定义 |

### Phase 3 — 特征平台 + 用户/物品画像

| 模块 | 内容 |
|------|------|
| `feature/registry/` | 特征注册中心（定义/分组/血缘/校验） |
| `feature/store/` | 多存储后端（Redis/MySQL/Faiss/Context/Hive） |
| `feature/engine/` | DSL 特征引擎 |
| `feature/profiles/` | 用户/物品/社交/上下文画像 |
| `feature/manager/` | 特征管理（版本/目录/生命周期） |
| `feature/server/` | 特征服务 + 插件 |
| `feature/platform.py` | 统一 API 入口 |
| `feature/offline/` | 离线特征（生成/统计/回填，需数据仓库环境） |
| `storage/` | Redis/MySQL/ClickHouse/Faiss 封装 |

### Phase 4 — LLM 融合

| 模块 | 内容 |
|------|------|
| `llm/base.py` + `llm/factory.py` | LLM 后端抽象（OpenAI 兼容协议） |
| `llm/backends/` | vLLM/OpenAI/Mock 三种后端 |
| `llm/agent/` | Agent 框架（base ABC + planner/executor/critic + ReAct Agent） |
| `llm/agent/tools/` | 5 个工具（链路控制/监控查询/配置热更新/A/B实验/模型管理） |
| `llm/chat/manager.py` | ChatSessionManager（会话管理 + 上下文记忆） |
| `llm/chat/router.py` | LangGraph StateGraph 对话路由 |
| `llm/chat/handlers/` | 4 个意图处理器（策略/监控/调试/配置） |
| `llm/chat/schemas.py` | 消息/意图/动作数据结构 |
| `llm/tasks/` | Embedding/内容生成/搜索摘要/语义搜索 |
| `llm/prompt/` | Prompt 管理 |

### Phase 5 — 监控体系

| 模块 | 内容 |
|------|------|
| `monitor/tracer.py` | RecTracer 链路追踪（阶段计时/物品分数/召回覆盖率） |
| `monitor/metrics.py` | Prometheus 指标（延迟/计数/直方图） |
| `monitor/training_logger.py` | 训练日志落盘 + 延迟标签回填 |
| `monitor/sinks/` | 4 个输出（File/ClickHouse/Training/Stdout） |

### Phase 6 — 训练 + 部署

| 模块 | 内容 |
|------|------|
| `scripts/` | 训练脚本（双塔/排序模型/特征回填） |
| `docker/` | Dockerfile + docker-compose.yaml（完整服务栈：rec-server/vLLM/Redis/MySQL/ClickHouse/Prometheus/Grafana） |
| `docker/conf/prometheus.yml` | Prometheus 采集配置 |

### 测试体系

| 文件 | 测试数 | 覆盖范围 |
|------|--------|----------|
| `tests/unit/test_utils.py` | 13 | hash/logger/timer |
| `tests/unit/test_configs.py` | 17 | deep_merge/get_nested/load_yaml/ref_resolution/类型保留/AppConfig |
| `tests/unit/test_protocols.py` | 17 | RecContext/Item/Request/Response/Converters |
| `tests/unit/test_pipeline.py` | 21 | ContextUtils/PipelineStage/PipelineExecutor/RecallMerger/HotRecall/ReRank/Mixer |
| `tests/unit/test_llm.py` | 16 | MockBackend/ChatSessionManager/意图分类/实体提取 |
| `tests/unit/test_monitor.py` | 12 | RecTracer/SchemaStructures |
| `tests/unit/test_server.py` | ~10 | health/metrics/recommend/search/track/middleware（需 fastapi） |
| `tests/integration/test_integration.py` | 5 | 完整链路/HTTP→Response/搜索/降级/通道隔离 |
| `tests/e2e/test_e2e.py` | 18 | FastAPI 真实 HTTP 端点（需 fastapi） |
| `tests/conftest.py` | — | 共享 fixtures |

### 工程化基础设施

| 文件 | 内容 |
|------|------|
| `.github/workflows/ci.yml` | CI: lint → test → docker build |
| `Makefile` | install/test/lint/run/docker-build/docker-up/clean |
| `.env.example` | 环境变量模板 |
| `.env` | 开发环境配置 |
| `.gitignore` | 完整忽略规则 |
| `README.md` | 项目文档（架构/技术栈/Quick Start/性能目标） |

---

## 三、修复的关键问题

### 1. 配置引用类型丢失（已修复）

**问题**: `ConfigLoader._resolve_path_ref()` 将所有引用值 `str()` 化，导致 YAML 引用的 dict/list 变成字符串表示，`AppConfig` Pydantic 校验失败。

**修复**: `_resolve_refs()` 中检测整个字符串是否恰好是一个引用（`fullmatch`），如果是则保留原始类型（dict/list/int），递归解析内部引用。

**测试**: `test_resolve_refs_preserves_dict_type` 验证 dict 类型保留。

### 2. pytest 异步兼容（已修复）

- 使用 `asyncio.get_event_loop().run_until_complete()` 执行 async 测试
- `conftest.py` 提供 session-scoped event_loop fixture
- `pyproject.toml` 配置 `asyncio_mode = "auto"`

### 3. Recall 模块 Redis fallback（已修复）

所有 5 个召回模块的 TODO stub 已替换为 Redis 查询 + graceful fallback：
- 尝试 `from storage.redis import get_redis` 获取连接
- Redis 不可用时返回空列表（不抛异常）
- `storage/redis.py` 新增 `get_redis()`/`set_redis()` 全局单例

### 4. SearchResponse 缺少 summary 字段（已修复）

`SearchResponse` 新增 `summary: Optional[str] = None`，搜索路由支持 LLM 生成的摘要透传。

---

## 四、Git 提交记录

```
5affe4f test: 添加单元/集成测试 + 补全基础设施配置
d2f018a feat: Phase 6 — 补全路由 + Docker Compose 部署 + 训练脚本
6f97c0c feat: Phase 5 — 监控体系（链路追踪 + Prometheus指标 + 训练日志落盘）
a724d9b refactor: 分离 HTTP request/response/context + Pipeline 初版用 function call
1986586 feat: Phase 3 — 特征平台 + 存储后端 + 用户/物品画像
a275a34 feat: Phase 2 — 推荐链路核心完整实现
443a4ab feat: Phase 1 完成 — FastAPI 服务骨架 + pyproject.toml + 所有包初始化
f0c8a94 feat: Phase 1 — 项目骨架 + 配置中心 + 协议定义 + 核心抽象
```

**待提交**: 配置加载器类型保留修复 + 召回模块 Redis fallback + README 更新 + CI/CD + Makefile + E2E 测试 + conftest.py

---

## 五、已知问题 & 待改进

### 需要环境依赖的模块

| 问题 | 状态 |
|------|------|
| E2E 测试需要 `pip install fastapi` | 代码已写好，安装依赖即可运行 |
| Docker 镜像需要完整依赖构建 | Dockerfile 已配置，需 `docker build` |
| 离线特征模块需要数据仓库（Hive） | 接口已定义，实现需要实际数据环境 |
| 训练脚本需要 Parquet 训练数据 | 框架已搭建，需要数据文件 |
| 模型推理需要 PyTorch/ONNX 模型文件 | 接口已定义，需要训练产出模型 |

### 功能增强方向

| 方向 | 说明 |
|------|------|
| gRPC 分布式拆分 | PipelineStage 已预留 `process_grpc` 接口，可按需启用 |
| LangGraph 编排升级 | 当前 Agent 使用 LangChain ReAct，可升级 LangGraph StateGraph |
| A/B 实验系统 | Agent 工具已定义，需要接入实验平台 |
| 实时特征更新 | 特征平台框架已搭建，需要接入 Flink/Kafka |
| 模型热更新 | ModelManager 框架已搭建，需要对接模型仓库 |

### 代码质量

| 项目 | 状态 |
|------|------|
| 单元测试覆盖 | 核心模块已覆盖（utils/configs/protocols/pipeline/llm/monitor） |
| 集成测试 | 5 个端到端链路测试 |
| E2E 测试 | 18 个 HTTP 端点测试（需 fastapi） |
| CI/CD | GitHub Actions 已配置 |
| Lint | ruff 已配置，`make lint` 可用 |

---

## 六、下一步计划

1. **安装完整依赖** — `pip install -e ".[dev]"` 解锁 E2E 测试和应用启动
2. **Docker 部署验证** — `make docker-up` 启动完整服务栈
3. **接入真实 LLM 后端** — 配置 vLLM 推理服务，替换 MockBackend
4. **填充训练数据** — 准备 Parquet 格式训练样本
5. **性能压测** — 验证 P99 < 200ms / QPS ≥ 1000 目标
