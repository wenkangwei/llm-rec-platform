"""DSL 解析器 — 特征计算表达式解析"""

from __future__ import annotations

import math
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


def _split_args(args_str: str) -> list[str]:
    """按逗号分割参数，但保留引号内的逗号。"""
    parts = []
    current = []
    in_quote = None
    paren_depth = 0
    for ch in args_str:
        if ch in ('"', "'") and paren_depth == 0:
            if in_quote == ch:
                in_quote = None
            elif in_quote is None:
                in_quote = ch
            current.append(ch)
        elif ch == '(' and in_quote is None:
            paren_depth += 1
            current.append(ch)
        elif ch == ')' and in_quote is None:
            paren_depth -= 1
            current.append(ch)
        elif ch == ',' and in_quote is None and paren_depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


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

    # 字符串字面量（引号包裹）
    if len(expression) >= 2 and expression[0] in ('"', "'") and expression[-1] == expression[0]:
        return expression[1:-1]

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

    args = [parse_dsl(a.strip(), context) for a in _split_args(args_str)]
    functions = {
        # 原有 5 个
        "time_decay": lambda val, decay: val * (float(decay)),
        "bucketize": lambda val, boundaries: _bucketize(val, boundaries),
        "normalize": lambda val: val,
        "hash_encode": lambda val: hash(str(val)),
        "sigmoid": lambda val: 1 / (1 + math.exp(-val)),
        # 条件函数
        "if": lambda cond, true_val, false_val: true_val if cond else false_val,
        "case": lambda *case_args: _case_function(*case_args),
        # 聚合函数
        "sum": lambda *vals: sum(float(v) for v in vals),
        "avg": lambda *vals: sum(float(v) for v in vals) / len(vals) if vals else 0,
        "max": lambda *vals: max(float(v) for v in vals) if vals else 0,
        "min": lambda *vals: min(float(v) for v in vals) if vals else 0,
        # 向量/交叉函数
        "dot": lambda a, b: sum(x * y for x, y in zip(a, b)),
        "cosine_sim": lambda a, b: _cosine_sim(a, b),
        # 字符串函数
        "split": lambda val, sep=" ": str(val).split(sep),
        "contains": lambda val, sub: str(sub) in str(val),
        "len": lambda val: len(val),
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


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """余弦相似度。"""
    dot_val = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_val / (norm_a * norm_b)


def _case_function(*args) -> Any:
    """case(cond1, val1, cond2, val2, ..., default) — 依次判断条件，返回第一个为真对应的值。"""
    i = 0
    while i + 1 < len(args):
        cond = args[i]
        val = args[i + 1]
        if cond:
            return val
        i += 2
    # 奇数参数最后一个是 default
    if len(args) % 2 == 1:
        return args[-1]
    return None
