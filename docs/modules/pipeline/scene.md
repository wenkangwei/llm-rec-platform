# 场景模块

4 个推荐场景，共享 PipelineExecutor 但各有独立逻辑。

| 场景 | 类 | 入口 | 特殊逻辑 |
|------|-----|------|----------|
| 首页推荐 | `HomeFeedScene` | `POST /api/recommend` scene=home_feed | 完整 5 级漏斗 |
| 搜索推荐 | `SearchFeedScene` | `POST /api/search` | query 扩展 + LLM 摘要 |
| 关注流 | `FollowFeedScene` | `POST /api/recommend` scene=follow_feed | 仅 SocialRecall |
| 社区流 | `CommunityFeedScene` | `POST /api/recommend` scene=community_feed | CommunityRecall + community_id |

## 使用

```python
from pipeline.scene import HomeFeedScene

scene = HomeFeedScene(executor=pipeline_executor)
ctx = await scene.recommend(user_id="u001", page=0, page_size=20)
```

## 搜索场景特殊流程

```
query → SemanticSearch.query_expand() → 多 query 并行召回
      → 常规 5 级排序
      → LLM generate summary（top 5 结果）
```
