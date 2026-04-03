"""monitor 模块单元测试 — RecTracer / Metrics"""

from __future__ import annotations

import pytest

from monitor.schema import ItemTrace, PipelineTrace, RecallCoverage, StageTrace
from monitor.tracer import RecTracer


class TestRecTracer:
    """RecTracer 链路追踪测试。"""

    def test_create_tracer(self):
        tracer = RecTracer(request_id="r1", user_id="u1", scene="home_feed")
        assert tracer.trace_id

    def test_stage_timing(self):
        import time

        tracer = RecTracer(request_id="r1", user_id="u1", scene="home_feed")
        tracer.start_stage("recall")
        time.sleep(0.01)
        tracer.end_stage("recall", input_count=0, output_count=500)

        trace = tracer.finalize()
        assert len(trace.stages) == 1
        assert trace.stages[0].stage_name == "recall"
        assert trace.stages[0].latency_ms >= 5
        assert trace.stages[0].output_count == 500

    def test_multiple_stages(self):
        tracer = RecTracer(request_id="r1", user_id="u1", scene="home_feed")
        tracer.start_stage("recall")
        tracer.end_stage("recall", output_count=500)
        tracer.start_stage("rank")
        tracer.end_stage("rank", input_count=500, output_count=50)

        trace = tracer.finalize()
        assert len(trace.stages) == 2

    def test_item_score_tracking(self):
        tracer = RecTracer(request_id="r1", user_id="u1", scene="home_feed")
        tracer.record_item_score("i1", "recall", 0.9, position=1)
        tracer.record_item_score("i1", "rank", 0.85, position=3)

        trace = tracer.finalize()
        assert len(trace.item_traces) == 1
        assert trace.item_traces[0].scores["recall"] == 0.9
        assert trace.item_traces[0].positions["rank"] == 3

    def test_filter_tracking(self):
        tracer = RecTracer(request_id="r1", user_id="u1", scene="home_feed")
        tracer.record_filter_out("i1", "prerank", "score_too_low")

        trace = tracer.finalize()
        assert trace.item_traces[0].filtered_out_at == "prerank"

    def test_recall_coverage(self):
        tracer = RecTracer(request_id="r1", user_id="u1", scene="home_feed")
        tracer.record_recall_source("hot", recalled_count=200)
        tracer.record_recall_source("cf", recalled_count=300)
        tracer.update_recall_survival("hot", survived=100, exposed=20)

        trace = tracer.finalize()
        assert len(trace.recall_coverages) == 2
        hot_cov = [c for c in trace.recall_coverages if c.source == "hot"][0]
        assert hot_cov.recalled_count == 200
        assert hot_cov.survived_count == 100

    def test_finalize_metadata(self):
        tracer = RecTracer(request_id="r1", user_id="u1", scene="home_feed")
        trace = tracer.finalize()
        assert trace.request_id == "r1"
        assert trace.user_id == "u1"
        assert trace.scene == "home_feed"
        assert trace.total_latency_ms >= 0


class TestSchemaStructures:
    """数据结构测试。"""

    def test_stage_trace(self):
        t = StageTrace(stage_name="recall", latency_ms=10.0, input_count=0, output_count=500)
        assert t.error == ""

    def test_item_trace(self):
        t = ItemTrace(item_id="i1")
        assert t.scores == {}
        assert t.filtered_out_at == ""

    def test_recall_coverage(self):
        c = RecallCoverage(source="hot", recalled_count=100, survived_count=50, final_exposed=10)
        assert c.source == "hot"

    def test_pipeline_trace(self):
        t = PipelineTrace(trace_id="t1", request_id="r1", user_id="u1", scene="home_feed")
        assert t.stages == []
        assert t.item_traces == []
