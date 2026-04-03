"""MySQL 存储封装 — 用户/物品画像"""

from __future__ import annotations

from typing import Any

from utils.logger import get_struct_logger

logger = get_struct_logger("storage.mysql")


class MySQLStore:
    """MySQL 异步存储封装。"""

    def __init__(self, host: str = "localhost", port: int = 3306,
                 user: str = "rec_user", password: str = "rec_pass",
                 database: str = "rec_platform", pool_size: int = 5):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._pool_size = pool_size
        self._pool = None

    async def connect(self) -> None:
        """建立连接池。"""
        import aiomysql
        self._pool = await aiomysql.create_pool(
            host=self._host, port=self._port, user=self._user,
            password=self._password, db=self._database,
            maxsize=self._pool_size, autocommit=True,
        )
        logger.info("MySQL 连接池创建完成", host=self._host, database=self._database)

    async def close(self) -> None:
        """关闭连接池。"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None

    async def fetch_one(self, table: str, conditions: dict[str, Any],
                        columns: list[str] | None = None) -> dict[str, Any] | None:
        """查询单条记录。"""
        cols = ", ".join(columns) if columns else "*"
        where = " AND ".join(f"{k} = %s" for k in conditions.keys())
        sql = f"SELECT {cols} FROM {table} WHERE {where} LIMIT 1"
        values = list(conditions.values())

        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, values)
                return await cur.fetchone()

    async def fetch_all(self, table: str, conditions: dict[str, Any],
                        columns: list[str] | None = None, limit: int = 100) -> list[dict]:
        """查询多条记录。"""
        cols = ", ".join(columns) if columns else "*"
        where = " AND ".join(f"{k} = %s" for k in conditions.keys()) if conditions else "1=1"
        sql = f"SELECT {cols} FROM {table} WHERE {where} LIMIT {limit}"
        values = list(conditions.values())

        async with self._pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql, values)
                return await cur.fetchall()

    async def execute(self, sql: str, values: tuple = ()) -> int:
        """执行写操作。"""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql, values)
                return cur.rowcount
