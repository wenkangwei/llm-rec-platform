"""configs 模块单元测试"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from configs.loader import (
    ConfigLoadError,
    ConfigLoader,
    _deep_merge,
    _get_nested,
    load_yaml,
    resolve_dep_graph,
)
from configs.schema import AppConfig, ServerConfig


class TestDeepMerge:
    """深度合并测试。"""

    def test_flat_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"db": {"host": "localhost", "port": 3306}}
        override = {"db": {"port": 3307, "user": "admin"}}
        result = _deep_merge(base, override)
        assert result == {"db": {"host": "localhost", "port": 3307, "user": "admin"}}

    def test_override_none(self):
        base = {"a": 1}
        result = _deep_merge(base, {})
        assert result == {"a": 1}


class TestGetNested:
    """嵌套取值测试。"""

    def test_simple(self):
        assert _get_nested({"a": 1}, "a") == 1

    def test_nested(self):
        assert _get_nested({"a": {"b": {"c": 3}}}, "a.b.c") == 3

    def test_missing_key(self):
        assert _get_nested({"a": 1}, "b") is None

    def test_partial_path(self):
        assert _get_nested({"a": {"b": 1}}, "a.c") is None


class TestLoadYaml:
    """YAML 加载测试。"""

    def test_load_existing(self, tmp_path: Path):
        f = tmp_path / "test.yaml"
        f.write_text("key: value\n")
        result = load_yaml(f)
        assert result == {"key": "value"}

    def test_load_missing(self, tmp_path: Path):
        with pytest.raises(ConfigLoadError):
            load_yaml(tmp_path / "missing.yaml")

    def test_load_empty(self, tmp_path: Path):
        f = tmp_path / "empty.yaml"
        f.write_text("")
        result = load_yaml(f)
        assert result == {}


class TestConfigLoader:
    """ConfigLoader 测试。"""

    def test_env_ref_resolution(self):
        loader = ConfigLoader()
        with patch.dict("os.environ", {"TEST_VAR": "hello"}):
            result = loader._resolve_refs("${env:TEST_VAR:default}")
            assert result == "hello"

    def test_env_ref_default(self):
        loader = ConfigLoader()
        result = loader._resolve_refs("${env:NONEXISTENT_VAR:default_val}")
        assert result == "default_val"

    def test_resolve_refs_dict(self):
        loader = ConfigLoader()
        data = {"key1": "plain", "key2": "${env:VAR:default}"}
        result = loader._resolve_refs(data)
        assert result["key1"] == "plain"
        assert result["key2"] == "default"

    def test_resolve_refs_list(self):
        loader = ConfigLoader()
        data = ["${env:X:1}", "${env:Y:2}"]
        result = loader._resolve_refs(data)
        assert result == ["1", "2"]


class TestAppConfig:
    """AppConfig Schema 测试。"""

    def test_default_config(self):
        config = AppConfig()
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8000

    def test_custom_server(self):
        config = AppConfig(server=ServerConfig(host="127.0.0.1", port=9000))
        assert config.server.host == "127.0.0.1"
        assert config.server.port == 9000
