# 特征引擎

## Composer

组合多源特征为模型输入。

```python
from feature.engine import Composer

composer = Composer(registry=registry, store_router=store_router)
features = composer.compose(
    user_id="user_001",
    item_ids=["item_001", "item_002"],
    groups=["user_profile", "item_content"]
)
```

## DSL 执行引擎

支持简单表达式解析：

```python
from feature.engine import Executor, Parser

executor = Executor(registry=registry)
result = executor.evaluate("user_profile.age * 2 + item_stats.click_count")
```

## Cache

LRU 特征缓存，减少存储查询。

```python
from feature.engine import Cache

cache = Cache(max_size=10000, ttl_sec=300)
cached = cache.get("user_001", ["user_interests"])
cache.set("user_001", {"user_interests": "tech,ai"})
```
