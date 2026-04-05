"""数据库查询工具 — 支持自然语言转 SQL 查询分析"""

from __future__ import annotations

import json
from typing import Any

from llm.agent.base import Tool
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.agent.tools.db_query")

# 预置常用查询模板
_QUERY_TEMPLATES = {
    "items_count": (
        "SELECT source_type, COUNT(*) AS cnt, "
        "ROUND(AVG(quality_score), 3) AS avg_score, "
        "ROUND(MIN(quality_score), 3) AS min_score, "
        "ROUND(MAX(quality_score), 3) AS max_score "
        "FROM cs_items WHERE status='published' GROUP BY source_type ORDER BY cnt DESC"
    ),
    "items_recent": (
        "SELECT id, title, source_type, quality_score, created_at "
        "FROM cs_items WHERE status='published' "
        "ORDER BY created_at DESC LIMIT {limit}"
    ),
    "items_by_source": (
        "SELECT id, title, quality_score, created_at "
        "FROM cs_items WHERE source_type='{source}' AND status='published' "
        "ORDER BY quality_score DESC LIMIT {limit}"
    ),
    "feeds_status": (
        "SELECT id, name, source_type, status, error_count, "
        "last_fetched_at, created_at FROM cs_feeds ORDER BY id"
    ),
    "items_stats": (
        "SELECT COUNT(*) AS total, "
        "SUM(CASE WHEN is_rewritten=1 THEN 1 ELSE 0 END) AS rewritten_count, "
        "SUM(exposure_count) AS total_exposures, "
        "SUM(click_count) AS total_clicks, "
        "ROUND(AVG(quality_score), 3) AS avg_quality "
        "FROM cs_items WHERE status='published'"
    ),
    "crawl_tasks": (
        "SELECT task_type, status, COUNT(*) AS cnt "
        "FROM cs_crawl_tasks GROUP BY task_type, status ORDER BY cnt DESC"
    ),
    "cleanup_summary": (
        "SELECT policy, status, COUNT(*) AS cnt, "
        "SUM(items_deleted) AS total_deleted "
        "FROM cs_cleanup_logs GROUP BY policy, status ORDER BY cnt DESC"
    ),
    "hot_keywords": (
        "SELECT platform, COUNT(*) AS cnt, MAX(fetched_at) AS latest_fetch "
        "FROM cs_hot_keywords GROUP BY platform ORDER BY cnt DESC"
    ),
    "table_sizes": (
        "SELECT TABLE_NAME AS table_name, TABLE_ROWS AS table_rows, "
        "ROUND(DATA_LENGTH/1024/1024, 2) AS size_mb "
        "FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA='rec_platform' ORDER BY TABLE_ROWS DESC"
    ),
    "item_detail": (
        "SELECT id, title, source_type, quality_score, tags, "
        "exposure_count, click_count, is_rewritten, status, "
        "published_at, created_at "
        "FROM cs_items WHERE id='{item_id}'"
    ),
}


class DBQueryTool(Tool):
    """数据库查询分析工具：查询内容池数据统计、分布、状态。"""

    def __init__(self, mysql_store=None):
        self._mysql = mysql_store

    def name(self) -> str:
        return "db_query"

    def description(self) -> str:
        return (
            "查询数据库获取内容池数据分析：内容数量统计、来源分布、质量评分分布、"
            "抓取任务状态、清理日志、热搜词统计等。"
            "参数: query(查询类型: items_count/items_recent/items_by_source/items_stats/"
            "feeds_status/crawl_tasks/cleanup_summary/hot_keywords/table_sizes/item_detail), "
            "sql(自定义SQL查询，仅支持SELECT), "
            "limit(返回条数，默认20), source(来源类型过滤), item_id(指定item ID)"
        )

    async def execute(self, params: dict[str, Any]) -> Any:
        if not self._mysql:
            return {"error": "MySQL 未连接，无法查询数据库"}

        query_type = params.get("query", "")
        custom_sql = params.get("sql", "")
        limit = min(int(params.get("limit", 20)), 200)
        source = params.get("source", "")
        item_id = params.get("item_id", "")

        try:
            if custom_sql:
                return await self._exec_custom_sql(custom_sql, limit)
            elif query_type in _QUERY_TEMPLATES:
                sql = _QUERY_TEMPLATES[query_type].format(
                    limit=limit, source=source, item_id=item_id,
                )
                return await self._exec_custom_sql(sql, limit)
            else:
                # 兜底：返回内容池概览
                return await self._get_overview()
        except Exception as e:
            logger.error(f"DB query failed: {e}")
            return {"error": str(e), "query_type": query_type}

    async def _exec_custom_sql(self, sql: str, limit: int) -> dict:
        rows = await self._mysql.raw_query(sql, limit=limit)
        return {
            "row_count": len(rows),
            "data": rows,
            "sql": sql,
        }

    async def _get_overview(self) -> dict:
        overview = {}
        for key in ("items_count", "items_stats", "crawl_tasks"):
            try:
                rows = await self._mysql.raw_query(_QUERY_TEMPLATES[key], limit=50)
                overview[key] = rows
            except Exception as e:
                overview[key] = {"error": str(e)}
        return overview

    def schema(self) -> dict:
        return {
            "query": {
                "type": "string",
                "enum": list(_QUERY_TEMPLATES.keys()),
                "description": "预置查询类型",
            },
            "sql": {
                "type": "string",
                "description": "自定义 SELECT SQL（仅读操作）",
            },
            "limit": {"type": "integer", "default": 20, "maximum": 200},
            "source": {"type": "string", "description": "来源类型过滤 (rss/web/jimeng/hot_keyword/manual)"},
            "item_id": {"type": "string", "description": "指定 item ID"},
        }
