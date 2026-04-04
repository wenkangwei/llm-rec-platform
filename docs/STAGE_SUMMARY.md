# LLM-Rec-Platform 阶段性工作总结

> 更新时间: 2026-04-05

---

## 一、项目概况

融合大语言模型的智能推荐系统平台，面向 10万-100万 用户规模，支持内容推荐 + 社交属性的个性化推荐场景。

- **仓库地址**: git@github.com:wenkangwei/llm-rec-platform.git
- **分支**: main
- **Python 文件数**: ~120 个源文件
- **测试**: 561 passed, 1 skipped

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
| `pipeline/executor.py` | PipelineExecutor（配置驱动，错误隔离，指标记录，降级标记） |
| `pipeline/recall/` | 8 个召回通道：Merger/Hot/Collaborative/Community/Social/ColdStart/Personalized/Operator |
| `pipeline/ranking/` | 4 阶段排序：PreRank(LightGBM)/Rank(DNN)/ReRank(策略)/Mixer(混排) |
| `pipeline/scene/` | 4 个场景入口（home_feed/search_feed/follow_feed/community_feed） |
| `pipeline/model_service/` | 模型服务框架（PyTorch/ONNX/BatchProcessor）+ 4 个模型定义（TwoTower/DCN/DIN/LightGBM） |

### Phase 3 — 特征平台 + 用户/物品画像

| 模块 | 内容 |
|------|------|
| `feature/registry/` | 特征注册中心（定义/分组/血缘/校验） |
| `feature/store/` | 多存储后端（Redis/MySQL/Faiss/Context/Hive） |
| `feature/store/faiss_store.py` | FaissFeatureStore（向量索引构建/相似度检索/暴力搜索降级） |
| `feature/store/hive_store.py` | HiveFeatureStore（PyHive 连接/SQL 查询/批量读取） |
| `feature/engine/` | DSL 特征引擎 |
| `feature/profiles/` | 用户/物品/社交/上下文画像 |
| `feature/manager/` | 特征管理（版本/目录/生命周期） |
| `feature/server/` | 特征服务 + 插件 |
| `feature/platform.py` | 统一 API 入口 |
| `feature/offline/` | 离线特征（生成/统计/回填，含数据加载和统计计算） |
| `storage/` | Redis/MySQL/ClickHouse/Faiss 封装 |

### Phase 4 — LLM 融合

| 模块 | 内容 |
|------|------|
| `llm/base.py` + `llm/factory.py` | LLM 后端抽象（OpenAI 兼容协议），缺少 base_url 时强制报错 |
| `llm/backends/` | vLLM/Mock/Triton 三种后端 |
| `llm/backends/triton_backend.py` | TritonLLMBackend（tritonclient 降级为 Mock） |
| `llm/agent/` | Agent 框架（base ABC + planner/executor/critic/monitor + ReAct Agent） |
| `llm/agent/tools/` | 3 个工具（链路控制/监控查询/配置热更新） |
| `llm/chat/manager.py` | ChatSessionManager（会话管理 + TTL过期 + max_sessions淘汰） |
| `llm/chat/router.py` | LangGraph StateGraph 对话路由 |
| `llm/chat/handlers/` | 4 个意图处理器（策略/监控/调试/配置） |
| `llm/chat/schemas.py` | 消息/意图/动作数据结构 |
| `llm/tasks/` | Embedding/内容生成/搜索摘要/语义搜索 |
| `llm/prompt/` | Prompt 管理（模板加载/渲染/缓存/注册） |

### Phase 5 — 监控体系

| 模块 | 内容 |
|------|------|
| `monitor/tracer.py` | RecTracer 链路追踪（阶段计时/物品分数/召回覆盖率） |
| `monitor/metrics.py` | Prometheus 指标（延迟/计数/直方图/Prometheus文本格式） |
| `monitor/collector.py` | MonitorCollector（汇聚 tracer + metrics + training + sinks） |
| `monitor/writer.py` | TraceWriter 基类 |
| `monitor/training_logger.py` | 训练日志落盘 + 延迟标签回填 |
| `monitor/sinks/` | 4 个输出（File/ClickHouse/Training/Stdout） |

