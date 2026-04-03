"""Settings 单例 — 全局配置访问入口"""

from __future__ import annotations

from typing import Any, Optional

from configs.loader import ConfigLoader, init_config
from configs.schema import AppConfig, validate_config


class _Settings:
    """全局配置单例，延迟加载。"""

    def __init__(self):
        self._raw: dict[str, Any] = {}
        self._validated: Optional[AppConfig] = None

    def init(self, env: str | None = None) -> None:
        """初始化配置。"""
        self._raw = init_config(env)
        self._validated = validate_config(self._raw)

    @property
    def raw(self) -> dict[str, Any]:
        """原始配置字典。"""
        if not self._raw:
            self.init()
        return self._raw

    @property
    def validated(self) -> AppConfig:
        """校验后的配置对象。"""
        if self._validated is None:
            self.init()
        return self._validated

    @property
    def server(self):
        return self.validated.server

    @property
    def storage(self):
        return self.validated.storage

    @property
    def llm(self):
        return self.validated.llm

    @property
    def monitor(self):
        return self.validated.monitor

    def get(self, key_path: str, default: Any = None) -> Any:
        """通过点号路径获取配置值。

        Example: settings.get("storage.redis.host")
        """
        keys = key_path.split(".")
        current = self.raw
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        return current


# 全局单例
_settings: _Settings | None = None


def get_settings() -> _Settings:
    """获取全局 Settings 实例。"""
    global _settings
    if _settings is None:
        _settings = _Settings()
    return _settings
