"""Redis 存储封装 — 实时特征缓存"""

from __future__ import annotations

import json
from typing import Any

from utils.logger import get_struct_logger

logger = get_struct_logger("storage.redis")


class RedisStore:
    """Redis 异步存储封装。"""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0,
                 password: str | None = None, pool_size: int = 10):
        self._host = host
        self._port = port
        self._db = db
        self._password = password
        self._pool_size = pool_size
        self._pool = None

    async def connect(self) -> None:
        """建立连接池。"""
        import redis.asyncio as aioredis
        self._pool = aioredis.ConnectionPool(
            host=self._host, port=self._port, db=self._db,
            password=self._password, max_connections=self._pool_size,
        )
        logger.info("Redis 连接池创建完成", host=self._host, port=self._port)

    async def close(self) -> None:
        """关闭连接池。"""
        if self._pool:
            await self._pool.disconnect()
            self._pool = None

    def _get_client(self):
        import redis.asyncio as aioredis
        return aioredis.Redis(connection_pool=self._pool)

    async def get(self, key: str) -> dict[str, Any] | None:
        """获取哈希字段。"""
        client = self._get_client()
        try:
            data = await client.hgetall(key)
            if not data:
                return None
            return {k.decode(): json.loads(v.decode()) for k, v in data.items()}
        except Exception as e:
            logger.error(f"Redis GET 失败: {key}", error=str(e))
            return None

    async def set(self, key: str, data: dict[str, Any], ttl: int | None = None) -> None:
        """设置哈希字段。"""
        client = self._get_client()
        try:
            mapping = {k: json.dumps(v) for k, v in data.items()}
            await client.hset(key, mapping=mapping)
            if ttl:
                await client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis SET 失败: {key}", error=str(e))

    async def mget(self, keys: list[str]) -> list[dict[str, Any] | None]:
        """批量获取。"""
        results = []
        for key in keys:
            results.append(await self.get(key))
        return results

    async def delete(self, key: str) -> None:
        """删除 key。"""
        client = self._get_client()
        await client.delete(key)