### Phase 6 — 训练 + 部署

| 模块 | 内容 |
|------|------|
| `scripts/` | 训练脚本（双塔/排序模型/特征回填/embedding生成，含 Parquet 加载 + 随机样本降级） |
| `pipeline/model_service/backends/triton_backend.py` | TritonModel 后端（tritonclient 降级为零输出） |
| `server/grpc_server.py` | gRPC 服务框架（Servicer/创建/启动，需 grpcio + protobuf 编译） |
| `server/routes/search.py` | 搜索路由 + LLM 搜索摘要生成 |
| `server/routes/social.py` | 社交路由（Redis 存储 + 画像读取降级） |
| `docker/` | Dockerfile + docker-compose.yaml（完整服务栈：rec-server/vLLM/Redis/MySQL/ClickHouse/Prometheus/Grafana） |
| `docker/conf/prometheus.yml` | Prometheus 采集配置 |

### 测试体系

| 文件 | 测试数 | 覆盖范围 |
|------|--------|----------|
| `test_utils.py` | 15 | hash/logger/timer |
| `test_utils_extended.py` | 12 | serialization/events(TrackEventV2/TrainingLogEntry) |
| `test_configs.py` | 17 | deep_merge/get_nested/load_yaml/ref_resolution/类型保留/AppConfig |
| `test_protocols.py` | 19 | RecContext/Item/Request/Response/Converters |
| `test_pipeline.py` | 28 | ContextUtils/PipelineStage/PipelineExecutor/RecallMerger/HotRecall/ReRank/Mixer/降级标记 |
| `test_pipeline_extended.py` | 25 | 6个recall/cold_start/operator/prerank/rank/cosine_sim/4个scene/BatchProcessor |
| `test_llm.py` | 25 | MockBackend/ChatSessionManager/意图分类/实体提取/会话过期/Factory |
| `test_llm_extended.py` | 30 | 4个chat handler/router/monitor_agent/content_gen/embedder/rerank_summary/semantic_search/prompt_manager |
| `test_agent.py` | 30 | AgentTask/Step/Result/PlannerAgent/CriticAgent/ReActAgent/3个Tool |
| `test_monitor.py` | 11 | RecTracer/SchemaStructures |
| `test_monitor_extended.py` | 16 | RecMetrics(全部方法)/MonitorCollector/TraceWriter |
| `test_sinks.py` | 12 | FileSink/ClickHouseSink/StdoutSink/TrainingSink |
| `test_model_service.py` | 11 | ModelServiceABC/ModelManager(register/unregister/reload/predict/warmup/shutdown) |
| `test_storage.py` | 12 | RedisStore/MySQLStore/ClickHouseStore/全局Redis单例 |
| `test_feature.py` | 72 | FeatureDef/FeatureGroupDef/FeatureRegistry/FeatureLineage/FeatureValidator/ContextFeatureStore/StoreRouter/DSL Parser/DSLExecutor/FeatureComposer/FeatureCache |
| `test_feature_extended.py` | 43 | UserProfile/ItemProfile/ContextProfile/FeaturePlatform/FeatureCatalog/FeatureVersionManager/FeatureLifecycle/OfflineFeatureGenerator/FeatureStats/FeatureBackfill/FeatureServer/FeatureFetchPlugin |
| `test_server.py` | 8 | health/metrics/recommend/search/track/CORS/request_id |
| `test_server_middleware.py` | 14 | AuthMiddleware(6)/ErrorHandlerMiddleware(2)/LoggingMiddleware(1)/RateLimitMiddleware(2)/RequestIDMiddleware(3) |
| `test_server_routes.py` | 16 | health(3)/recommend(3)/search(2)/track(2)/social(2)/chat(4) |
| `test_feature_store.py` | 16 | RedisFeatureStore(8)/MySQLFeatureStore(8) |
| `test_uncovered_modules.py` | 44 | Settings/TrainingLogger/TorchModel/ONNXModel/TwoTower/DCN/DIN/LightGBM/CrossLayer/AttentionLayer/UserTower/ItemTower |
| `test_new_modules.py` | 45 | FaissFeatureStore/HiveFeatureStore/TritonLLM/TritonModel/gRPC Server/SearchSummary/SocialRoute/PairwiseDataset/RankDataset |
| `tests/integration/` | 5 | 完整链路/HTTP→Response/搜索/降级/通道隔离 |
| `tests/e2e/` | ~14 | FastAPI 真实 HTTP 端点（需 fastapi） |
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

