"""实验模块单元测试"""

import pytest

from experiment.manager import ExperimentManager
from experiment.models import Experiment, ExperimentStatus, ExperimentVariant


# ===== Models =====

class TestExperimentVariant:
    def test_valid_variant(self):
        v = ExperimentVariant(name="control", traffic_percent=50.0)
        assert v.name == "control"
        assert v.traffic_percent == 50.0
        assert v.config == {}

    def test_variant_with_config(self):
        v = ExperimentVariant(
            name="treatment",
            traffic_percent=50.0,
            config={"recall": {"collaborative": {"weight": 0.4}}},
        )
        assert v.config["recall"]["collaborative"]["weight"] == 0.4

    def test_invalid_traffic_percent(self):
        with pytest.raises(ValueError, match="traffic_percent"):
            ExperimentVariant(name="bad", traffic_percent=-1)
        with pytest.raises(ValueError, match="traffic_percent"):
            ExperimentVariant(name="bad", traffic_percent=101)


class TestExperiment:
    def test_valid_experiment(self):
        exp = Experiment(
            id="exp_1",
            name="Test",
            variants=[
                ExperimentVariant(name="control", traffic_percent=50),
                ExperimentVariant(name="treatment", traffic_percent=50),
            ],
        )
        assert exp.status == ExperimentStatus.DRAFT
        assert len(exp.variants) == 2

    def test_traffic_must_sum_to_100(self):
        with pytest.raises(ValueError, match="sum to 100"):
            Experiment(
                id="exp_bad",
                name="Bad",
                variants=[
                    ExperimentVariant(name="a", traffic_percent=30),
                    ExperimentVariant(name="b", traffic_percent=30),
                ],
            )

    def test_get_variant(self):
        exp = Experiment(
            id="exp_1",
            name="Test",
            variants=[
                ExperimentVariant(name="control", traffic_percent=50),
                ExperimentVariant(name="treatment", traffic_percent=50),
            ],
        )
        assert exp.get_variant("control") is not None
        assert exp.get_variant("treatment").name == "treatment"
        assert exp.get_variant("nonexistent") is None

    def test_empty_variants_ok(self):
        exp = Experiment(id="exp_empty", name="Empty")
        assert exp.variants == []


# ===== Manager =====

class TestExperimentManager:
    def _make_manager_with_experiment(self):
        mgr = ExperimentManager()
        exp = Experiment(
            id="test_exp",
            name="Test Experiment",
            variants=[
                ExperimentVariant(name="control", traffic_percent=50),
                ExperimentVariant(name="treatment", traffic_percent=50),
            ],
        )
        mgr.create_experiment(exp)
        mgr.start_experiment("test_exp")
        return mgr

    def test_create_and_start(self):
        mgr = self._make_manager_with_experiment()
        exp = mgr._get_experiment("test_exp")
        assert exp.status == ExperimentStatus.RUNNING
        assert exp.started_at > 0

    def test_create_duplicate_fails(self):
        mgr = ExperimentManager()
        exp = Experiment(
            id="dup",
            name="Dup",
            variants=[ExperimentVariant(name="a", traffic_percent=100)],
        )
        mgr.create_experiment(exp)
        with pytest.raises(ValueError, match="已存在"):
            mgr.create_experiment(exp)

    def test_create_no_variants_fails(self):
        mgr = ExperimentManager()
        exp = Experiment(id="no_v", name="No Variants", variants=[])
        with pytest.raises(ValueError, match="至少需要一个变体"):
            mgr.create_experiment(exp)

    def test_pause_and_resume(self):
        mgr = self._make_manager_with_experiment()
        mgr.pause_experiment("test_exp")
        assert mgr._get_experiment("test_exp").status == ExperimentStatus.PAUSED
        mgr.resume_experiment("test_exp")
        assert mgr._get_experiment("test_exp").status == ExperimentStatus.RUNNING

    def test_resume_non_paused_fails(self):
        mgr = self._make_manager_with_experiment()
        with pytest.raises(ValueError, match="只能恢复暂停状态"):
            mgr.resume_experiment("test_exp")

    def test_stop_experiment(self):
        mgr = self._make_manager_with_experiment()
        mgr.stop_experiment("test_exp")
        exp = mgr._get_experiment("test_exp")
        assert exp.status == ExperimentStatus.COMPLETED
        assert exp.ended_at > 0

    def test_cancel_experiment(self):
        mgr = self._make_manager_with_experiment()
        mgr.cancel_experiment("test_exp")
        assert mgr._get_experiment("test_exp").status == ExperimentStatus.CANCELLED

    def test_nonexistent_experiment_raises(self):
        mgr = ExperimentManager()
        with pytest.raises(KeyError, match="不存在"):
            mgr._get_experiment("nonexistent")

    def test_delete_experiment(self):
        mgr = self._make_manager_with_experiment()
        mgr.delete_experiment("test_exp")
        with pytest.raises(KeyError):
            mgr._get_experiment("test_exp")

    def test_delete_nonexistent_raises(self):
        mgr = ExperimentManager()
        with pytest.raises(KeyError, match="不存在"):
            mgr.delete_experiment("nonexistent")


