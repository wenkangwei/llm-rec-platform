# 特征平台使用

## 注册特征

```python
from feature.registry import FeatureRegistry, FeatureDef

registry = FeatureRegistry()
registry.register(FeatureDef(
    name="user_interests",
    type="string",
    source="redis",
    fields=["interests", "updated_at"]
))
```

## 获取特征

```python
from feature.platform import FeaturePlatform

platform = FeaturePlatform(registry=registry, store_router=router)

# 单特征
features = platform.get_features("user_001", ["user_interests"])

# 批量
batch = platform.batch_get_features(["user_001", "user_002"], ["user_interests"])
```

## 特征组

7 个预定义特征组：

| 特征组 | 说明 | 存储 |
|--------|------|------|
| user_profile | 用户画像（兴趣/年龄/性别） | Redis |
| user_behavior | 行为统计（点击率/活跃度） | Redis |
| item_content | 内容特征（类型/标签/时效） | MySQL |
| item_stats | 内容统计（点赞数/评论数） | Redis |
| social_relation | 社交关系（关注/粉丝/共同） | Redis |
| context_feature | 请求上下文（时间/设备/场景） | 内存 |
| cross_feature | 交叉特征（用户×物品） | 在线计算 |

## 特征引擎 DSL

```python
from feature.engine import Composer

composer = Composer(registry=registry, store_router=router)
features = composer.compose(
    user_id="user_001",
    item_ids=["item_001", "item_002"],
    groups=["user_profile", "item_content", "cross_feature"]
)
```

## 特征存储

| 存储 | 场景 | 类 |
|------|------|-----|
| RedisStore | 热特征缓存 | `feature.store.RedisStore` |
| MySQLStore | 持久化特征 | `feature.store.MySQLStore` |
| ClickHouseStore | 离线特征 | `feature.store.ClickHouseStore` |
| FaissStore | 向量特征 | `feature.store.FaissStore` |
