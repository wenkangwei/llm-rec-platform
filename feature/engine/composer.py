"""特征组合器 — 将多源特征组装为模型输入"""

from __future__ import annotations

from typing import Any

from utils.logger import get_struct_logger

logger = get_struct_logger("feature.engine.composer")


# 特征组装顺序
_ASSEMBLY_ORDER = ["user", "item", "context", "cross"]


class FeatureComposer:
    """特征组合器：将散列特征组装为模型输入 tensor。"""

    def compose(self, features: dict[str, Any], schema: list[dict]) -> list[float]:
        """按 schema 顺序组装特征为 float 数组。"""
        result = []
        for field_def in schema:
            name = field_def["name"]
            dtype = field_def.get("dtype", "float")
            default = field_def.get("default", 0.0)
            dim = field_def.get("dimension", 1)

            value = features.get(name, default)
            if dtype == "array" and isinstance(value, (list, tuple)):
                result.extend([float(v) for v in value[:dim]])
            else:
                result.append(float(value))

        return result

    def compose_batch(self, features_list: list[dict], schema: list[dict]) -> list[list[float]]:
        """批量组装。"""
        return [self.compose(f, schema) for f in features_list]
