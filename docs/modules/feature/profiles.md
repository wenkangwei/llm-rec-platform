# 特征画像

4 类特征画像，覆盖推荐系统全链路。

| 画像 | 类 | 特征域 |
|------|-----|--------|
| UserProfile | `UserProfile` | 兴趣标签、年龄段、性别、活跃度 |
| ItemProfile | `ItemProfile` | 内容类型、标签、时效性、质量分 |
| SocialProfile | `SocialProfile` | 关注列表、粉丝数、社区成员、共同关注 |
| ContextProfile | `ContextProfile` | 时间、设备、场景、网络类型 |

```python
from feature.profiles import UserProfile, ItemProfile

user = UserProfile(registry, store)
profile = await user.get("user_001")
# → {"interests": ["tech","ai"], "age_group": "25-34", "active_days_7d": 5}

item = ItemProfile(registry, store)
item_features = await item.get("item_001")
# → {"content_type": "article", "tags": ["AI","ML"], "quality_score": 0.85}
```

## 离线处理

```python
from feature.offline import Backfill, FeatureGenerator, Stats

# 回填历史特征
backfill = Backfill(store)
await backfill.run(date_range=("2024-01-01", "2024-06-01"))

# 生成统计特征
stats = Stats(store)
await stats.compute("user_behavior", window="7d")
```
