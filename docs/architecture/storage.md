# 存储层设计

系统使用 4 种存储引擎，各司其职。

## 存储矩阵

| 存储 | 用途 | 接口 | 配置 |
|------|------|------|------|
| **Redis** | 热特征缓存、会话、社交关系 | `storage.redis.RedisStore` | `storage.yaml:redis` |
| **MySQL** | 用户画像、内容元数据 | `storage.mysql.MySQLStore` | `storage.yaml:mysql` |
| **ClickHouse** | 链路追踪、训练日志、OLAP 分析 | `storage.clickhouse.ClickHouseStore` | `storage.yaml:clickhouse` |
| **Faiss** | 向量召回 ANN 索引 | `storage.faiss.FaissStore` | 模型配置 |

## RedisStore

异步 Redis 封装，基于 `redis-py`。

```python
from storage.redis import RedisStore

store = RedisStore(host="localhost", port=6379, db=0)
await store.set_hash("user:001", {"interests": "tech,ai", "age": "25"})
data = await store.get_hash("user:001")
```

## MySQLStore

异步 MySQL 连接池，基于 `aiomysql`。

```python
from storage.mysql import MySQLStore

store = MySQLStore(host="localhost", port=3306, db="rec_platform",
                   user="rec_user", password="rec_pass")
row = await store.fetch_one("SELECT * FROM users WHERE user_id = %s", ("u001",))
rows = await store.fetch_all("SELECT * FROM items WHERE status = %s", ("active",))
await store.execute("INSERT INTO track_events (...) VALUES (...)", (...))
```

## ClickHouseStore

ClickHouse OLAP 查询 + 批量写入。

```python
from storage.clickhouse import ClickHouseStore

store = ClickHouseStore(host="localhost", port=8123, database="rec_monitor")
rows = await store.query("SELECT * FROM traces WHERE date = today()")
await store.batch_insert("training_logs", columns=["trace_id","label"], rows=data)
```

## FaissStore

Faiss ANN 向量检索，支持多种索引类型。

```python
from storage.faiss import FaissStore

store = FaissStore(dim=64, index_type="ivf")
store.build(vectors)           # 构建索引
ids, dists = store.search(query_vec, top_k=50)  # 检索
store.add(new_vectors, ids)    # 增量添加
count = store.count()          # 向量总数
```

## 连接配置

```yaml
# configs/storage/storage.yaml
redis:
  host: localhost
  port: 6379
  db: 0
  max_connections: 20

mysql:
  host: localhost
  port: 3306
  database: rec_platform
  user: rec_user
  password: rec_pass
  pool_size: 10

clickhouse:
  host: localhost
  port: 8123
  database: rec_monitor
```

环境覆盖通过 `configs/environments/*.yaml` 自动合并。
