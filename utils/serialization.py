"""序列化工具 — JSON 封装"""

from __future__ import annotations

import json
from typing import Any


def to_json(obj: Any, **kwargs) -> str:
    """序列化为 JSON 字符串，支持 dataclass/Pydantic model。"""
    if hasattr(obj, "model_dump"):
        data = obj.model_dump()
    elif hasattr(obj, "__dict__"):
        data = _to_plain_dict(obj)
    else:
        data = obj
    return json.dumps(data, ensure_ascii=False, default=str, **kwargs)


def from_json(text: str) -> Any:
    """从 JSON 字符串反序列化。"""
    return json.loads(text)


def _to_plain_dict(obj: Any) -> Any:
    """递归转换为纯 dict/list/基本类型。"""
    if isinstance(obj, dict):
        return {k: _to_plain_dict(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_plain_dict(v) for v in obj]
    if hasattr(obj, "model_dump"):
        return _to_plain_dict(obj.model_dump())
    if hasattr(obj, "__dict__"):
        return _to_plain_dict(obj.__dict__)
    return obj