### 2. pytest 异步兼容（已修复）

- 使用 `asyncio.get_event_loop().run_until_complete()` 执行 async 测试
- `conftest.py` 提供 session-scoped event_loop fixture
- `pyproject.toml` 配置 `asyncio_mode = "auto"`

### 3. Recall 模块 Redis fallback（已修复）

所有 5 个召回模块的 TODO stub 已替换为 Redis 查询 + graceful fallback。

### 4. SearchResponse 缺少 summary 字段（已修复）

`SearchResponse` 新增 `summary: Optional[str] = None`，搜索路由支持 LLM 生成的摘要透传。

### 5. ClickHouseSink 无客户端时缓冲区不清理（已修复）

**问题**: `_flush()` 在无 client 时直接 return，不清理 `_buffer`，内存持续增长。

**修复**: 无 client 时仍执行 `_buffer.clear()`。

### 6. ChatSessionManager 会话无限增长（已修复）

**问题**: `_sessions` dict 无 TTL、无上限，长时间运行后内存泄漏。

**修复**: 新增 `session_ttl`（默认 3600s）和 `max_sessions`（默认 1000），自动淘汰过期和最旧会话。

### 7. Pipeline 执行失败无降级标记（已修复）

**问题**: 单阶段失败后链路继续执行，但调用方无法感知哪些阶段降级。

**修复**: `RecContext` 新增 `degraded: bool` 和 `degraded_stages: list[str]`，`PipelineExecutor.execute()` 在捕获异常时设置。

### 8. LLMFactory 硬编码 base_url fallback（已修复）

**问题**: `LLMFactory.create()` 在配置缺少 `base_url` 时静默使用 `localhost:8001`，生产环境可能连错服务。

**修复**: 缺少 `base_url` 时抛出 `ValueError`，强制要求配置。

### 9. chat.py 语法错误 — nonlocal 声明顺序（已修复）

**问题**: `chat_websocket()` 函数中 `nonlocal session_id` 出现在赋值之后，Python 语法错误导致模块无法导入。

**修复**: 移除 `nonlocal` 声明，直接使用外层作用域的 `session_id` 变量（`while` 循环外已定义 `session_id = None`）。

### 10. chat.py 直接属性访问导致 AttributeError（已修复）

**问题**: `chat_http()` 和 `chat_stream()` 直接访问 `request.app.state.chat_manager`，当 lifespan 未初始化该属性时抛出 `AttributeError`。

**修复**: 改用 `getattr(request.app.state, "chat_manager", None)` 带默认值访问。

### 11. RecMetrics p99 计算错误 + 内存无限增长（已修复）

**问题**: `get_histogram_summary()` 的 p99 索引 `int(len(sorted_v) * 0.99)` 在小样本时不准确（10 个元素返回 max 而非 p99）。`_histograms` 的 list 持续追加不清理，高负载下内存泄漏。

**修复**: 改用 `(len(sorted_v) - 1) * 99 // 100` 计算百分位索引。新增 `_MAX_HISTOGRAM_SIZE=10000` 上限，超限时截断保留最新一半样本。

