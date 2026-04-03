"""model_service 模块单元测试 — ModelManager / ModelService ABC"""

from __future__ import annotations

import numpy as np
import pytest

from pipeline.model_service.base import ModelService
from pipeline.model_service.manager import ModelManager


class _DummyModel(ModelService):
    """测试用 ModelService 实现。"""

    def __init__(self, model_name: str = "test_model", ver: str = "1.0"):
        self._name = model_name
        self._ver = ver
        self._shutdown_called = False
        self._warmup_called = False

    def name(self) -> str:
        return self._name

    def version(self) -> str:
        return self._ver

    def predict(self, features: np.ndarray) -> np.ndarray:
        return np.ones(features.shape[0])

    def warmup(self) -> None:
        self._warmup_called = True

    def shutdown(self) -> None:
        self._shutdown_called = True


class TestModelServiceABC:
    def test_default_methods(self):
        m = _DummyModel()
        assert m.health_check() is True
        assert m.input_schema() == {}
        assert m.output_dim() == 1


class TestModelManager:
    @pytest.fixture
    def manager(self):
        return ModelManager()

    @pytest.fixture
    def model(self):
        return _DummyModel()

    def test_register_and_get(self, manager: ModelManager, model: _DummyModel):
        manager.register(model)
        assert manager.get("test_model") is model

    def test_get_missing_raises(self, manager: ModelManager):
        with pytest.raises(KeyError, match="不存在"):
            manager.get("no_such_model")

    def test_unregister(self, manager: ModelManager, model: _DummyModel):
        manager.register(model)
        manager.unregister("test_model")
        with pytest.raises(KeyError):
            manager.get("test_model")
        assert model._shutdown_called

    def test_reload(self, manager: ModelManager, model: _DummyModel):
        manager.register(model)
        new_model = _DummyModel(ver="2.0")
        manager.reload("test_model", new_model)
        assert manager.get("test_model").version() == "2.0"
        assert model._shutdown_called

    def test_predict(self, manager: ModelManager, model: _DummyModel):
        manager.register(model)
        features = np.random.rand(5, 10)
        result = manager.predict("test_model", features)
        assert result.shape == (5,)

    def test_warmup_all(self, manager: ModelManager):
        m1 = _DummyModel("a")
        m2 = _DummyModel("b")
        manager.register(m1)
        manager.register(m2)
        manager.warmup_all()
        assert m1._warmup_called
        assert m2._warmup_called

    def test_shutdown_all(self, manager: ModelManager):
        m1 = _DummyModel("a")
        m2 = _DummyModel("b")
        manager.register(m1)
        manager.register(m2)
        manager.shutdown_all()
        assert m1._shutdown_called
        assert m2._shutdown_called
        assert manager.list_models() == []

    def test_health_check(self, manager: ModelManager, model: _DummyModel):
        manager.register(model)
        health = manager.health_check()
        assert health["test_model"] is True

    def test_list_models(self, manager: ModelManager):
        manager.register(_DummyModel("rank", "1.0"))
        manager.register(_DummyModel("recall", "2.0"))
        models = manager.list_models()
        assert len(models) == 2
        names = {m["name"] for m in models}
        assert "rank" in names
        assert "recall" in names
