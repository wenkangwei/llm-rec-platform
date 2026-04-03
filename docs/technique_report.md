# LLM 推荐系统平台 — 技术方案

## 1. 项目结构

```
llm-rec-platform/
├── configs/                           # 配置中心（图依赖）
│   ├── app.yaml                       # ★ 主配置入口（根节点）
│   ├── loader.py                      # 配置加载器（图解析 + 拓扑排序）
│   ├── settings.py                    # Settings 单例（Pydantic）
│   ├── schema.py                      # 配置 schema 校验
│   ├── server/server.yaml             # 服务器配置
│   ├── storage/storage.yaml           # 存储配置
│   ├── feature/features.yaml          # 特征平台注册表
│   ├── model/models.yaml              # 模型定义
│   ├── pipeline/
│   │   ├── pipeline.yaml              # 链路编排
│   │   ├── recall.yaml                # 召回通道配置 + 权重
│   │   └── ranking.yaml               # 粗排/精排/重排/混排配置
│   ├── llm/llm.yaml                   # LLM 配置
│   ├── monitor/monitor.yaml           # 监控配置
│   └── environments/
│       ├── development.yaml
│       ├── staging.yaml
│       └── production.yaml
├── protocols/                         # 协议定义
│   ├── proto/                         # Protobuf 定义
│   │   ├── common.proto
│   │   ├── recommendation.proto
│   │   ├── model_service.proto
│   │   ├── llm_service.proto
│   │   ├── feature_service.proto
│   │   └── social_service.proto
│   ├── schemas/                       # Pydantic Schema
│   │   ├── context.py
│   │   ├── request.py
│   │   ├── response.py
│   │   └── events.py
│   └── generated/                     # 代码生成输出
│       ├── python/
│       └── go/
├── server/                            # 服务器核心
│   ├── app.py                         # FastAPI 应用
│   ├── lifespan.py                    # 生命周期管理
│   ├── middleware/                    # 中间件
│   │   ├── auth.py
│   │   ├── rate_limit.py
│   │   ├── request_id.py
│   │   ├── logging.py
│   │   └── error_handler.py
│   ├── routes/                        # 路由
│   │   ├── recommend.py
│   │   ├── search.py
│   │   ├── track.py
│   │   ├── social.py
│   │   └── health.py
│   └── grpc_server.py                 # gRPC 服务（预留）
├── pipeline/                          # 推荐链路核心
│   ├── base.py                        # PipelineStage ABC
│   ├── context.py                     # RecContext + Item + StageMetrics
│   ├── executor.py                    # 链路执行器（配置驱动）
│   ├── model_service/                 # 模型服务模块
│   │   ├── base.py                    # ModelService ABC
│   │   ├── manager.py                 # ModelManager（生命周期/热更新）
│   │   ├── backends/                  # 推理后端
│   │   │   ├── torch_backend.py
│   │   │   ├── onnx_backend.py
│   │   │   ├── triton_backend.py
│   │   │   └── batch_processor.py
│   │   └── models/                    # 模型实现
│   │       ├── two_tower.py
│   │       ├── dcn.py
│   │       ├── din.py
│   │       └── lightgbm_model.py
│   ├── recall/                        # 召回模块
│   │   ├── merger.py
│   │   ├── personalized.py            # 双塔个性化召回
│   │   ├── collaborative.py           # 协同过滤召回
│   │   ├── social.py                  # 社交召回
│   │   ├── community.py               # 社区召回
│   │   ├── hot.py                     # 热门召回
│   │   ├── operator.py                # 运营召回
│   │   └── cold_start.py             # 冷启动召回
│   ├── ranking/                       # 排序模块
│   │   ├── prerank.py                 # 粗排（LightGBM）
│   │   ├── rank.py                    # 精排（DNN）
│   │   ├── rerank.py                  # 策略重排
│   │   └── mixer.py                   # 混排
│   └── scene/                         # 场景入口
│       ├── home_feed.py
│       ├── search_feed.py
│       ├── follow_feed.py
│       └── community_feed.py
├── llm/                               # LLM 核心
│   ├── base.py                        # LLMBackend ABC
│   ├── backends/                      # LLM 后端
│   │   ├── vllm_backend.py
│   │   ├── triton_backend.py
│   │   └── mock_backend.py
│   ├── factory.py                     # LLM 工厂
│   ├── agent/                         # Agent 框架
│   │   ├── base.py                    # Agent/Tool ABC
│   │   ├── planner.py
│   │   ├── executor.py
│   │   ├── critic.py
│   │   ├── monitor_agent.py           # 监控分析 Agent
│   │   └── tools/                     # Agent 工具集
│   ├── tasks/                         # LLM 任务
│   │   ├── embedder.py                # Embedding 生成
│   │   ├── content_gen.py             # 内容模拟
│   │   ├── rerank_summary.py          # 搜索重排摘要
│   │   └── semantic_search.py         # 语义搜索
│   └── prompt/                        # Prompt 管理
│       ├── templates/
│       └── manager.py
├── feature/                           # 特征平台
│   ├── platform.py                    # ★ 统一外部 API
│   ├── registry/                      # 特征注册中心
│   │   ├── registry.py
│   │   ├── feature_def.py             # FeatureDef 定义
│   │   ├── group_def.py               # FeatureGroupDef 定义
│   │   ├── lineage.py                 # 特征血缘追踪
│   │   └── validator.py
│   ├── manager/                       # 特征管理
│   │   ├── catalog.py
│   │   ├── version.py
│   │   └── lifecycle.py
│   ├── store/                         # 特征存储
│   │   ├── base.py
│   │   ├── redis_store.py
│   │   ├── mysql_store.py
│   │   ├── hive_store.py
│   │   ├── faiss_store.py
│   │   ├── context_store.py
│   │   └── router.py                  # 存储路由
│   ├── engine/                        # DSL 引擎
│   │   ├── parser.py
│   │   ├── executor.py
│   │   ├── functions/
│   │   ├── composer.py
│   │   └── cache.py
│   ├── server/                        # 特征服务
│   │   ├── feature_server.py
│   │   └── feature_plugin.py
│   ├── profiles/                      # 用户/物品画像
│   │   ├── user_profile.py
│   │   ├── item_profile.py
│   │   ├── social_profile.py
│   │   └── context_profile.py
│   └── offline/                       # 离线特征
│       ├── feature_gen.py
│       ├── backfill.py
│       └── stats.py
├── monitor/                           # 监控体系
│   ├── tracer.py                      # RecTracer 链路追踪
│   ├── collector.py
│   ├── writer.py
│   ├── training_logger.py             # 训练日志落盘
│   ├── metrics.py                     # Prometheus 指标
│   ├── schema.py                      # 监控数据结构
│   └── sinks/                         # 日志输出
│       ├── file.py
│       ├── clickhouse.py
│       ├── training.py
│       └── stdout.py
├── storage/                           # 存储后端封装
│   ├── redis.py
│   ├── mysql.py
│   ├── clickhouse.py
│   └── faiss.py
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yaml
│   └── conf/
├── scripts/
│   ├── train_two_tower.py
│   ├── train_ranking.py
│   ├── generate_embeddings.py
│   └── backfill_features.py
├── utils/
│   ├── logger.py
│   ├── timer.py
│   ├── hash.py
│   └── serialization.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── data/
│   └── training/                      # 训练日志落盘路径
├── pyproject.toml
└── README.md
```

