"""feature 模块测试 — registry / store / engine"""

from __future__ import annotations

import math
import time

import pytest

from feature.registry.feature_def import FeatureDef, FeatureSource, FeatureStatus, ValueType
from feature.registry.group_def import FeatureGroupDef
from feature.registry.registry import FeatureRegistry
from feature.registry.lineage import FeatureLineage
from feature.registry.validator import FeatureValidator
from feature.store.context_store import ContextFeatureStore
from feature.store.router import StoreRouter
from feature.engine.parser import parse_dsl, _bucketize
from feature.engine.executor import DSLExecutor
from feature.engine.composer import FeatureComposer
from feature.engine.cache import FeatureCache


# ===== FeatureDef =====

class TestFeatureDef:
    def test_defaults(self):
        fd = FeatureDef(slot_id="s1", name="age")
        assert fd.slot_id == "s1"
        assert fd.name == "age"
        assert fd.dtype == "float"
        assert fd.source == FeatureSource.REDIS
        assert fd.status == FeatureStatus.ACTIVE
        assert fd.version == "v1"
        assert fd.composite_of == []
        assert fd.depends_on == []

    def test_all_fields(self):
        fd = FeatureDef(
            slot_id="s2", name="price", dtype="int",
            value_type=ValueType.SCALAR, dimension=1,
            source=FeatureSource.MYSQL, status=FeatureStatus.DRAFT,
            description="item price", owner="rec-team",
        )
        assert fd.dtype == "int"
        assert fd.source == FeatureSource.MYSQL
        assert fd.status == FeatureStatus.DRAFT

    def test_separate_instances_have_separate_lists(self):
        fd1 = FeatureDef(slot_id="s1", name="a")
        fd2 = FeatureDef(slot_id="s2", name="b")
        fd1.depends_on.append("x")
        assert fd2.depends_on == []


# ===== FeatureGroupDef =====

class TestFeatureGroupDef:
    def test_defaults(self):
        gd = FeatureGroupDef(name="user_basic", entity_type="user")
        assert gd.features == []
        assert gd.description == ""

    def test_get_feature(self):
        fd = FeatureDef(slot_id="s1", name="age")
        gd = FeatureGroupDef(name="g1", entity_type="user", features=[fd])
        assert gd.get_feature("age") is fd
        assert gd.get_feature("nonexistent") is None

    def test_get_active_features(self):
        fd1 = FeatureDef(slot_id="s1", name="active_feat", status=FeatureStatus.ACTIVE)
        fd2 = FeatureDef(slot_id="s2", name="draft_feat", status=FeatureStatus.DRAFT)
        gd = FeatureGroupDef(name="g1", entity_type="user", features=[fd1, fd2])
        active = gd.get_active_features()
        assert len(active) == 1
        assert active[0].name == "active_feat"

    def test_add_feature(self):
        gd = FeatureGroupDef(name="g1", entity_type="user")
        fd = FeatureDef(slot_id="s1", name="age")
        gd.add_feature(fd)
        assert len(gd.features) == 1


# ===== FeatureRegistry =====

