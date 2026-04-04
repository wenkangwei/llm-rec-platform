# 特征注册

## FeatureRegistry

注册、查找、列出特征定义。

```python
from feature.registry import FeatureRegistry, FeatureDef

registry = FeatureRegistry()

registry.register(FeatureDef(
    name="user_interests",
    type="string",
    source="redis",
    fields=["interests", "updated_at"],
    description="用户兴趣标签"
))

defn = registry.get("user_interests")
all_defs = registry.list_all()
```

## FeatureGroup

分组管理特征。

```python
registry.create_group("user_profile", features=["user_interests", "user_demographics"])
group = registry.get_group("user_profile")
```

## FeatureLineage

追踪特征依赖关系，用于血缘分析和影响评估。
