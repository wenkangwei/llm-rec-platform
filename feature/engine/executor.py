"""DSL 执行引擎 — 衍生特征实时计算"""

from __future__ import annotations

from typing import Any

from feature.engine.parser import parse_dsl
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.engine.executor")


class DSLExecutor:
    """衍生特征执行引擎。"""

    def compute(self, dsl: str, context: dict[str, Any]) -> Any:
        """执行 DSL 表达式。"""
        try:
            return parse_dsl(dsl, context)
        except Exception as e:
            logger.error(f"DSL 执行失败: {dsl}", error=str(e))
            return None

    def compute_batch(self, dsl: str, contexts: list[dict[str, Any]]) -> list[Any]:
        """批量执行 DSL。"""
        return [self.compute(dsl, ctx) for ctx in contexts]
