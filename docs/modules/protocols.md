# 协议与数据结构

## HTTP 请求/响应 Schema

### RecRequest

```python
class RecRequest(BaseModel):
    user_id: str
    scene: str = "home_feed"          # home_feed/follow_feed/community_feed
    page: int = Field(0, ge=0)
    num: int = Field(20, ge=1, le=100)
    context: dict | None = None
```

### RecResponse

```python
class RecResponse(BaseModel):
    request_id: str
    items: list[RecItem]              # [{item_id, score, source, summary, extra}]
    trace_id: str | None
    total: int = 0
    page: int = 0
    has_more: bool = False
```

### SearchRequest / SearchResponse

同 RecRequest/RecResponse，增加 `query` 和 `summary` 字段。

### TrackEvent

```python
class TrackEvent(BaseModel):
    user_id: str
    item_id: str
    action: str                       # click/like/share/comment/dwell/expose
    scene: str = ""
    request_id: str = ""
    dwell_time_sec: float | None = None
```

## 内部数据结构

### RecContext

贯穿整个 Pipeline 的上下文：

```python
@dataclass
class RecContext:
    request_id: str
    user_id: str
    scene: str
    candidates: list[Item]
    user_features: dict
    context_features: dict
    stage_metrics: list[StageMetrics]
    extras: dict
    query: str | None                 # 搜索场景
    page: int = 0
    page_size: int = 20
    degraded: bool = False            # 降级标记
    experiment_id: str = ""           # 实验分流
    variant_name: str = ""
    experiment_overrides: dict        # 变体配置覆盖
```

## gRPC Proto

`protocols/proto/` 下定义了 5 个 service（当前返回 Unimplemented，预留拆分部署）：

- `recommendation.proto` — RecommendationService
- `feature_service.proto` — FeatureService
- `model_service.proto` — ModelService
- `llm_service.proto` — LLMService
- `social_service.proto` — SocialService
