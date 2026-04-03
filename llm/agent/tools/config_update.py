"""配置更新工具"""

from __future__ import annotations

from typing import Any

from llm.agent.base import Tool
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.agent.tools.config")


class ConfigUpdateTool(Tool):
    """配置热更新工具：修改运行时配置。"""

    def __init__(self, config_state: dict[str, Any] | None = None):
        self._config = config_state or {}

    def name(self) -> str:
        return "config_update"

    def description(self) -> str:
        return "更新推荐系统运行时配置：切换模型版本、修改排序参数。参数: key(配置路径), value(新值)"

    async def execute(self, params: dict[str, Any]) -> Any:
        key = params.get("key", "")
        value = params.get("value")

        if not key:
            return {"error": "缺少 key 参数"}

        # 解析路径并更新
        keys = key.split(".")
        current = self._config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        old_value = current.get(keys[-1])
        current[keys[-1]] = value

        logger.info(f"配置更新: {key}", old=old_value, new=value)
        return {
            "success": True,
            "key": key,
            "old_value": old_value,
            "new_value": value,
        }

    def schema(self) -> dict:
        return {
            "key": {"type": "string", "description": "配置路径，如 models.rank.version"},
            "value": {"type": "any", "description": "新值"},
        }