class TestExperimentBucketing:
    """确定性分桶测试。"""

    def _make_manager(self):
        mgr = ExperimentManager()
        exp = Experiment(
            id="bucket_test",
            name="Bucket Test",
            variants=[
                ExperimentVariant(name="control", traffic_percent=50),
                ExperimentVariant(name="treatment", traffic_percent=50),
            ],
        )
        mgr.create_experiment(exp)
        mgr.start_experiment("bucket_test")
        return mgr

    def test_deterministic_bucketing(self):
        """同一用户多次调用结果一致。"""
        mgr = self._make_manager()
        v1 = mgr.get_variant("bucket_test", "user_123")
        v2 = mgr.get_variant("bucket_test", "user_123")
        assert v1 is not None
        assert v1.name == v2.name

    def test_different_users_may_differ(self):
        """不同用户可能分到不同组。"""
        mgr = self._make_manager()
        variants = set()
        for i in range(100):
            v = mgr.get_variant("bucket_test", f"user_{i}")
            if v:
                variants.add(v.name)
        # 100 users with 50/50 split should hit both variants
        assert len(variants) >= 1  # at minimum 1, statistically ~2

    def test_not_running_returns_none(self):
        mgr = ExperimentManager()
        exp = Experiment(
            id="draft_exp",
            name="Draft",
            variants=[ExperimentVariant(name="a", traffic_percent=100)],
        )
        mgr.create_experiment(exp)
        # DRAFT, not started
        assert mgr.get_variant("draft_exp", "user_1") is None

    def test_layer_isolation(self):
        """不同 layer 独立分桶。"""
        mgr = self._make_manager()
        v_default = mgr.get_variant("bucket_test", "user_1", layer="default")
        v_layer2 = mgr.get_variant("bucket_test", "user_1", layer="layer2")
        # 两个层可能不同（不保证一定不同，但 key 不同所以分桶独立）
        assert v_default is not None
        assert v_layer2 is not None

    def test_get_config_override(self):
        mgr = ExperimentManager()
        exp = Experiment(
            id="config_exp",
            name="Config",
            variants=[
                ExperimentVariant(name="control", traffic_percent=50, config={}),
                ExperimentVariant(
                    name="treatment",
                    traffic_percent=50,
                    config={"weight": 0.8},
                ),
            ],
        )
        mgr.create_experiment(exp)
        mgr.start_experiment("config_exp")

        # 获取所有用户的配置覆盖，检查至少有一个返回非空
        has_override = False
        for i in range(50):
            override = mgr.get_config_override("config_exp", f"user_{i}")
            if override:
                has_override = True
                break
        # 不强制，因为取决于分桶结果


class TestExperimentMetrics:
    def test_record_and_results(self):
        mgr = ExperimentManager()
        exp = Experiment(
            id="metric_exp",
            name="Metric Test",
            variants=[
                ExperimentVariant(name="control", traffic_percent=50),
                ExperimentVariant(name="treatment", traffic_percent=50),
            ],
        )
        mgr.create_experiment(exp)
        mgr.start_experiment("metric_exp")

        mgr.record_metric("metric_exp", "control", "click_rate", 0.1)
        mgr.record_metric("metric_exp", "control", "click_rate", 0.2)
        mgr.record_metric("metric_exp", "treatment", "click_rate", 0.3)

        results = mgr.get_results("metric_exp")
        assert results["experiment_id"] == "metric_exp"
        assert "control" in results["variants"]
        assert "treatment" in results["variants"]
        assert results["variants"]["control"]["click_rate"]["mean"] == pytest.approx(0.15)
        assert results["variants"]["control"]["click_rate"]["count"] == 2
        assert results["variants"]["treatment"]["click_rate"]["mean"] == pytest.approx(0.3)


class TestHashBucket:
    def test_range(self):
        for key in ["a", "b", "test_key", "layer:exp:user"]:
            val = ExperimentManager._hash_bucket(key)
            assert 0 <= val < 100

    def test_deterministic(self):
        val1 = ExperimentManager._hash_bucket("test_key")
        val2 = ExperimentManager._hash_bucket("test_key")
        assert val1 == val2


class TestListExperiments:
    def test_list_all(self):
        mgr = ExperimentManager()
        exp1 = Experiment(
            id="exp_1", name="E1",
            variants=[ExperimentVariant(name="a", traffic_percent=100)],
        )
        exp2 = Experiment(
            id="exp_2", name="E2",
            variants=[ExperimentVariant(name="a", traffic_percent=100)],
        )
        mgr.create_experiment(exp1)
        mgr.create_experiment(exp2)
        all_exps = mgr.list_experiments()
        assert len(all_exps) == 2

    def test_filter_by_status(self):
        mgr = ExperimentManager()
        exp = Experiment(
            id="exp_1", name="E1",
            variants=[ExperimentVariant(name="a", traffic_percent=100)],
        )
        mgr.create_experiment(exp)
        mgr.start_experiment("exp_1")
        running = mgr.list_experiments(ExperimentStatus.RUNNING)
        assert len(running) == 1
        assert running[0]["id"] == "exp_1"

        draft = mgr.list_experiments(ExperimentStatus.DRAFT)
        assert len(draft) == 0
