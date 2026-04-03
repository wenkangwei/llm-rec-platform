"""特征存储基类"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FeatureStore(ABC):
    """特征存储抽象接口。"""

    @abstractmethod
    async def get(self, entity_id: str, feature_names: list[str]) -> dict[str, Any]:
        """获取实体的一组特征。"""

    @abstractmethod
    async def batch_get(self, entity_ids: list[str], feature_names: list[str]) -> list[dict[str, Any]]:
        """批量获取多个实体的特征。"""

    @abstractmethod
    async def set(self, entity_id: str, features: dict[str, Any], ttl: int | None = None) -> None:
        """设置实体特征。"""

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查。"""
