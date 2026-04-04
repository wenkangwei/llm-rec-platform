"""ClickHouse 存储封装 — 监控日志 OLAP"""

from __future__ import annotations

import asyncio
from typing import Any

from utils.logger import get_struct_logger

logger = get_struct_logger("storage.clickhouse")


class ClickHouseStore:
    """ClickHouse 存储封装，用于监控数据和训练日志。"""

    def __init__(self, host: str = "localhost", port: int = 9000,
                 user: str = "default", password: str = "",
                 database: str = "rec_monitor"):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._client = None

    def connect(self) -> None:
        """建立连接（同步）。"""
        import clickhouse_driver
        self._client = clickhouse_driver.Client(
            host=self._host, port=self._port,
            user=self._user, password=self._password,
            database=self._database,
        )
        logger.info("ClickHouse 连接完成", host=self._host, database=self._database)

    async def async_connect(self) -> None:
        """建立连接（异步包装）。"""
        await asyncio.to_thread(self.connect)

    def close(self) -> None:
        """关闭连接。"""
        self._client = None

    async def async_close(self) -> None:
        """关闭连接（异步包装）。"""
        self.close()

    def execute(self, query: str, params: dict | None = None) -> list[dict]:
        """执行查询（同步）。"""
        if self._client is None:
            return []
        try:
            return self._client.execute(query, params or {}, with_column_types=True)
        except Exception as e:
            logger.error(f"ClickHouse 查询失败", error=str(e))
            return []

    async def async_execute(self, query: str, params: dict | None = None) -> list[dict]:
        """执行查询（异步包装）。"""
        return await asyncio.to_thread(self.execute, query, params)

    def insert_batch(self, table: str, data: list[dict]) -> None:
        """批量写入（同步）。"""
        if self._client is None or not data:
            return
        try:
            columns = list(data[0].keys())
            rows = [tuple(item[c] for c in columns) for item in data]
            self._client.insert(table, rows, column_names=columns)
            logger.debug(f"ClickHouse 写入 {len(rows)} 条到 {table}")
        except Exception as e:
            logger.error(f"ClickHouse 写入失败", error=str(e))

    async def async_insert_batch(self, table: str, data: list[dict]) -> None:
        """批量写入（异步包装）。"""
        await asyncio.to_thread(self.insert_batch, table, data)
