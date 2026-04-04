# 特征存储

4 种存储后端，统一 `FeatureStore` 接口。

| 存储 | 类 | 适用场景 |
|------|-----|----------|
| Redis | `RedisStore` | 热特征、实时更新 |
| MySQL | `MySQLStore` | 持久化、复杂查询 |
| ClickHouse | `ClickHouseStore` | 离线特征、OLAP |
| Faiss | `FaissStore` | 向量特征、ANN 检索 |

## StoreRouter

自动路由特征请求到对应存储。

```python
from feature.store import StoreRouter

router = StoreRouter()
router.register("redis", RedisStore(...))
router.register("mysql", MySQLStore(...))

store = router.get_store("user_interests")  # 根据特征定义的 source 路由
```

## 接口

```python
class FeatureStore(ABC):
    async def get(self, key: str, fields: list[str]) -> dict
    async def batch_get(self, keys: list[str], fields: list[str]) -> list[dict]
    async def set(self, key: str, values: dict) -> None
    async def delete(self, key: str) -> None
```
