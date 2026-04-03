"""monitor 扩展模块测试 — metrics / collector / writer"""

from __future__ import annotations

import pytest

from monitor.metrics import RecMetrics, get_metrics
from monitor.schema import PipelineTrace
from monitor.tracer import RecTracer
from monitor.collector import MonitorCollector
from monitor.writer import TraceWriter
from protocols.schemas.context import RecContext


# ========== RecMetrics ==========

class TestRecMetrics:
    @pytest.fixture
    def metrics(self):
        return RecMetrics()

    def test_record_latency(self, metrics):
        metrics.record_latency("recall", 10.5)
        metrics.record_latency("recall", 20.0)
        summary = metrics.get_histogram_summary("latency:recall")
        assert summary["count"] == 2
        assert summary["max"] == 20.0

    def test_record_count(self, metrics):
        metrics.record_count("requests")
        metrics.record_count("requests", 3.0)
        assert metrics.get_counter("requests") == 4.0

    def test_get_counter_missing(self, metrics):
        assert metrics.get_counter("nonexistent") == 0.0

    def test_get_histogram_summary_missing(self, metrics):
        summary = metrics.get_histogram_summary("nonexistent")
        assert summary["p50"] == 0
        assert summary["count"] == 0

    def test_record_histogram(self, metrics):
        for v in [10, 20, 30, 40, 50]:
            metrics.record_histogram("test_hist", float(v))
        summary = metrics.get_histogram_summary("test_hist")
        assert summary["count"] == 5
        assert summary["max"] == 50.0

    def test_get_all_metrics(self, metrics):
        metrics.record_count("a")
        metrics.record_latency("b", 1.0)
        all_m = metrics.get_all_metrics()
        assert "counters" in all_m
        assert "latency:b" in all_m

    def test_format_prometheus(self, metrics):
        metrics.record_count("http_requests", 42.0)
        metrics.record_latency("recall", 15.0)
        output = metrics.format_prometheus()
        assert "http_requests" in output
        assert "latency_recall" in output

    def test_format_prometheus_empty(self, metrics):
        output = metrics.format_prometheus()
        assert isinstance(output, str)


class TestGetMetricsSingleton:
    def test_returns_instance(self):
        m = get_metrics()
        assert isinstance(m, RecMetrics)


# ========== MonitorCollector ==========

class TestMonitorCollector:
    @pytest.fixture
    def collector(self):
        return MonitorCollector()

    def test_add_sink(self, collector):
        class FakeSink:
            async def write(self, trace):
                pass
        collector.add_sink(FakeSink())
        assert len(collector._sinks) == 1

    @pytest.mark.asyncio
    async def test_collect(self, collector):
        tracer = RecTracer(request_id="r1", user_id="u1", scene="home")
        tracer.start_stage("recall")
        tracer.end_stage("recall", input_count=0, output_count=100)

        ctx = RecContext(request_id="r1", user_id="u1", scene="home")
        trace = await collector.collect(tracer, ctx)
        assert isinstance(trace, PipelineTrace)
        assert trace.request_id == "r1"
        assert len(trace.stages) == 1
        assert trace.stages[0].stage_name == "recall"


# ========== TraceWriter ==========

class TestTraceWriter:
    @pytest.mark.asyncio
    async def test_write_not_implemented(self):
        writer = TraceWriter()
        trace = PipelineTrace(trace_id="t1", request_id="r1", user_id="u1", scene="home")
        with pytest.raises(NotImplementedError):
            await writer.write(trace)