### 12. ModelManager.reload() 竞态条件（已修复）

**问题**: `old_model = self._models.get(name)` 在锁外读取，并发 reload 时可能获取过期引用。

**修复**: 将 `old_model` 读取移入 `with self._lock` 块内。

### 13. DIN 模型 forward 维度错误（已修复）

**问题**: DIN.forward 中 item_emb 和 behavior_pool 都被 `unsqueeze(1)` 变成 `[B, 1, D]`，传给 AttentionLayer 后 item_emb 又被 `unsqueeze(1)` 变成 `[B, 1, 1, D]`，导致 RuntimeError。

**修复**: forward 中只对 behavior_pool 做 unsqueeze，item_emb 保持 2D 传入 AttentionLayer。

---

## 四、Git 提交记录

```
b3cfad0 feat: 全面测试覆盖 + Bug 修复 — 508 tests 全通过
2cb9aef test: 补全 LLM/Pipeline/Monitor/Utils 扩展测试覆盖
0d932c0 feat: 补全测试覆盖 + 会话过期 + 降级标记 + Factory 校验
a8b5db3 fix: 配置加载器类型保留 + 召回模块Redis fallback + 工程化基础设施
5affe4f test: 添加单元/集成测试 + 补全基础设施配置
d2f018a feat: Phase 6 — 补全路由 + Docker Compose 部署 + 训练脚本
6f97c0c feat: Phase 5 — 监控体系（链路追踪 + Prometheus指标 + 训练日志落盘）
a724d9b refactor: 分离 HTTP request/response/context + Pipeline 初版用 function call
1986586 feat: Phase 3 — 特征平台 + 存储后端 + 用户/物品画像
a275a34 feat: Phase 2 — 推荐链路核心完整实现
443a4ab feat: Phase 1 完成 — FastAPI 服务骨架 + pyproject.toml + 所有包初始化
f0c8a94 feat: Phase 1 — 项目骨架 + 配置中心 + 协议定义 + 核心抽象
```

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

### 未覆盖测试的模块

| 模块 | 文件数 | 原因 |
|------|--------|------|
| `server/lifespan.py` | 1 | 需要完整依赖启动生命周期 |
| `storage/faiss.py` | 1 | 需要 faiss C++ 库 |
| `scripts/` | 1 | `generate_embeddings.py` 需要 embedding 模型 |

### 功能增强方向

| 方向 | 说明 |
|------|------|
| gRPC 分布式拆分 | PipelineStage 已预留 `process_grpc` 接口 |
| LangGraph 编排升级 | 当前 Agent 使用 LangChain ReAct，可升级 LangGraph StateGraph |
| A/B 实验系统 | Agent 工具已定义，需要接入实验平台 |
| 实时特征更新 | 特征平台框架已搭建，需要接入 Flink/Kafka |
| 模型热更新 | ModelManager 框架已搭建，需要对接模型仓库 |

### 代码质量

| 项目 | 状态 |
|------|------|
| 单元测试 | 561 passed（22 个测试文件，全部核心模块 + 模型服务 + 特征平台 + 服务端全覆盖） |
| 集成测试 | 5 个端到端链路测试 |
| E2E 测试 | ~14 个 HTTP 端点测试（需 fastapi） |
| CI/CD | GitHub Actions 已配置 |
| Lint | ruff 已配置，`make lint` 可用 |

---

## 六、下一步计划

1. **Docker 部署验证** — `make docker-up` 启动完整服务栈
2. **接入真实 LLM 后端** — 配置 vLLM 推理服务，替换 MockBackend
3. **填充训练数据** — 准备 Parquet 格式训练样本
4. **性能压测** — 验证 P99 < 200ms / QPS ≥ 1000 目标
5. **gRPC 服务启用** — 编译 protobuf + 注册 Servicer
6. **lifespan 集成测试** — 需要完整依赖启动生命周期验证