## 2. 核心抽象层设计

### 2.1 PipelineStage — 统一链路接口

所有链路模块（召回、粗排、精排、重排、混排）实现相同的抽象接口，确保协议一致、可互换：

```python
from abc import ABC, abstractmethod

class PipelineStage(ABC):
    """推荐链路统一抽象接口"""

    @abstractmethod
    def name(self) -> str:
        """模块名称"""

    @abstractmethod
    def process(self, ctx: RecContext) -> RecContext:
        """
        处理推荐上下文，返回更新后的上下文。
        每个模块只读写 ctx 中属于自己的字段。
        """

    @abstractmethod
    def warmup(self) -> None:
        """预热（加载模型、连接存储等）"""

    @abstractmethod
    def health_check(self) -> bool:
        """健康检查"""

    @abstractmethod
    def shutdown(self) -> None:
        """优雅关闭"""
```

### 2.2 RecContext — 上下文透传

Context 对象贯穿整个链路，每个模块只读写自己的字段：

```python
@dataclass
class StageMetrics:
    stage_name: str
    latency_ms: float
    input_count: int
    output_count: int
    extra: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Item:
    id: str
    score: float = 0.0
    source: str = ""               # 来源通道
    features: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class RecContext:
    request_id: str
    user_id: str
    scene: str                      # 场景标识
    candidates: List[Item] = field(default_factory=list)
    user_features: Dict[str, Any] = field(default_factory=dict)
    stage_metrics: List[StageMetrics] = field(default_factory=list)
    extras: Dict[str, Any] = field(default_factory=dict)
```

