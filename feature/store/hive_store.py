"""Hive 数据仓库特征存储 — 离线批量特征读取"""

from __future__ import annotations

from typing import Any

from feature.store.base import FeatureStore
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.store.hive")


class HiveFeatureStore(FeatureStore):
    """基于 Hive 的离线特征存储。

    通过 PyHive 连接 Hive 数据仓库，执行 SQL 查询获取特征。
    主要用于离线批量特征读取和 T+1 特征计算。
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 10000,
        database: str = "rec_features",
        auth: str = "NONE",
        table_prefix: str = "dw_",
    ):
        self._host = host
        self._port = port
        self._database = database
        self._auth = auth
        self._table_prefix = table_prefix
        self._connection: Any = None

    def _get_connection(self) -> Any:
        """获取 Hive 连接。"""
        if self._connection is not None:
            return self._connection

        try:
            from pyhive import hive
            self._connection = hive.Connection(
                host=self._host,
                port=self._port,
                database=self._database,
                auth=self._auth,
            )
            logger.info(f"Hive 连接成功", host=self._host, database=self._database)
            return self._connection
        except ImportError:
            logger.warning("pyhive 未安装，HiveFeatureStore 功能不可用")
            return None
        except Exception as e:
            logger.error(f"Hive 连接失败", error=str(e))
            return None

    def _execute_query(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """执行 SQL 查询并返回结果。"""
        conn = self._get_connection()
        if conn is None:
            return []

        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            cursor.close()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Hive 查询失败", sql=sql[:200], error=str(e))
            return []

    async def get(self, entity_id: str, feature_names: list[str]) -> dict[str, Any]:
        """获取实体的离线特征。"""
        columns = ", ".join(feature_names)
        sql = f"SELECT {columns} FROM {self._table_prefix}user_features WHERE entity_id = :entity_id LIMIT 1"
        rows = self._execute_query(sql, {"entity_id": entity_id})
        if rows:
            return {k: v for k, v in rows[0].items() if v is not None}
        return {}

    async def batch_get(self, entity_ids: list[str], feature_names: list[str]) -> list[dict[str, Any]]:
        """批量获取离线特征。"""
        if not entity_ids:
            return []

        columns = ", ".join(feature_names)
        placeholders = ", ".join([f"'{eid}'" for eid in entity_ids])
        sql = (
            f"SELECT entity_id, {columns} FROM {self._table_prefix}user_features "
            f"WHERE entity_id IN ({placeholders})"
        )
        rows = self._execute_query(sql)
        result_map = {}
        for row in rows:
            eid = row.pop("entity_id", None)
            if eid:
                result_map[eid] = {k: v for k, v in row.items() if v is not None}

        return [result_map.get(eid, {}) for eid in entity_ids]

    async def set(self, entity_id: str, features: dict[str, Any], ttl: int | None = None) -> None:
        """写入特征到 Hive（通过 INSERT 语句）。

        离线场景通常不通过此接口写入，而是通过批量 ETL 任务。
        """
        if not features:
            return

        columns = ["entity_id"] + list(features.keys())
        values = [f"'{entity_id}'"] + [
            f"'{v}'" if isinstance(v, str) else str(v) for v in features.values()
        ]
        sql = (
            f"INSERT INTO TABLE {self._table_prefix}user_features ({', '.join(columns)}) "
            f"VALUES ({', '.join(values)})"
        )
        self._execute_query(sql)
        logger.info(f"Hive 特征写入", entity_id=entity_id, features=list(features.keys()))

    def query_custom(self, sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """执行自定义 SQL 查询。"""
        return self._execute_query(sql, params)

    async def health_check(self) -> bool:
        """健康检查。"""
        conn = self._get_connection()
        if conn is None:
            return False
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception:
            return False

    def close(self) -> None:
        """关闭连接。"""
        if self._connection:
            try:
                self._connection.close()
            except Exception as e:
                logger.debug(f"Hive 连接失败", error=str(e))
            self._connection = None
