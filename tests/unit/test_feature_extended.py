"""feature 扩展模块测试 — profiles / platform / manager / offline / server"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from feature.registry.feature_def import FeatureDef, FeatureSource, FeatureStatus
from feature.registry.group_def import FeatureGroupDef
from feature.registry.registry import FeatureRegistry
from feature.store.router import StoreRouter
from feature.platform import FeaturePlatform
from feature.manager.catalog import FeatureCatalog
from feature.manager.version import FeatureVersionManager
from feature.manager.lifecycle import FeatureLifecycle
from feature.offline.feature_gen import OfflineFeatureGenerator
from feature.offline.stats import FeatureStats
from feature.offline.backfill import FeatureBackfill
from feature.server.feature_server import FeatureServer
from feature.server.feature_plugin import FeatureFetchPlugin
from feature.profiles.user_profile import UserProfile, UserSocialProfile
from feature.profiles.item_profile import ItemProfile, ItemAuthor, ItemSocialStats
from feature.profiles.context_profile import ContextProfile
from pipeline.context import create_context


# ===== UserProfile / UserSocialProfile =====

class TestUserProfile:
    def test_required_fields(self):
        p = UserProfile(user_id="u1")
        assert p.user_id == "u1"
        assert p.interests == []
        assert p.cold_start is True
        assert p.embedding is None

    def test_social_default(self):
        p = UserProfile(user_id="u1")
        assert p.social.following_count == 0
        assert p.social.community_ids == []

    def test_all_fields(self):
        p = UserProfile(
            user_id="u1", interests=["tech"], cold_start=False,
            social=UserSocialProfile(following_count=10, community_ids=["c1"]),
            embedding=[0.1, 0.2],
        )
        assert p.interests == ["tech"]
        assert p.social.following_count == 10
        assert len(p.embedding) == 2


class TestItemProfile:
    def test_defaults(self):
        p = ItemProfile(item_id="i1")
        assert p.content_type == "article"
        assert p.tags == []
        assert p.decay_score == 1.0
        assert p.author.author_id == ""

    def test_all_fields(self):
        p = ItemProfile(
            item_id="i1", content_type="video", tags=["AI"],
            author=ItemAuthor(author_id="a1", follower_count=100),
            stats=ItemSocialStats(like_count=50, engagement_rate=0.05),
            embedding=[0.3],
        )
        assert p.author.follower_count == 100
        assert p.stats.like_count == 50
        assert p.embedding == [0.3]


class TestContextProfile:
    def test_required_fields(self):
        now = datetime(2026, 4, 3, 14, 30)
        p = ContextProfile(timestamp=now, hour_of_day=14, day_of_week=4)
        assert p.device_type == "unknown"
        assert p.scene == "home_feed"
        assert p.page_number == 0


# ===== FeaturePlatform =====

class TestFeaturePlatform:
    @pytest.fixture
    def platform(self):
        reg = FeatureRegistry()
        reg.register(FeatureDef(slot_id="s1", name="age", source=FeatureSource.REDIS))
        router = StoreRouter(reg)
        return FeaturePlatform(reg, router)

    @pytest.mark.asyncio
    async def test_get_features(self, platform):
        # No store registered → empty result
        result = await platform.get_features("u1", ["age"])
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_feature_group_missing(self, platform):
        result = await platform.get_feature_group("u1", "nonexistent")
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_feature_group(self, platform):
        from feature.store.context_store import ContextFeatureStore
        platform._registry.register(
            FeatureDef(slot_id="ctx1", name="hour_of_day", source=FeatureSource.CONTEXT)
        )
        group = FeatureGroupDef(name="time", entity_type="context")
        group.add_feature(FeatureDef(slot_id="ctx1", name="hour_of_day", source=FeatureSource.CONTEXT))
        platform._registry.register_group(group)
        platform._router.register_store(FeatureSource.CONTEXT, ContextFeatureStore())
        result = await platform.get_feature_group("u1", "time")
        assert "hour_of_day" in result

    def test_get_registry(self, platform):
        assert isinstance(platform.get_registry(), FeatureRegistry)


# ===== FeatureCatalog =====

class TestFeatureCatalog:
    @pytest.fixture
    def catalog(self):
        reg = FeatureRegistry()
        reg.register(FeatureDef(slot_id="s1", name="user_age", source=FeatureSource.REDIS, description="user age"))
        reg.register(FeatureDef(slot_id="s2", name="item_price", source=FeatureSource.MYSQL, description="item price"))
        reg.register(FeatureDef(slot_id="s3", name="user_gender", source=FeatureSource.REDIS, status=FeatureStatus.DRAFT))
        return FeatureCatalog(reg)

    def test_list_all(self, catalog):
        features = catalog.list_features()
        assert len(features) == 3

    def test_filter_by_source(self, catalog):
        features = catalog.list_features(source="redis")
        assert len(features) == 2

    def test_filter_by_status(self, catalog):
        features = catalog.list_features(status="draft")
        assert len(features) == 1
        assert features[0]["name"] == "user_gender"

    def test_search(self, catalog):
        results = catalog.search_features("age")
        assert len(results) == 1
        assert results[0]["name"] == "user_age"

    def test_search_no_match(self, catalog):
        assert catalog.search_features("nonexistent") == []

    def test_search_empty_keyword(self, catalog):
        # empty string matches all
        assert len(catalog.search_features("")) == 3


# ===== FeatureVersionManager =====

class TestFeatureVersionManager:
    def test_record_and_get_history(self):
        mgr = FeatureVersionManager(FeatureRegistry())
        mgr.record_change("age", "v1", "v2", "updated dtype")
        history = mgr.get_history()
        assert len(history) == 1
        assert history[0]["feature_name"] == "age"

    def test_get_history_by_name(self):
        mgr = FeatureVersionManager(FeatureRegistry())
        mgr.record_change("age", "v1", "v2", "reason1")
        mgr.record_change("price", "v1", "v2", "reason2")
        assert len(mgr.get_history("age")) == 1
        assert len(mgr.get_history("price")) == 1

    def test_get_history_empty(self):
        mgr = FeatureVersionManager(FeatureRegistry())
        assert mgr.get_history() == []


# ===== FeatureLifecycle =====

class TestFeatureLifecycle:
    @pytest.fixture
    def lifecycle(self):
        reg = FeatureRegistry()
        reg.register(FeatureDef(slot_id="s1", name="new_feat", status=FeatureStatus.DRAFT))
        reg.register(FeatureDef(slot_id="s2", name="active_feat", status=FeatureStatus.ACTIVE))
        reg.register(FeatureDef(slot_id="s3", name="deprecated_feat", status=FeatureStatus.DEPRECATED))
        return FeatureLifecycle(reg)

    def test_activate(self, lifecycle):
        assert lifecycle.activate("new_feat") is True
        assert lifecycle.activate("new_feat") is False  # already active

    def test_activate_nonexistent(self, lifecycle):
        assert lifecycle.activate("missing") is False

    def test_deprecate(self, lifecycle):
        assert lifecycle.deprecate("active_feat") is True
        assert lifecycle.deprecate("active_feat") is False  # already deprecated

    def test_deprecate_draft_fails(self, lifecycle):
        assert lifecycle.deprecate("new_feat") is False

    def test_reactivate(self, lifecycle):
        assert lifecycle.reactivate("deprecated_feat") is True
        assert lifecycle.reactivate("deprecated_feat") is False  # now active


# ===== Offline Stubs =====

class TestOfflineFeatureGenerator:
    def test_generate_user_features_empty(self):
        gen = OfflineFeatureGenerator()
        assert gen.generate_user_features(["u1"]) == []

    def test_generate_user_features_with_data(self):
        gen = OfflineFeatureGenerator()
        gen.load_data("user", [
            {"user_id": "u1", "action": "click", "category": "tech"},
            {"user_id": "u1", "action": "collect", "category": "tech"},
            {"user_id": "u1", "action": "share", "category": "sports"},
        ])
        result = gen.generate_user_features(["u1"])
        assert len(result) == 1
        assert result[0]["entity_id"] == "u1"
        assert result[0]["click_count"] == 1
        assert result[0]["collect_count"] == 1
        assert result[0]["share_count"] == 1
        assert result[0]["top_category"] == "tech"

    def test_generate_item_features_empty(self):
        gen = OfflineFeatureGenerator()
        assert gen.generate_item_features(["i1"]) == []

    def test_generate_item_features_with_data(self):
        gen = OfflineFeatureGenerator()
        gen.load_data("item", [
            {"item_id": "i1", "action": "expose"},
            {"item_id": "i1", "action": "click"},
            {"item_id": "i1", "action": "collect"},
        ])
        result = gen.generate_item_features(["i1"])
        assert len(result) == 1
        assert result[0]["entity_id"] == "i1"
        assert result[0]["expose_count"] == 1
        assert result[0]["click_count"] == 1
        assert result[0]["ctr"] == 1.0

    def test_generate_cross_features_no_data(self):
        gen = OfflineFeatureGenerator()
        result = gen.generate_cross_features("u1", ["i1"])
        assert len(result) == 1
        assert result[0]["has_interacted"] is False

    def test_generate_cross_features_with_data(self):
        gen = OfflineFeatureGenerator()
        gen.load_data("cross", [
            {"user_id": "u1", "item_id": "i1", "action": "click"},
        ])
        result = gen.generate_cross_features("u1", ["i1", "i2"])
        assert len(result) == 2
        assert result[0]["has_interacted"] is True
        assert result[1]["has_interacted"] is False


class TestFeatureStats:
    def test_compute_coverage_no_data(self):
        stats = FeatureStats()
        result = stats.compute_coverage("age")
        assert result["feature"] == "age"
        assert result["sample_size"] == 0
        assert result["coverage"] == 0.0

    def test_compute_coverage_with_data(self):
        stats = FeatureStats()
        stats.load_samples("age", [25, None, 30, "", 35])
        result = stats.compute_coverage("age")
        assert result["feature"] == "age"
        assert result["sample_size"] == 5
        assert result["coverage"] == 0.6  # 3/5

    def test_compute_distribution_no_data(self):
        stats = FeatureStats()
        result = stats.compute_distribution("price")
        assert result["feature"] == "price"
        assert result["mean"] == 0.0

    def test_compute_distribution_with_data(self):
        stats = FeatureStats()
        stats.load_samples("price", [10, 20, 30, 40, 50])
        result = stats.compute_distribution("price")
        assert result["feature"] == "price"
        assert result["mean"] == 30.0
        assert result["min"] == 10
        assert result["max"] == 50
        assert result["median"] == 30.0

    def test_compute_multi_stats(self):
        stats = FeatureStats()
        stats.load_samples("f1", [1, 2, 3])
        results = stats.compute_multi_stats(["f1", "f2"])
        assert len(results) == 2


class TestFeatureBackfill:
    @pytest.mark.asyncio
    async def test_backfill_empty_ids(self):
        bf = FeatureBackfill()
        count = await bf.backfill("user", [], ["age"])
        assert count == 0

    @pytest.mark.asyncio
    async def test_backfill_no_store(self):
        bf = FeatureBackfill()
        gen = OfflineFeatureGenerator()
        bf.configure(generator=gen)
        count = await bf.backfill("user", ["u1"], ["age"])
        # 无原始数据，生成器返回空
        assert count == 0

    @pytest.mark.asyncio
    async def test_backfill_with_generator(self):
        bf = FeatureBackfill(batch_size=10)
        gen = OfflineFeatureGenerator()
        gen.load_data("user", [
            {"user_id": "u1", "action": "click", "category": "tech"},
        ])
        bf.configure(generator=gen)
        count = await bf.backfill("user", ["u1"], ["click_count"])
        assert count == 1  # 无 store 时 write 返回 len


# ===== FeatureServer =====

class TestFeatureServer:
    @pytest.fixture
    def server(self):
        platform = MagicMock(spec=FeaturePlatform)
        platform.get_features = AsyncMock(return_value={"age": 25})
        return FeatureServer(platform)

    @pytest.mark.asyncio
    async def test_fetch_user_features(self, server):
        result = await server.fetch_user_features("u1", "home")
        assert "age" in result

    @pytest.mark.asyncio
    async def test_fetch_item_features(self, server):
        result = await server.fetch_item_features("i1")
        assert "age" in result

    @pytest.mark.asyncio
    async def test_fetch_context_features(self, server):
        result = await server.fetch_context_features()
        assert "hour_of_day" in result
        assert "is_weekend" in result
        assert isinstance(result["timestamp"], float)


# ===== FeatureFetchPlugin =====

class TestFeatureFetchPlugin:
    def test_name(self):
        server = MagicMock(spec=FeatureServer)
        server.fetch_user_features = AsyncMock(return_value={"age": 25})
        plugin = FeatureFetchPlugin(server)
        assert plugin.name() == "feature_fetch"

    def test_process(self):
        import asyncio
        server = MagicMock(spec=FeatureServer)
        server.fetch_user_features = AsyncMock(return_value={"age": 25, "gender": "M"})
        plugin = FeatureFetchPlugin(server)
        ctx = create_context(user_id="u1", scene="home_feed")
        try:
            result = plugin.process(ctx)
            assert result.user_features["age"] == 25
            assert result.user_features["gender"] == "M"
        finally:
            # Ensure event loop is restored for subsequent tests
            asyncio.set_event_loop(asyncio.new_event_loop())
