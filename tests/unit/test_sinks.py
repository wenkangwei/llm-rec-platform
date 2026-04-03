"""monitor/sinks 模块单元测试"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pytest

from monitor.schema import ItemTrace, PipelineTrace, StageTrace
from monitor.sinks.file import FileSink
from monitor.sinks.clickhouse import ClickHouseSink
from monitor.sinks.stdout import StdoutSink
from monitor.sinks.training import TrainingSink
from monitor.training_logger import TrainingLogger


def _make_trace(**overrides) -> PipelineTrace:
    """创建测试用 PipelineTrace。"""
    defaults = dict(
        trace_id="tr-001",
        request_id="req-001",
        user_id="u-001",
        scene="home_feed",
        total_latency_ms=50.0,
        stages=[StageTrace(stage_name="recall", latency_ms=10, input_count=0, output_count=100)],
        item_traces=[
            ItemTrace(item_id="i-1", scores={"recall": 0.9}, positions={"recall": 1}),
            ItemTrace(item_id="i-2", scores={"recall": 0.8}, positions={"recall": 2}, filtered_out_at="prerank"),
        ],
        timestamp=1700000000.0,
    )
    defaults.update(overrides)
    return PipelineTrace(**defaults)


# ---------- FileSink ----------

class TestFileSink:
    @pytest.fixture
    def sink(self, tmp_path: Path) -> FileSink:
        return FileSink(output_dir=str(tmp_path / "traces"))

    @pytest.mark.asyncio
    async def test_write_creates_file(self, sink: FileSink, tmp_path: Path):
        trace = _make_trace()
        await sink.write(trace)
        files = list((tmp_path / "traces").glob("trace_*.jsonl"))
        assert len(files) == 1

    @pytest.mark.asyncio
    async def test_write_content(self, sink: FileSink, tmp_path: Path):
        trace = _make_trace()
        await sink.write(trace)
        filepath = next((tmp_path / "traces").glob("trace_*.jsonl"))
        data = json.loads(filepath.read_text())
        assert data["trace_id"] == "tr-001"
        assert len(data["stages"]) == 1
        assert data["stages"][0]["stage_name"] == "recall"

    @pytest.mark.asyncio
    async def test_write_multiple(self, sink: FileSink, tmp_path: Path):
        for i in range(3):
            await sink.write(_make_trace(trace_id=f"tr-{i:03d}"))
        filepath = next((tmp_path / "traces").glob("trace_*.jsonl"))
        lines = filepath.read_text().strip().split("\n")
        assert len(lines) == 3


# ---------- ClickHouseSink ----------

class TestClickHouseSink:
    @pytest.fixture
    def sink(self):
        return ClickHouseSink(client=None, batch_size=3)

    @pytest.mark.asyncio
    async def test_buffer_accumulates(self, sink: ClickHouseSink):
        await sink.write(_make_trace())
        assert len(sink._buffer) == 1

    @pytest.mark.asyncio
    async def test_auto_flush_at_batch_size(self, sink: ClickHouseSink):
        for i in range(3):
            await sink.write(_make_trace(trace_id=f"tr-{i}"))
        # batch_size=3, no client → buffer cleared on flush
        assert len(sink._buffer) == 0

    @pytest.mark.asyncio
    async def test_close_flushes_remaining(self, sink: ClickHouseSink):
        await sink.write(_make_trace())
        await sink.close()
        assert len(sink._buffer) == 0

    def test_init_table_no_client(self, sink: ClickHouseSink):
        sink.init_table()  # should not raise

    @pytest.mark.asyncio
    async def test_with_mock_client(self):
        """测试有 mock client 时会调用 insert。"""
        inserted = []

        class MockClient:
            def insert(self, table, rows, column_names=None):
                inserted.extend(rows)

        sink = ClickHouseSink(client=MockClient(), batch_size=2)
        await sink.write(_make_trace())
        await sink.write(_make_trace())
        assert len(inserted) == 2


# ---------- StdoutSink ----------

class TestStdoutSink:
    @pytest.fixture
    def sink(self):
        return StdoutSink()

    @pytest.mark.asyncio
    async def test_write_does_not_raise(self, sink: StdoutSink):
        trace = _make_trace()
        await sink.write(trace)  # 只验证不抛异常


# ---------- TrainingSink ----------

class TestTrainingSink:
    @pytest.fixture
    def training_logger(self, tmp_path: Path):
        return TrainingLogger(output_dir=str(tmp_path / "training"), flush_interval=100)

    @pytest.fixture
    def sink(self, training_logger: TrainingLogger):
        return TrainingSink(training_logger)

    @pytest.mark.asyncio
    async def test_write_logs_items(self, sink: TrainingSink, training_logger: TrainingLogger):
        trace = _make_trace()
        await sink.write(trace)
        # 只有非 filtered_out 的 item 才被记录 (i-1 survived, i-2 filtered)
        assert len(training_logger._buffer) == 1

    @pytest.mark.asyncio
    async def test_write_all_filtered(self, sink: TrainingSink, training_logger: TrainingLogger):
        trace = _make_trace(
            item_traces=[
                ItemTrace(item_id="i-1", filtered_out_at="prerank"),
                ItemTrace(item_id="i-2", filtered_out_at="rank"),
            ]
        )
        await sink.write(trace)
        assert len(training_logger._buffer) == 0
