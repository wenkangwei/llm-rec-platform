"""配置加载器 — 图依赖解析 + 拓扑排序 + 引用替换"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

from utils.logger import get_struct_logger

logger = get_struct_logger("config_loader")

# 配置根目录
_CONFIG_ROOT = Path(__file__).parent

# 引用语法: ${path/to/file.yaml:key.nested.key} 或 ${env:VAR:default}
_PATH_REF_RE = re.compile(r"\$\{([^}:]+):([^}]+)\}")
_ENV_REF_RE = re.compile(r"\$\{env:([^:}]+)(?::([^}]*))?\}")


class ConfigLoadError(Exception):
    """配置加载异常。"""


def load_yaml(path: Path) -> dict[str, Any]:
    """加载单个 YAML 文件。"""
    if not path.exists():
        raise ConfigLoadError(f"配置文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def resolve_dep_graph(app_config: dict[str, Any]) -> list[Path]:
    """从 app.yaml 中解析依赖图，返回拓扑排序后的加载顺序。"""
    deps: dict[str, set[str]] = {}
    _scan_deps(app_config, "", deps)

    # 拓扑排序 (Kahn's algorithm)
    in_degree: dict[str, int] = {k: 0 for k in deps}
    for node, parents in deps.items():
        for p in parents:
            if p not in in_degree:
                in_degree[p] = 0
            in_degree[node] += 1

    queue = [n for n, d in in_degree.items() if d == 0]
    order: list[str] = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for child, parents in deps.items():
            if node in parents:
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

    if len(order) < len(in_degree):
        raise ConfigLoadError("配置依赖存在循环引用")

    return [_CONFIG_ROOT / p for p in order if (_CONFIG_ROOT / p).exists()]


def _scan_deps(data: Any, prefix: str, deps: dict[str, set[str]]) -> None:
    """递归扫描配置数据中的 ${path:key} 引用，构建依赖图。"""
    if isinstance(data, str):
        for match in _PATH_REF_RE.finditer(data):
            ref_path = match.group(1)
            # 提取配置文件路径（不含子key的部分）
            config_file = ref_path if ref_path.endswith(".yaml") else ref_path.split("/")[0] + "/" + ref_path.split("/")[1]
            if prefix not in deps:
                deps[prefix] = set()
            deps[prefix].add(config_file)
    elif isinstance(data, dict):
        for k, v in data.items():
            child_prefix = f"{prefix}.{k}" if prefix else k
            _scan_deps(v, child_prefix, deps)
    elif isinstance(data, list):
        for i, v in enumerate(data):
            _scan_deps(v, f"{prefix}[{i}]", deps)


class ConfigLoader:
    """配置加载器：加载 app.yaml → 解析依赖 → 拓扑排序 → 引用替换 → 环境覆盖。"""

    def __init__(self, config_root: Path | None = None, env: str = "development"):
        self._root = config_root or _CONFIG_ROOT
        self._env = env
        self._cache: dict[str, dict[str, Any]] = {}

    def load(self) -> dict[str, Any]:
        """加载完整配置。"""
        app_path = self._root / "app.yaml"
        app_config = load_yaml(app_path)

        # 加载环境覆盖
        env_path = self._root / "environments" / f"{self._env}.yaml"
        env_config = load_yaml(env_path) if env_path.exists() else {}

        # 深度合并环境覆盖
        merged = _deep_merge(app_config, env_config)

        # 解析引用
        resolved = self._resolve_refs(merged)

        return resolved

    def _resolve_refs(self, data: Any) -> Any:
        """递归解析 ${path:key} 和 ${env:VAR:default} 引用。"""
        if isinstance(data, str):
            # 如果整个字符串恰好是一个引用，保留原始类型（dict/list/int 等）
            path_match = _PATH_REF_RE.fullmatch(data.strip())
            if path_match:
                value = self._resolve_path_value(path_match)
                if value is not None and not isinstance(value, str):
                    return self._resolve_refs(value)
                if isinstance(value, str):
                    return value
            # 部分引用（字符串内嵌引用），替换为字符串
            data = _PATH_REF_RE.sub(self._resolve_path_ref, data)
            data = _ENV_REF_RE.sub(self._resolve_env_ref, data)
            return data
        if isinstance(data, dict):
            return {k: self._resolve_refs(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self._resolve_refs(v) for v in data]
        return data

    def _resolve_path_value(self, match: re.Match) -> Any:
        """解析路径引用，返回原始类型值。"""
        ref_path = match.group(1)
        ref_key = match.group(2)
        if ref_path not in self._cache:
            full_path = self._root / ref_path
            try:
                self._cache[ref_path] = load_yaml(full_path)
            except ConfigLoadError:
                logger.warning(f"引用的配置文件不存在: {ref_path}")
                return None
        return _get_nested(self._cache[ref_path], ref_key)

    def _resolve_path_ref(self, match: re.Match) -> str:
        """解析单个 ${path:key} 引用，返回字符串。"""
        value = self._resolve_path_value(match)
        return str(value) if value is not None else match.group(0)

    @staticmethod
    def _resolve_env_ref(match: re.Match) -> str:
        """解析单个 ${env:VAR:default} 引用。"""
        var_name = match.group(1)
        default = match.group(2) or ""
        return os.environ.get(var_name, default)


def _get_nested(data: dict[str, Any], key_path: str) -> Any:
    """通过点号路径获取嵌套值。"""
    keys = key_path.split(".")
    current = data
    for k in keys:
        if isinstance(current, dict) and k in current:
            current = current[k]
        else:
            return None
    return current


def _deep_merge(base: dict, override: dict) -> dict:
    """深度合并两个字典，override 覆盖 base。"""
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# 全局加载器实例
_loader: ConfigLoader | None = None


def init_config(env: str | None = None) -> dict[str, Any]:
    """初始化全局配置，返回完整配置字典。"""
    global _loader
    env = env or os.environ.get("APP_ENV", "development")
    _loader = ConfigLoader(env=env)
    config = _loader.load()
    logger.info(f"配置加载完成", env=env)
    return config


def get_config() -> dict[str, Any]:
    """获取当前配置。如果未初始化则使用默认配置。"""
    global _loader
    if _loader is None:
        return init_config()
    return _loader.load()