class TestFeatureRegistry:
    @pytest.fixture
    def registry(self):
        return FeatureRegistry()

    def test_register_and_get(self, registry):
        fd = FeatureDef(slot_id="s1", name="age")
        registry.register(fd)
        assert registry.get("age") is fd

    def test_get_by_slot_id(self, registry):
        fd = FeatureDef(slot_id="s1", name="age")
        registry.register(fd)
        assert registry.get("s1") is fd

    def test_get_missing(self, registry):
        assert registry.get("nonexistent") is None

    def test_unregister(self, registry):
        fd = FeatureDef(slot_id="s1", name="age")
        registry.register(fd)
        registry.unregister("age")
        assert registry.get("age") is None

    def test_unregister_nonexistent_no_error(self, registry):
        registry.unregister("nonexistent")  # should not raise

    def test_register_group(self, registry):
        fd1 = FeatureDef(slot_id="s1", name="age")
        fd2 = FeatureDef(slot_id="s2", name="gender")
        group = FeatureGroupDef(name="user_basic", entity_type="user", features=[fd1, fd2])
        registry.register_group(group)
        assert registry.get("age") is fd1
        assert registry.get("gender") is fd2
        assert "user_basic" in registry.list_groups()

    def test_get_group(self, registry):
        group = FeatureGroupDef(name="g1", entity_type="user")
        registry.register_group(group)
        assert registry.get_group("g1") is group
        assert registry.get_group("missing") is None

    def test_get_by_source(self, registry):
        fd1 = FeatureDef(slot_id="s1", name="a", source=FeatureSource.REDIS)
        fd2 = FeatureDef(slot_id="s2", name="b", source=FeatureSource.MYSQL)
        registry.register(fd1)
        registry.register(fd2)
        redis_feats = registry.get_by_source(FeatureSource.REDIS)
        assert len(redis_feats) == 1
        assert redis_feats[0].name == "a"

    def test_get_active_features(self, registry):
        fd1 = FeatureDef(slot_id="s1", name="a", status=FeatureStatus.ACTIVE)
        fd2 = FeatureDef(slot_id="s2", name="b", status=FeatureStatus.DEPRECATED)
        registry.register(fd1)
        registry.register(fd2)
        active = registry.get_active_features()
        assert len(active) == 1

    def test_list_all(self, registry):
        fd1 = FeatureDef(slot_id="s1", name="a")
        fd2 = FeatureDef(slot_id="s2", name="b")
        registry.register(fd1)
        registry.register(fd2)
        assert len(registry.list_all()) == 2

    def test_load_from_config(self, registry):
        config = {
            "user_basic": {
                "fields": [{"name": "age"}, {"name": "gender", "dtype": "string"}],
                "type": "user",
                "source": "redis",
            }
        }
        registry.load_from_config(config)
        assert registry.get("age") is not None
        assert registry.get("gender") is not None
        assert registry.get("age").source == FeatureSource.REDIS
        assert registry.get("gender").dtype == "string"


# ===== FeatureLineage =====

class TestFeatureLineage:
    @pytest.fixture
    def lineage(self):
        reg = FeatureRegistry()
        fd1 = FeatureDef(slot_id="s1", name="raw_age")
        fd2 = FeatureDef(slot_id="s2", name="norm_age", depends_on=["raw_age"])
        fd3 = FeatureDef(slot_id="s3", name="age_bucket", depends_on=["norm_age"])
        fd1.depended_by = ["norm_age"]
        fd2.depended_by = ["age_bucket"]
        reg.register(fd1)
        reg.register(fd2)
        reg.register(fd3)
        return FeatureLineage(reg)

    def test_get_upstream(self, lineage):
        upstream = lineage.get_upstream("age_bucket")
        names = [f.name for f in upstream]
        assert "norm_age" in names
        assert "raw_age" in names

    def test_get_downstream(self, lineage):
        downstream = lineage.get_downstream("raw_age")
        names = [f.name for f in downstream]
        assert "norm_age" in names
        assert "age_bucket" in names

    def test_impact_analysis_low_risk(self, lineage):
        report = lineage.impact_analysis("norm_age")
        assert report.feature_name == "norm_age"
        assert report.risk_level == "low"

    def test_impact_analysis_high_risk(self):
        reg = FeatureRegistry()
        fd = FeatureDef(slot_id="s1", name="root")
        fd.depended_by = [f"child_{i}" for i in range(5)]
        reg.register(fd)
        for i in range(5):
            reg.register(FeatureDef(slot_id=f"c{i}", name=f"child_{i}", depends_on=["root"]))
        lineage = FeatureLineage(reg)
        report = lineage.impact_analysis("root")
        assert report.risk_level == "high"

    def test_missing_feature_returns_empty(self, lineage):
        assert lineage.get_upstream("nonexistent") == []
        assert lineage.get_downstream("nonexistent") == []


# ===== FeatureValidator =====

class TestFeatureValidator:
    def test_none_always_valid(self):
        fd = FeatureDef(slot_id="s1", name="x", dtype="int")
        assert FeatureValidator.validate(fd, None) is True

    def test_int_rejects_bool(self):
        fd = FeatureDef(slot_id="s1", name="x", dtype="int")
        assert FeatureValidator.validate(fd, True) is False
        assert FeatureValidator.validate(fd, 42) is True

    def test_float_allows_int(self):
        fd = FeatureDef(slot_id="s1", name="x", dtype="float")
        assert FeatureValidator.validate(fd, 3.14) is True
        assert FeatureValidator.validate(fd, 42) is True

    def test_string(self):
        fd = FeatureDef(slot_id="s1", name="x", dtype="string")
        assert FeatureValidator.validate(fd, "hello") is True
        assert FeatureValidator.validate(fd, 42) is False

    def test_array(self):
        fd = FeatureDef(slot_id="s1", name="x", dtype="array")
        assert FeatureValidator.validate(fd, [1, 2]) is True
        assert FeatureValidator.validate(fd, (1, 2)) is True
        assert FeatureValidator.validate(fd, "str") is False

    def test_map(self):
        fd = FeatureDef(slot_id="s1", name="x", dtype="map")
        assert FeatureValidator.validate(fd, {"a": 1}) is True
        assert FeatureValidator.validate(fd, [1]) is False

    def test_unknown_dtype_passes(self):
        fd = FeatureDef(slot_id="s1", name="x", dtype="custom")
        assert FeatureValidator.validate(fd, "anything") is True

    def test_validate_batch(self):
        fd = FeatureDef(slot_id="s1", name="x", dtype="int")
        results = FeatureValidator.validate_batch(fd, [1, "bad", None])
        assert results == [True, False, True]


