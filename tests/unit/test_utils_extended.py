"""utils 扩展 + events + serialization 测试"""

from __future__ import annotations

import json

import pytest

from utils.serialization import to_json, from_json, _to_plain_dict
from protocols.schemas.events import TrackEventV2, TrainingLogEntry


# ========== Serialization ==========

class TestSerialization:
    def test_to_json_dict(self):
        result = to_json({"key": "value"})
        assert json.loads(result) == {"key": "value"}

    def test_to_json_list(self):
        result = to_json([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]

    def test_to_json_dataclass(self):
        from dataclasses import dataclass
        @dataclass
        class Foo:
            x: int = 1
        result = to_json(Foo())
        assert json.loads(result)["x"] == 1

    def test_from_json(self):
        result = from_json('{"a": 1}')
        assert result == {"a": 1}

    def test_from_json_list(self):
        result = from_json("[1, 2]")
        assert result == [1, 2]

    def test_to_plain_dict_nested(self):
        data = {"a": [1, {"b": 2}], "c": "str"}
        result = _to_plain_dict(data)
        assert result == data

    def test_to_plain_dict_primitives(self):
        assert _to_plain_dict(42) == 42
        assert _to_plain_dict("hello") == "hello"
        assert _to_plain_dict(None) is None


# ========== Events ==========

class TestTrackEventV2:
    def test_required_fields(self):
        event = TrackEventV2(
            event_id="e1", user_id="u1", item_id="i1",
            action="click", scene="home", request_id="r1", timestamp=1.0,
        )
        assert event.event_id == "e1"
        assert event.action == "click"

    def test_defaults(self):
        event = TrackEventV2(
            event_id="e1", user_id="u1", item_id="i1",
            action="click", scene="home", request_id="r1", timestamp=1.0,
        )
        assert event.page == 0
        assert event.position == 0
        assert event.device_type == ""
        assert event.dwell_time_sec is None
        assert event.extra == {}

    def test_all_fields(self):
        event = TrackEventV2(
            event_id="e1", user_id="u1", item_id="i1",
            action="click", scene="home", request_id="r1", timestamp=1.0,
            page=1, position=3, device_type="mobile",
            dwell_time_sec=15.5, extra={"source": "feed"},
        )
        assert event.page == 1
        assert event.dwell_time_sec == 15.5


class TestTrainingLogEntry:
    def test_defaults(self):
        entry = TrainingLogEntry(trace_id="t1")
        assert entry.trace_id == "t1"
        assert entry.user_features == {}
        assert entry.prerank_score == 0.0
        assert entry.label_clicked is None

    def test_all_fields(self):
        entry = TrainingLogEntry(
            trace_id="t1",
            user_features={"age": 25},
            item_features={"price": 100},
            prerank_score=0.8,
            rank_score=0.9,
            rank_position=1,
            label_clicked=True,
            label_liked=False,
            dwell_time_sec=30.0,
        )
        assert entry.user_features["age"] == 25
        assert entry.label_clicked is True
        assert entry.dwell_time_sec == 30.0
