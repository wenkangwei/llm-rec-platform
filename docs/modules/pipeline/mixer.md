# MixerStage — 混排模块

按内容类型比例做加权轮询混排。

## 配置

```yaml
# ranking.yaml → mixer
strategy: "weighted_round_robin"
slots:
  - content_type: "article"
    ratio: 0.5
  - content_type: "video"
    ratio: 0.3
  - content_type: "post"
    ratio: 0.2
```

## 原理

1. 按内容类型分组候选
2. 按比例分配每个类型的输出数量
3. 轮询从各组中取候选，直到总数达到 `page_size`
4. 保证最终结果的内容类型分布符合配置比例

## 示例

`page_size=20`，比例 `article:0.5, video:0.3, post:0.2`：

- article: 10 条
- video: 6 条
- post: 4 条