# ===== ContextFeatureStore =====

class TestContextFeatureStore:
    @pytest.fixture
    def store(self):
        return ContextFeatureStore()

    @pytest.mark.asyncio
    async def test_get(self, store):
        result = await store.get("u1", ["hour_of_day", "is_weekend"])
        assert "hour_of_day" in result
        assert "is_weekend" in result
        assert "timestamp" not in result

    @pytest.mark.asyncio
    async def test_get_empty_names(self, store):
        result = await store.get("u1", [])
        assert result == {}

    @pytest.mark.asyncio
    async def test_batch_get(self, store):
        results = await store.batch_get(["u1", "u2"], ["hour_of_day"])
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_set_noop(self, store):
        await store.set("u1", {"k": "v"})  # should not raise

    @pytest.mark.asyncio
    async def test_health_check(self, store):
        assert await store.health_check() is True


# ===== StoreRouter =====

class TestStoreRouter:
    @pytest.fixture
    def router(self):
        reg = FeatureRegistry()
        reg.register(FeatureDef(slot_id="s1", name="age", source=FeatureSource.REDIS))
        reg.register(FeatureDef(slot_id="s2", name="title", source=FeatureSource.MYSQL))
        router = StoreRouter(reg)
        return router

    def test_register_store_and_route(self, router):
        store = ContextFeatureStore()
        router.register_store(FeatureSource.REDIS, store)
        assert router.route("age") is store

    def test_route_unknown_feature(self, router):
        assert router.route("nonexistent") is None

    def test_route_no_store_registered(self, router):
        assert router.route("age") is None

    @pytest.mark.asyncio
    async def test_get_features(self, router):
        router.register_store(FeatureSource.CONTEXT, ContextFeatureStore())
        reg = router._registry
        reg.register(FeatureDef(slot_id="ctx1", name="hour_of_day", source=FeatureSource.CONTEXT))
        result = await router.get_features("u1", ["hour_of_day"])
        assert "hour_of_day" in result

    @pytest.mark.asyncio
    async def test_get_features_store_error_graceful(self, router):
        class FailStore(ContextFeatureStore):
            async def get(self, entity_id, feature_names):
                raise RuntimeError("boom")

        router.register_store(FeatureSource.REDIS, FailStore())
        result = await router.get_features("u1", ["age"])
        assert result == {}

    @pytest.mark.asyncio
    async def test_batch_get_features(self, router):
        router.register_store(FeatureSource.CONTEXT, ContextFeatureStore())
        router._registry.register(
            FeatureDef(slot_id="ctx1", name="hour_of_day", source=FeatureSource.CONTEXT)
        )
        results = await router.batch_get_features(["u1", "u2"], ["hour_of_day"])
        assert len(results) == 2


# ===== DSL Parser =====

class TestParseDSL:
    def test_float_literal(self):
        assert parse_dsl("3.14", {}) == 3.14

    def test_int_literal(self):
        assert parse_dsl("42", {}) == 42

    def test_context_var(self):
        assert parse_dsl("age", {"age": 25}) == 25

    def test_arithmetic_add(self):
        assert parse_dsl("10 + 5", {}) == 15

    def test_arithmetic_div_by_zero(self):
        assert parse_dsl("10 / 0", {}) == 0

    def test_function_time_decay(self):
        result = parse_dsl("time_decay(100, 0.9)", {})
        assert result == pytest.approx(90.0)

    def test_function_sigmoid(self):
        result = parse_dsl("sigmoid(0)", {})
        assert result == pytest.approx(0.5)

    def test_function_normalize(self):
        assert parse_dsl("normalize(42)", {}) == 42

    def test_function_bucketize(self):
        # bucketize(val, boundaries) — boundaries resolved from context as a list
        result = parse_dsl("bucketize(15, bounds)", {"bounds": [10, 20, 30]})
        assert result == 1  # 15 < 20, index 1

    def test_unknown_function(self):
        assert parse_dsl("unknown_func(1)", {}) is None

    def test_unknown_expression_returns_raw(self):
        assert parse_dsl("some_raw_string", {}) == "some_raw_string"

    def test_bucketize_direct(self):
        assert _bucketize(5, [10, 20, 30]) == 0
        assert _bucketize(15, [10, 20, 30]) == 1
        assert _bucketize(25, [10, 20, 30]) == 2
        assert _bucketize(35, [10, 20, 30]) == 3

    def test_bucketize_string_boundaries(self):
        assert _bucketize(15, "10,20,30") == 1

    def test_arithmetic_with_context(self):
        assert parse_dsl("price * 2", {"price": 50}) == 100