### 2.3 ModelService — 模型服务接口

```python
class ModelService(ABC):
    """模型服务抽象接口"""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def version(self) -> str: ...

    @abstractmethod
    def predict(self, features: np.ndarray) -> np.ndarray: ...

    @abstractmethod
    def warmup(self) -> None: ...

    @abstractmethod
    def shutdown(self) -> None: ...

    @abstractmethod
    def input_schema(self) -> Dict: ...

    @abstractmethod
    def output_dim(self) -> int: ...
```

### 2.4 LLMBackend — LLM 后端接口

```python
class LLMBackend(ABC):
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str: ...

    @abstractmethod
    def generate_stream(self, prompt: str, **kwargs) -> Iterator[str]: ...

    @abstractmethod
    def embed(self, text: str) -> List[float]: ...

    @abstractmethod
    def health_check(self) -> bool: ...

    @abstractmethod
    def warmup(self) -> None: ...
```

### 2.5 Agent / Tool — LLM Agent 框架接口

```python
class Agent(ABC):
    @abstractmethod
    def run(self, task: AgentTask) -> AgentResult: ...

    @abstractmethod
    def available_tools(self) -> List[Tool]: ...

    @abstractmethod
    def plan(self, task: AgentTask) -> List[Step]: ...

    @abstractmethod
    def reflect(self, result: AgentResult) -> Optional[str]: ...

class Tool(ABC):
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def description(self) -> str: ...

    @abstractmethod
    def execute(self, params: Dict) -> Any: ...

    @abstractmethod
    def schema(self) -> Dict: ...
```

## 3. 模型服务模块

### 3.1 ModelManager — 模型生命周期管理

```python
class ModelManager:
    """
    职责：
    - 模型注册/注销
    - 模型加载/卸载
    - 模型热更新（版本切换）
    - 批量推理调度
    - 健康检查聚合
    """

    def register(self, model: ModelService) -> None: ...
    def get(self, name: str) -> ModelService: ...
    def reload(self, name: str, version: str) -> None: ...  # 热更新
    def predict_batch(self, name: str, features: np.ndarray) -> np.ndarray: ...
```

### 3.2 TwoTowerModel — 双塔个性化召回

```python
class TwoTowerModel(ModelService):
    """
    双塔模型：UserTower + ItemTower
    - encode_users: 批量用户 embedding
    - encode_items: 批量物品 embedding
    - 用户/物品 embedding 存入 Faiss 进行 ANN 检索
    """

    def encode_users(self, user_features: np.ndarray) -> np.ndarray: ...
    def encode_items(self, item_features: np.ndarray) -> np.ndarray: ...
```

### 3.3 推理后端

| 后端 | 适用场景 | 说明 |
|------|---------|------|
| PyTorchBackend | 开发/调试 | 直接 PyTorch 推理 |
| ONNXBackend | 生产部署 | ONNX Runtime 优化推理 |
| TritonBackend | 高性能场景 | NVIDIA Triton 推理服务器 |
| BatchProcessor | 批量推理 | 请求聚合 + 批处理调度 |

## 4. 特征平台

### 4.1 统一 API — FeaturePlatform

```python
class FeaturePlatform:
    """
    特征平台唯一外部入口。
    内部路由到不同存储后端，调用方无需关心数据源。
    """

    def get_features(self, entity_id: str, feature_names: List[str]) -> Dict[str, Any]: ...
    def get_feature_group(self, entity_id: str, group_name: str) -> Dict[str, Any]: ...
    def batch_get_features(self, entity_ids: List[str], feature_names: List[str]) -> List[Dict[str, Any]]: ...
```

### 4.2 FeatureDef — 特征定义

```python
class FeatureDef:
    slot_id: str                        # 特征唯一标识（全局唯一，用于模型训练 slot 映射）
    name: str
    dtype: str                          # int, float, string, array, map
    value_type: str                     # dense, sparse, scalar
    dimension: int                      # 向量维度（用于 embedding）
    source: FeatureSource               # redis / mysql / hive / faiss / context / derived / composite
    source_config: Dict[str, Any]       # 存储定位配置
    dsl: Optional[str]                  # 衍生特征的 DSL 表达式
    composite_of: Optional[List[str]]   # 组合特征的子特征列表
    depends_on: List[str]               # 依赖的上游特征
    depended_by: List[str]              # 被依赖的下游特征（反向索引）
    status: FeatureStatus               # active / deprecated / draft
    version: str
    owner: str
```

