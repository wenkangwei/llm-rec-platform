# 召回模块

7 个召回通道并行执行，`RecallMerger` 统一合并去重。

## 通道配置

```yaml
# configs/pipeline/recall.yaml
channels:
  personalized:    {enabled: true, weight: 0.30, class: "...PersonalizedRecall",  params: {top_k: 500}}
  collaborative:   {enabled: true, weight: 0.20, class: "...CollaborativeRecall", params: {top_k: 300}}
  social:          {enabled: true, weight: 0.15, class: "...SocialRecall",        params: {top_k: 200}}
  community:       {enabled: true, weight: 0.10, class: "...CommunityRecall",     params: {top_k: 200}}
  hot:             {enabled: true, weight: 0.10, class: "...HotRecall",           params: {top_k: 200}}
  operator:        {enabled: true, weight: 0.05, class: "...OperatorRecall",      params: {top_k: 50}}
  cold_start:      {enabled: true, weight: 0.10, class: "...ColdStartRecall",     params: {top_k: 200}}
merger:
  max_candidates: 3000
  dedup_by: "item_id"
```

## 各通道说明

| 通道 | 类 | 召回源 | 适用场景 |
|------|-----|--------|----------|
| personalized | `PersonalizedRecall` | TwoTower + Faiss ANN | 有行为用户 |
| collaborative | `CollaborativeRecall` | ItemCF 相似物品 | 老用户 |
| social | `SocialRecall` | 关注用户最近发布 | 社交场景 |
| community | `CommunityRecall` | 社区热门内容 | 社区场景 |
| hot | `HotRecall` | 全局/分类热门 | 兜底+补量 |
| operator | `OperatorRecall` | 运营置顶/精选 | 运营干预 |
| cold_start | `ColdStartRecall` | 新物品探索+LLM生成 | 新用户/新物品 |

## RecallMerger 处理流程

1. 并行调用所有 enabled 通道的 `process(ctx)`
2. 收集各通道候选集，按 weight 加权排序
3. 按 `item_id` 去重（保留最高分）
4. 截断到 `max_candidates`

## 通过 Agent 控制通道

```bash
# 关闭通道
curl -X POST /api/chat -d '{"message":"关闭热门召回通道"}'
# 调权重
curl -X POST /api/chat -d '{"message":"将个性化召回权重调到0.4"}'
```
