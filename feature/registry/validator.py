"""特征校验器 — 校验特征值类型和范围"""

from __future__ import annotations

from typing import Any

from feature.registry.feature_def import FeatureDef
from utils.logger import get_struct_logger

logger = get_struct_logger("feature.validator")


class FeatureValidator:
    """特征值校验器。"""

    @staticmethod
    def validate(feature: FeatureDef, value: Any) -> bool:
        """校验特征值是否合法。"""
        if value is None:
            return True  # None 允许（表示缺失）

        type_checks = {
            "int": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "float": lambda v: isinstance(v, (int, float)),
            "string": lambda v: isinstance(v, str),
            "array": lambda v: isinstance(v, (list, tuple)),
            "map": lambda v: isinstance(v, dict),
        }

        check = type_checks.get(feature.dtype)
        if check and not check(value):
            logger.warning(
                f"特征类型不匹配: {feature.name}",
                expected=feature.dtype,
                actual=type(value).__name__,
            )
            return False

        return True

    @staticmethod
    def validate_batch(feature: FeatureDef, values: list[Any]) -> list[bool]:
        """批量校验。"""
        return [FeatureValidator.validate(feature, v) for v in values]
