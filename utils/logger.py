"""统一日志工具 — 结构化日志"""

from __future__ import annotations

import logging
import sys
from typing import Any


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """获取命名 logger，统一配置格式和输出。"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger


class LogAdapter:
    """结构化日志适配器，支持 key-value 附加字段。"""

    def __init__(self, logger: logging.Logger, extra: dict[str, Any] | None = None):
        self._logger = logger
        self._extra = extra or {}

    def _log(self, level: int, msg: str, **kwargs: Any) -> None:
        merged = {**self._extra, **kwargs}
        extra_str = " | ".join(f"{k}={v}" for k, v in merged.items()) if merged else ""
        full_msg = f"{msg} | {extra_str}" if extra_str else msg
        self._logger.log(level, full_msg)

    def bind(self, **kwargs: Any) -> LogAdapter:
        """绑定上下文字段，返回新实例。"""
        return LogAdapter(self._logger, {**self._extra, **kwargs})

    def info(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, **kwargs)

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, msg, **kwargs)


def get_struct_logger(name: str) -> LogAdapter:
    """获取结构化日志适配器。"""
    return LogAdapter(get_logger(name))
