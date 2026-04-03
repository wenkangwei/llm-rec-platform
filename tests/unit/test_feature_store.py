"""feature store 单元测试 — Redis / MySQL 特征存储"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from feature.store.redis_store import RedisFeatureStore
from feature.store.mysql_store import MySQLFeatureStore


# ===== RedisFeatureStore =====

class TestRedisFeatureStore:
    @pytest.fixture
    def mock_redis(self):
        redis = MagicMock()
        redis._pool = MagicMock()  # not None
        redis.get = AsyncMock()
        redis.mget = AsyncMock()
        redis.set = AsyncMock()
        return redis

    @pytest.fixture
    def store(self, mock_redis):
        return RedisFeatureStore(mock_redis)

    @pytest.mark.asyncio
    async def test_get_hit(self, store, mock_redis):
        mock_redis.get.return_value = {"age": 25, "gender": "M", "extra": 1}
        result = await store.get("u1", ["age", "gender"])
        assert result == {"age": 25, "gender": "M"}
        mock_redis.get.assert_called_once_with("feat:u1")

    @pytest.mark.asyncio
    async def test_get_miss(self, store, mock_redis):
        mock_redis.get.return_value = None
        result = await store.get("u1", ["age"])
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_empty_dict(self, store, mock_redis):
        mock_redis.get.return_value = {}
        result = await store.get("u1", ["age"])
        assert result == {}

    @pytest.mark.asyncio
    async def test_batch_get(self, store, mock_redis):
        mock_redis.mget.return_value = [
            {"age": 25},
            None,
            {"age": 30},
        ]
        result = await store.batch_get(["u1", "u2", "u3"], ["age"])
        assert len(result) == 3
        assert result[0] == {"age": 25}
        assert result[1] == {}
        assert result[2] == {"age": 30}

    @pytest.mark.asyncio
    async def test_set(self, store, mock_redis):
        await store.set("u1", {"age": 25}, ttl=3600)
        mock_redis.set.assert_called_once_with("feat:u1", {"age": 25}, ttl=3600)

    @pytest.mark.asyncio
    async def test_set_no_ttl(self, store, mock_redis):
        await store.set("u1", {"age": 25})
        mock_redis.set.assert_called_once_with("feat:u1", {"age": 25}, ttl=None)

    @pytest.mark.asyncio
    async def test_health_check(self, store):
        assert await store.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_no_pool(self, mock_redis):
        mock_redis._pool = None
        store = RedisFeatureStore(mock_redis)
        assert await store.health_check() is False


# ===== MySQLFeatureStore =====

class TestMySQLFeatureStore:
    @pytest.fixture
    def mock_mysql(self):
        mysql = MagicMock()
        mysql._pool = MagicMock()  # not None
        mysql.fetch_one = AsyncMock()
        mysql.execute = AsyncMock()
        return mysql

    @pytest.fixture
    def store(self, mock_mysql):
        return MySQLFeatureStore(mock_mysql)

    @pytest.mark.asyncio
    async def test_get_hit(self, store, mock_mysql):
        mock_mysql.fetch_one.return_value = {"age": 25, "gender": "M"}
        result = await store.get("u1", ["age", "gender"])
        assert result == {"age": 25, "gender": "M"}
        mock_mysql.fetch_one.assert_called_once_with(
            "user_features",
            conditions={"entity_id": "u1"},
            columns=["age", "gender"],
        )

    @pytest.mark.asyncio
    async def test_get_miss(self, store, mock_mysql):
        mock_mysql.fetch_one.return_value = None
        result = await store.get("u1", ["age"])
        assert result == {}

    @pytest.mark.asyncio
    async def test_batch_get(self, store, mock_mysql):
        mock_mysql.fetch_one.side_effect = [
            {"age": 25},
            {"age": 30},
        ]
        result = await store.batch_get(["u1", "u2"], ["age"])
        assert len(result) == 2
        assert result[0] == {"age": 25}
        assert result[1] == {"age": 30}

    @pytest.mark.asyncio
    async def test_set(self, store, mock_mysql):
        await store.set("u1", {"age": 25, "gender": "M"})
        mock_mysql.execute.assert_called_once()
        sql = mock_mysql.execute.call_args[0][0]
        values = mock_mysql.execute.call_args[0][1]
        assert "INSERT INTO user_features" in sql
        assert "ON DUPLICATE KEY UPDATE" in sql
        assert values[0] == "u1"

    @pytest.mark.asyncio
    async def test_set_ignores_ttl(self, store, mock_mysql):
        await store.set("u1", {"age": 25}, ttl=3600)
        # ttl param accepted but not used in SQL
        mock_mysql.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check(self, store):
        assert await store.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_no_pool(self, mock_mysql):
        mock_mysql._pool = None
        store = MySQLFeatureStore(mock_mysql)
        assert await store.health_check() is False

    @pytest.mark.asyncio
    async def test_custom_table(self, mock_mysql):
        store = MySQLFeatureStore(mock_mysql, table="item_features")
        mock_mysql.fetch_one.return_value = {"price": 100}
        await store.get("i1", ["price"])
        mock_mysql.fetch_one.assert_called_once_with(
            "item_features",
            conditions={"entity_id": "i1"},
            columns=["price"],
        )
