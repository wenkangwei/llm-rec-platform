"""storage 模块单元测试 — Redis/MySQL/ClickHouse 封装"""

from __future__ import annotations

import pytest

from storage.redis import RedisStore, get_redis, set_redis
from storage.mysql import MySQLStore
from storage.clickhouse import ClickHouseStore


# ---------- Redis ----------

class TestRedisStore:
    def test_constructor_defaults(self):
        store = RedisStore()
        assert store._host == "localhost"
        assert store._port == 6379

    def test_constructor_custom(self):
        store = RedisStore(host="redis.prod", port=6380, db=1, password="secret")
        assert store._host == "redis.prod"
        assert store._port == 6380


class TestRedisGlobal:
    def test_get_redis_initially_none(self):
        # get_redis 初始返回 None
        set_redis(None)
        assert get_redis() is None

    def test_set_and_get_redis(self):
        class FakeClient:
            pass
        client = FakeClient()
        set_redis(client)
        assert get_redis() is client
        set_redis(None)  # cleanup


# ---------- MySQL ----------

class TestMySQLStore:
    def test_constructor_defaults(self):
        store = MySQLStore()
        assert store._host == "localhost"
        assert store._port == 3306
        assert store._database == "rec_platform"

    def test_constructor_custom(self):
        store = MySQLStore(host="mysql.prod", port=3307, user="admin", database="rec")
        assert store._host == "mysql.prod"
        assert store._user == "admin"

    def test_pool_initially_none(self):
        store = MySQLStore()
        assert store._pool is None


# ---------- ClickHouse ----------

class TestClickHouseStore:
    def test_constructor_defaults(self):
        store = ClickHouseStore()
        assert store._host == "localhost"
        assert store._port == 9000
        assert store._database == "rec_monitor"

    def test_constructor_custom(self):
        store = ClickHouseStore(host="ch.prod", port=8123, database="analytics")
        assert store._host == "ch.prod"
        assert store._database == "analytics"

    def test_execute_no_client(self):
        store = ClickHouseStore()
        assert store.execute("SELECT 1") == []

    def test_insert_batch_no_client(self):
        store = ClickHouseStore()
        store.insert_batch("table", [{"a": 1}])  # should not raise

    def test_close(self):
        store = ClickHouseStore()
        store.close()  # should not raise
        assert store._client is None
