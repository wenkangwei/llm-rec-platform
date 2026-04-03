"""对话消息/意图/动作数据结构"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class IntentType(str, Enum):
    STRATEGY = "strategy"       # 策略控制
    MONITOR = "monitor"         # 监控查询
    DEBUG = "debug"             # 调试诊断
    CONFIG = "config"           # 配置管理
    UNKNOWN = "unknown"         # 未识别


@dataclass
class ChatMessage:
    """对话消息。"""
    role: str  # user / assistant / system
    content: str
    timestamp: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Intent:
    """识别出的意图。"""
    type: IntentType
    confidence: float = 0.0
    entities: dict[str, Any] = field(default_factory=dict)  # 提取的实体


@dataclass
class ChatAction:
    """对话触发的动作。"""
    tool_name: str
    params: dict[str, Any]
    result: Any = None
    success: bool = False


@dataclass
class ChatSession:
    """对话会话。"""
    session_id: str
    user_id: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0
