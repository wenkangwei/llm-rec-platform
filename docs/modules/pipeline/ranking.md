# 排序模块

三级排序：粗排（PreRank）→ 精排（Rank）→ 重排（ReRank）。

## PreRankStage — 粗排

LightGBM 模型，万级→千级。

```yaml
# ranking.yaml → prerank
model: lightgbm
max_candidates: 1000
score_threshold: 0.1
```

- 输入：召回合并后候选（~3000）
- 输出：Top 1000，过滤 score < 0.1
- 特征：用户基础特征 + 物品基础特征 + 交叉统计

## RankStage — 精排

DCN-v2 或 DIN 模型，千级→百级。

```yaml
# ranking.yaml → rank
model: dcn
max_candidates: 200
batch_size: 64
```

- 输入：粗排后候选（~1000）
- 输出：Top 200
- 模型选择：DCN（特征交叉）/ DIN（行为序列注意力）

## ReRankStage — 重排

业务规则 + 多样性 + 疲劳控制。

```yaml
# ranking.yaml → rerank
diversity:
  enabled: true
  same_author_max: 2
  same_tag_max: 3
  mmr_lambda: 0.5
fatigue:
  enabled: true
  recent_expose_window: 100
  max_repeat: 2
boost:
  new_content_weight: 1.2
  followed_author_weight: 1.1
```

| 策略 | 说明 |
|------|------|
| 多样性（MMR） | 同作者最多 N 篇，同标签最多 M 篇 |
| 疲劳控制 | 近 N 次曝光中同物品最多出现 M 次 |
| 业务加权 | 新内容 ×1.2，关注作者 ×1.1 |

## 数据流

```
~3000 候选 → PreRank → ~1000 → Rank → ~200 → ReRank → ~200(重排后)
```