# ===== DSLExecutor =====

class TestDSLExecutor:
    def test_compute(self):
        ex = DSLExecutor()
        assert ex.compute("10 + 5", {}) == 15

    def test_compute_error_returns_none(self):
        ex = DSLExecutor()
        # Force error by passing bad context type
        assert ex.compute("x", None) is None  # type: ignore

    def test_compute_batch(self):
        ex = DSLExecutor()
        results = ex.compute_batch("x + 1", [{"x": 1}, {"x": 2}])
        assert results == [2, 3]


# ===== FeatureComposer =====

class TestFeatureComposer:
    def test_compose_basic(self):
        composer = FeatureComposer()
        schema = [{"name": "age"}, {"name": "score", "default": 0.0}]
        features = {"age": 25.0, "score": 0.8}
        result = composer.compose(features, schema)
        assert result == [25.0, 0.8]

    def test_compose_missing_feature_uses_default(self):
        composer = FeatureComposer()
        schema = [{"name": "age"}, {"name": "missing", "default": -1.0}]
        features = {"age": 25.0}
        result = composer.compose(features, schema)
        assert result == [25.0, -1.0]

    def test_compose_array_dtype(self):
        composer = FeatureComposer()
        schema = [{"name": "emb", "dtype": "array", "dimension": 3}]
        features = {"emb": [1.0, 2.0, 3.0]}
        result = composer.compose(features, schema)
        assert result == [1.0, 2.0, 3.0]

    def test_compose_array_truncate(self):
        composer = FeatureComposer()
        schema = [{"name": "emb", "dtype": "array", "dimension": 2}]
        features = {"emb": [1.0, 2.0, 3.0]}
        result = composer.compose(features, schema)
        assert result == [1.0, 2.0]

    def test_compose_batch(self):
        composer = FeatureComposer()
        schema = [{"name": "x"}]
        features_list = [{"x": 1.0}, {"x": 2.0}]
        results = composer.compose_batch(features_list, schema)
        assert results == [[1.0], [2.0]]

    def test_compose_empty_schema(self):
        assert FeatureComposer().compose({"x": 1}, []) == []


# ===== FeatureCache =====

class TestFeatureCache:
    def test_set_and_get(self):
        cache = FeatureCache()
        cache.set("k1", "v1")
        assert cache.get("k1") == "v1"

    def test_get_missing(self):
        assert FeatureCache().get("missing") is None

    def test_ttl_expiry(self):
        cache = FeatureCache(default_ttl=0)
        cache.set("k1", "v1")
        time.sleep(0.01)
        assert cache.get("k1") is None

    def test_explicit_ttl_zero(self):
        # ttl=0 is falsy, so `ttl or default_ttl` uses default_ttl
        cache = FeatureCache(default_ttl=3600)
        cache.set("k1", "v1", ttl=0)
        # ttl=0 → ttl or 3600 = 3600, so entry survives
        assert cache.get("k1") == "v1"

    def test_custom_ttl_expiry(self):
        cache = FeatureCache(default_ttl=3600)
        cache.set("k1", "v1", ttl=1)  # 1 second, but test uses short wait
        # Manually expire by manipulating cache
        cache._cache["k1"] = ("v1", time.time() - 1)
        assert cache.get("k1") is None

    def test_evict_when_full(self):
        cache = FeatureCache(max_size=2, default_ttl=3600)
        cache.set("k1", "v1")
        cache.set("k2", "v2")
        cache.set("k3", "v3")  # should trigger eviction
        # at least one should still be accessible
        total = sum(1 for k in ["k1", "k2", "k3"] if cache.get(k) is not None)
        assert total >= 1

    def test_clear(self):
        cache = FeatureCache()
        cache.set("k1", "v1")
        cache.clear()
        assert cache.get("k1") is None
