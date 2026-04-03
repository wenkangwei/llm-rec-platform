"""ContextProfile — 上下文画像"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class ContextProfile:
    """请求上下文画像。"""
    timestamp: datetime
    hour_of_day: int
    day_of_week: int
    device_type: str = "unknown"  # iOS/Android/Web
    scene: str = "home_feed"
    page_number: int = 0
