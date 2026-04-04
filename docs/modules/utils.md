# 工具函数

## Logger

```python
from utils.logger import get_logger, get_struct_logger

logger = get_logger("my_module")           # 标准 logging
slogger = get_struct_logger("my_module")   # 结构化 KV 日志
slogger.info("请求完成", latency_ms=120, user_id="u001")
```

## Hash

```python
from utils.hash import md5_hash, consistent_bucket, generate_request_id, generate_trace_id

h = md5_hash("input_string")                    # MD5 哈希
bucket = consistent_bucket("user_001", 100)      # 0-99 确定性分桶
req_id = generate_request_id()                   # 唯一请求 ID
trace_id = generate_trace_id()                   # 唯一追踪 ID
fp = fingerprint({"a": 1, "b": [2, 3]})         # 字典指纹（确定性序列化）
```

## Timer

```python
from utils.timer import timer, async_timer

with timer("my_operation") as t:
    do_something()
print(t.elapsed_ms)  # 耗时毫秒

@async_timer
async def my_async_func():
    ...
```

## Serialization

```python
from utils.serialization import to_json, from_json

json_str = to_json(my_dataclass_instance)
obj = from_json(json_str, MyClass)
```
