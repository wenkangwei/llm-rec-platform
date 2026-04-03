"""settings / training_logger / model backends / model definitions 测试"""

from __future__ import annotations

import time

import numpy as np
import pytest

# ===== Settings =====

from configs.settings import _Settings, get_settings


class TestSettings:
    def test_get_settings_singleton(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_get_dot_path(self):
        s = _Settings()
        s._raw = {"storage": {"redis": {"host": "localhost", "port": 6379}}}
        assert s.get("storage.redis.host") == "localhost"
        assert s.get("storage.redis.port") == 6379

    def test_get_missing_path_returns_default(self):
        s = _Settings()
        s._raw = {"a": 1}
        assert s.get("b.c.d") is None
        assert s.get("b.c.d", "fallback") == "fallback"

    def test_get_non_dict_path(self):
        s = _Settings()
        s._raw = {"a": "not_a_dict"}
        assert s.get("a.b") is None


# ===== TrainingLogger =====

from monitor.training_logger import TrainingLogger


class TestTrainingLogger:
    @pytest.fixture
    def logger(self, tmp_path):
        return TrainingLogger(output_dir=str(tmp_path / "training"), flush_interval=3)

    @pytest.mark.asyncio
    async def test_log_and_flush(self, logger):
        await logger.log({"trace_id": "t1"})
        await logger.log({"trace_id": "t2"})
        assert len(logger._buffer) == 2

    @pytest.mark.asyncio
    async def test_auto_flush_at_threshold(self, logger, tmp_path):
        await logger.log({"trace_id": "t1"})
        await logger.log({"trace_id": "t2"})
        await logger.log({"trace_id": "t3"})  # triggers flush
        assert len(logger._buffer) == 0
        # Check file was created
        files = list((tmp_path / "training").glob("*.jsonl"))
        assert len(files) == 1
        lines = files[0].read_text().strip().split("\n")
        assert len(lines) == 3

    @pytest.mark.asyncio
    async def test_close_flushes_remaining(self, logger, tmp_path):
        await logger.log({"trace_id": "t1"})
        await logger.close()
        files = list((tmp_path / "training").glob("*.jsonl"))
        assert len(files) == 1
        lines = files[0].read_text().strip().split("\n")
        assert len(lines) == 1

    @pytest.mark.asyncio
    async def test_log_batch(self, logger):
        await logger.log_batch([{"id": i} for i in range(5)])
        assert len(logger._buffer) == 2  # 5 items, flush at 3, remaining 2

    @pytest.mark.asyncio
    async def test_backfill_labels(self, logger):
        await logger.backfill_labels("r1", "i1", {"action": "click"})
        assert len(logger._buffer) == 1
        assert logger._buffer[0]["type"] == "label_backfill"

    @pytest.mark.asyncio
    async def test_log_entry_has_timestamp(self, logger):
        await logger.log({"x": 1})
        assert "log_time" in logger._buffer[0]


# ===== Torch Backend =====

torch = pytest.importorskip("torch")
from pipeline.model_service.backends.torch_backend import TorchModel


class TestTorchModel:
    def test_name_version(self):
        m = TorchModel("test_model", "v2")
        assert m.name() == "test_model"
        assert m.version() == "v2"

    def test_warmup_no_file(self):
        m = TorchModel("test", model_path="/nonexistent/model.pt")
        m.warmup()  # should not raise
        assert m._model is None

    def test_predict_no_model(self):
        m = TorchModel("test")
        features = np.random.rand(3, 5)
        result = m.predict(features)
        assert result.shape == (3,)
        assert np.all(result == 0)

    def test_shutdown(self):
        m = TorchModel("test")
        m.shutdown()  # should not raise

    def test_health_check_no_model(self):
        m = TorchModel("test")
        assert m.health_check() is False

    def test_resolve_device_auto(self):
        device = TorchModel._resolve_device("auto")
        assert device in ("cpu", "cuda")

    def test_resolve_device_explicit(self):
        assert TorchModel._resolve_device("cpu") == "cpu"


# ===== ONNX Backend =====

from pipeline.model_service.backends.onnx_backend import ONNXModel


class TestONNXModel:
    def test_name_version(self):
        m = ONNXModel("onnx_test", "v1")
        assert m.name() == "onnx_test"
        assert m.version() == "v1"

    def test_warmup_no_file(self):
        m = ONNXModel("test", model_path="/nonexistent/model.onnx")
        m.warmup()  # should not raise
        assert m._session is None

    def test_predict_no_session(self):
        m = ONNXModel("test")
        features = np.random.rand(3, 5)
        result = m.predict(features)
        assert result.shape == (3,)
        assert np.all(result == 0)

    def test_shutdown(self):
        m = ONNXModel("test")
        m.shutdown()

    def test_health_check_no_session(self):
        assert ONNXModel("test").health_check() is False


# ===== TwoTower Model =====

from pipeline.model_service.models.two_tower import TwoTowerModel, UserTower, ItemTower


class TestTwoTowerModel:
    def test_name_version(self):
        m = TwoTowerModel()
        assert m.name() == "two_tower"
        assert m.version() == "v1"

    def test_encode_users_no_model(self):
        m = TwoTowerModel(output_dim=32)
        features = np.random.rand(2, 64)
        result = m.encode_users(features)
        assert result.shape == (2, 32)
        assert np.all(result == 0)

    def test_encode_items_no_model(self):
        m = TwoTowerModel(output_dim=32)
        features = np.random.rand(2, 64)
        result = m.encode_items(features)
        assert result.shape == (2, 32)

    @pytest.mark.skipif(not torch.cuda.is_available(), reason="needs warmup with torch")
    def test_warmup_and_predict(self):
        m = TwoTowerModel(input_dim=32, output_dim=16, device="cpu")
        m.warmup()
        features = np.random.rand(4, 32).astype(np.float32)
        result = m.predict(features)
        assert result.shape == (4, 16)

    def test_shutdown(self):
        m = TwoTowerModel()
        m.shutdown()

    def test_output_dim(self):
        m = TwoTowerModel(output_dim=32)
        assert m.output_dim() == 32


class TestUserTower:
    def test_forward(self):
        tower = UserTower(input_dim=32, hidden_dim=16, output_dim=8)
        x = torch.randn(3, 32)
        out = tower(x)
        assert out.shape == (3, 8)
        # normalized
        norms = out.norm(dim=-1)
        assert torch.allclose(norms, torch.ones(3), atol=1e-5)


class TestItemTower:
    def test_forward(self):
        tower = ItemTower(input_dim=32, hidden_dim=16, output_dim=8)
        x = torch.randn(3, 32)
        out = tower(x)
        assert out.shape == (3, 8)


# ===== DCN Model =====

from pipeline.model_service.models.dcn import DCNModel, CrossLayer


class TestDCNModel:
    def test_name_version(self):
        m = DCNModel()
        assert m.name() == "dcn"
        assert m.version() == "v1"

    def test_predict_no_model(self):
        m = DCNModel()
        features = np.random.rand(5, 256)
        result = m.predict(features)
        assert result.shape == (5,)
        assert np.all(result >= 0) and np.all(result <= 1)

    def test_warmup_and_predict(self):
        m = DCNModel(input_dim=32, device="cpu")
        m.warmup()
        features = np.random.rand(3, 32).astype(np.float32)
        result = m.predict(features)
        assert result.shape == (3,)
        assert np.all(result >= 0) and np.all(result <= 1)

    def test_shutdown(self):
        DCNModel().shutdown()


class TestCrossLayer:
    def test_forward(self):
        layer = CrossLayer(16)
        x0 = torch.randn(2, 16)
        xi = torch.randn(2, 16)
        out = layer(x0, xi)
        assert out.shape == (2, 16)


# ===== DIN Model =====

from pipeline.model_service.models.din import DINModel, AttentionLayer


class TestDINModel:
    def test_name_version(self):
        m = DINModel()
        assert m.name() == "din"
        assert m.version() == "v1"

    def test_predict_no_model(self):
        m = DINModel()
        features = np.random.rand(5, 128)
        result = m.predict(features)
        assert result.shape == (5,)

    def test_warmup_and_predict(self):
        m = DINModel(embedding_dim=16, device="cpu")
        m.warmup()
        # DIN forward splits features into item_emb + behavior_pool at half
        # Each half must be embedding_dim (16), so total input_dim = 32
        # Attention expects item: [B, D] and behavior: [B, T, D]
        # Forward unsqueezes both to [B, 1, D] which creates [B, T=1, D]
        features = np.random.rand(2, 32).astype(np.float32)
        result = m.predict(features)
        assert result.shape == (2,)
        assert np.all(result >= 0) and np.all(result <= 1)

    def test_shutdown(self):
        DINModel().shutdown()


class TestAttentionLayer:
    def test_forward(self):
        layer = AttentionLayer(embedding_dim=16, hidden_units=[32, 16])
        item = torch.randn(2, 16)
        behavior = torch.randn(2, 3, 16)
        out = layer(item, behavior)
        assert out.shape == (2, 16)


# ===== LightGBM Model =====

from pipeline.model_service.models.lightgbm_model import LightGBMModel


class TestLightGBMModel:
    def test_name_version(self):
        m = LightGBMModel()
        assert m.name() == "lightgbm"
        assert m.version() == "v1"

    def test_warmup_no_file(self):
        m = LightGBMModel(model_path="/nonexistent/model.txt")
        m.warmup()  # should not raise
        assert m._model is None

    def test_predict_no_model(self):
        m = LightGBMModel()
        features = np.random.rand(5, 10)
        result = m.predict(features)
        assert result.shape == (5,)

    def test_shutdown(self):
        LightGBMModel().shutdown()

    def test_health_check_always_true(self):
        m = LightGBMModel()
        assert m.health_check() is True
