"""File Sink — 将 PipelineTrace 写入 JSONL 文件"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from monitor.schema import PipelineTrace
from utils.logger import get_struct_logger

logger = get_struct_logger("monitor.sinks.file")


class FileSink:
    """将 PipelineTrace 写入 JSONL 文件，按日期轮转。"""

    def __init__(self, output_dir: str = "data/traces", rotate_mb: int = 500):
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._rotate_mb = rotate_mb

    async def write(self, trace: PipelineTrace) -> None:
        date_str = time.strftime("%Y%m%d")
        filepath = self._output_dir / f"trace_{date_str}.jsonl"

        try:
            data = asdict(trace)
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            logger.error(f"Trace 文件写入失败", error=str(e))