### 4.3 FeatureLineage — 特征血缘

```python
class FeatureLineage:
    """
    特征血缘追踪：通过 DFS 遍历依赖图
    - get_upstream: 获取某特征的所有上游依赖
    - get_downstream: 获取某特征的所有下游影响
    - impact_analysis: 变更影响分析
    """

    def get_upstream(self, feature_name: str) -> List[FeatureDef]: ...
    def get_downstream(self, feature_name: str) -> List[FeatureDef]: ...
    def impact_analysis(self, feature_name: str) -> ImpactReport: ...
```

### 4.4 DSL 引擎

支持的特征计算表达式：

| 类别 | 支持表达式 |
|------|-----------|
| 算术运算 | `+`, `-`, `*`, `/`, `**`, `%` |
| 函数 | `time_decay()`, `bucketize()`, `normalize()`, `hash_encode()`, `sigmoid()` |
| 条件 | `if(cond, a, b)`, `case(cond1->val1, cond2->val2, default)` |
| 聚合 | `sum()`, `avg()`, `max()`, `min()` |
| 交叉 | `dot(a, b)`, `cosine_sim(a, b)` |
| 字符串 | `split()`, `contains()`, `len()` |

### 4.5 存储路由

```
FeaturePlatform.get_features()
  → StoreRouter.route(feature_name)
    → RedisStore     (实时特征: 用户行为统计、session特征)
    → MySQLStore     (准实时特征: 用户画像、物品属性)
    → FaissStore     (向量特征: embedding)
    → HiveStore      (离线特征: 历史统计、训练特征)
    → ContextStore   (请求上下文特征: 时间、设备)
    → DSLExecutor    (衍生特征: 实时计算)
```

## 5. 用户/物品画像

### 5.1 UserProfile

```python
@dataclass
class UserSocialProfile:
    following_count: int
    follower_count: int
    mutual_follow_count: int
    community_ids: List[str]
    interaction_strength: Dict[str, float]   # user_id → 互动强度

@dataclass
class UserProfile:
    user_id: str
    interests: List[str]                     # 兴趣标签
    long_term_interests: List[float]         # 长期兴趣向量
    short_term_interests: List[float]        # 短期兴趣向量
    behavior_stats: Dict[str, Any]           # 行为统计
    social: UserSocialProfile                # 社交画像
    embedding: Optional[List[float]]         # 用户 embedding
    cold_start: bool                         # 冷启动标记
```

### 5.2 ItemProfile

```python
@dataclass
class ItemAuthor:
    author_id: str
    follower_count: int
    avg_engagement: float

@dataclass
class ItemSocialStats:
    like_count: int
    comment_count: int
    share_count: int
    view_count: int
    engagement_rate: float

@dataclass
class ItemProfile:
    item_id: str
    content_type: str                        # 图文/视频/...
    tags: List[str]
    topics: List[str]
    author: ItemAuthor
    stats: ItemSocialStats
    embedding: Optional[List[float]]
    decay_score: float                       # 时间衰减分
```

### 5.3 ContextProfile

```python
@dataclass
class ContextProfile:
    timestamp: datetime
    hour_of_day: int
    day_of_week: int
    device_type: str                         # iOS/Android/Web
    scene: str                               # 场景标识
    page_number: int                         # 翻页位置
```

## 6. 配置中心 — 图依赖结构

### 6.1 依赖关系图

```
app.yaml（根节点）
  ├── server.yaml         （无依赖）
  ├── storage.yaml        （无依赖）
  ├── features.yaml       （无依赖，被 models/ranking 引用）
  ├── models.yaml         → depends: features.yaml
  ├── recall.yaml         → depends: models.yaml + features.yaml + storage.yaml
  ├── ranking.yaml        → depends: models.yaml + features.yaml
  ├── pipeline.yaml       → depends: recall.yaml + ranking.yaml
  ├── llm.yaml            （无依赖）
  ├── monitor.yaml        → depends: pipeline.yaml
  └── environments/*.yaml （覆盖层，最后加载）
```

### 6.2 配置引用语法

```yaml
# app.yaml
server:
  host: ${server/server.yaml:host}
  port: ${server/server.yaml:port}

models:
  two_tower:
    config: ${model/models.yaml:two_tower}

# 环境变量覆盖
database:
  url: ${env:DB_URL:localhost:3306}
```

