"""DSL 解析器 — 特征计算表达式解析"""

from __future__ import annotations

import re
from typing import Any

from utils.logger import get_struct_logger

logger = get_struct_logger("feature.engine.parser")

# 支持的运算符
_OPERATORS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b if b != 0 else 0,
    "**": lambda a, b: a ** b,
    "%": lambda a, b: a % b,
}


def parse_dsl(expression: str, context: dict[str, Any]) -> Any:
    """解析并执行简单的 DSL 表达式。

    支持:
    - 算术: field1 + field2 * 0.5
    - 函数: time_decay(field, 0.95)
    - 字面量: 3.14
    - 变量引用: ${user.age}
    """
    # 先尝试解析字面量
    try:
        return float(expression)
    except ValueError:
        pass

    try:
        return int(expression)
    except ValueError:
        pass

    if expression in context:
        return context[expression]

    # 函数调用: func_name(arg1, arg2, ...)
    func_match = re.match(r"(\w+)\(([^)]+)\)", expression)
    if func_match:
        return _eval_function(func_match.group(1), func_match.group(2), context)

    # 简单算术表达式
    tokens = expression.split()
    if len(tokens) == 3 and tokens[1] in _OPERATORS:
        left = _eval_simple(tokens[0], tokens[1], tokens[2], context)
        if left is not None:
            return left

    return expression


def _eval_function(name: str, args_str: str, context: dict[str, Any]) -> Any:
    """执行内置函数。"""
    import math

    args = [parse_dsl(a.strip(), context) for a in args_str.split(",")]
    functions = {
        "time_decay": lambda val, decay: val * (float(decay)),
        "bucketize": lambda val, boundaries: _bucketize(val, boundaries),
        "normalize": lambda val: val,
        "hash_encode": lambda val: hash(str(val)),
        "sigmoid": lambda val: 1 / (1 + math.exp(-val)),
    }

    func = functions.get(name)
    if func:
        return func(*args)
    return None


def _eval_simple(left: str, op: str, right: str, context: dict[str, Any]) -> Any:
    """简单算术。"""
    l = parse_dsl(left, context)
    r = parse_dsl(right, context)
    if l is not None and r is not None:
        return _OPERATORS[op](l, r)
    return None


def _bucketize(value: float, boundaries: Any) -> int:
    """分桶。"""
    if isinstance(boundaries, str):
        boundaries = [float(x) for x in boundaries.split(",")]
    for i, b in enumerate(boundaries):
        if value < b:
            return i
    return len(boundaries)