### 6.3 加载流程

1. 解析 `app.yaml`，构建依赖图
2. 拓扑排序确定加载顺序
3. 依次加载各配置文件，解析 `${path}` 引用
4. 应用环境覆盖层
5. Pydantic schema 校验
6. 输出 Settings 单例

## 7. 监控体系

### 7.1 RecTracer — 链路追踪

```python
class RecTracer:
    """每请求全链路追踪"""

    def start_stage(self, stage_name: str) -> None: ...
    def end_stage(self, stage_name: str) -> None: ...
    def record_items_stage(self, item_ids: List[str], stage: str, scores: List[float]) -> None: ...
    def record_filter_out(self, item_ids: List[str], reason: str) -> None: ...
    def record_recall_source(self, source: str, count: int) -> None: ...
    def finalize(self) -> PipelineTrace: ...
```

### 7.2 数据结构

```python
@dataclass
class StageTrace:
    stage_name: str
    latency_ms: float
    input_count: int
    output_count: int

@dataclass
class ItemTrace:
    item_id: str
    scores: Dict[str, float]                 # {stage_name: score}
    positions: Dict[str, int]                # {stage_name: position}
    filtered_out_at: Optional[str]           # 被过滤的阶段
    filter_reason: Optional[str]
    recall_sources: List[str]                # 来源通道

@dataclass
class RecallCoverage:
    source: str
    recalled_count: int
    survived_count: int
    final_exposed: int

@dataclass
class PipelineTrace:
    trace_id: str
    stages: List[StageTrace]
    item_traces: List[ItemTrace]
    recall_coverages: List[RecallCoverage]
```

### 7.3 训练日志落盘

```python
@dataclass
class TrainingLogEntry:
    trace_id: str
    # 特征
    user_features: Dict[str, Any]
    item_features: Dict[str, Any]
    social_features: Dict[str, Any]
    context_features: Dict[str, Any]
    cross_features: Dict[str, Any]           # 交叉特征
    # 模型分数
    prerank_score: float
    rank_score: float
    rank_position: int
    # 标签（延迟回填）
    label_clicked: Optional[bool]
    label_liked: Optional[bool]
    label_shared: Optional[bool]
    label_commented: Optional[bool]
    dwell_time_sec: Optional[float]
```

训练日志写入流程：
1. 推荐请求完成后，异步写入实时日志（Parquet 格式）
2. 用户行为上报后，延迟回填 label 字段
3. 离线 T+1 合并特征 + 标签，生成训练样本

### 7.4 Monitor Agent

监控分析 Agent，基于 LLM 的智能运维：
- 分析链路日志，识别性能瓶颈
- 检测召回覆盖率异常
- 发现排序模型效果退化
- 自动生成告警和建议

## 8. 协议定义

### 8.1 Protobuf（未来分布式部署）

```
protocols/proto/
├── common.proto           # 通用类型
├── recommendation.proto   # 推荐请求/响应
├── model_service.proto    # 模型服务协议
├── llm_service.proto      # LLM 服务协议
├── feature_service.proto  # 特征服务协议
└── social_service.proto   # 社交服务协议
```

### 8.2 Pydantic Schema（当前 HTTP）

```python
# schemas/request.py
class RecRequest(BaseModel):
    user_id: str
    scene: str
    page: int = 0
    num: int = 20
    context: Optional[Dict[str, Any]] = None

# schemas/response.py
class RecResponse(BaseModel):
    request_id: str
    items: List[RecItem]
    trace_id: Optional[str] = None

class RecItem(BaseModel):
    item_id: str
    score: float
    source: str
    summary: Optional[str] = None           # LLM 生成的摘要
```

## 9. 部署架构

### 9.1 Docker Compose 服务编排

```yaml
services:
  rec-server:        # FastAPI 推荐服务
  llm-server:        # vLLM 推理服务
  redis:             # 实时特征缓存
  mysql:             # 用户/物品画像
  clickhouse:        # 监控/日志 OLAP
  grafana:           # 可视化监控
  prometheus:        # 指标采集
  vector:            # 日志收集
```

### 9.2 资源规划

| 服务 | 资源 | 说明 |
|------|------|------|
| rec-server | 4C8G | FastAPI + 模型推理 |
| llm-server | GPU V100 16G | vLLM 推理 |
| redis | 2G | 特征缓存 |
| mysql | 10G | 画像存储 |
| clickhouse | 20G | 日志/监控 OLAP |
