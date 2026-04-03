"""混排 — 多类型内容混合输出"""

from __future__ import annotations

from pipeline.base import PipelineStage
from protocols.schemas.context import RecContext
from utils.logger import get_struct_logger

logger = get_struct_logger("ranking.mixer")


class MixerStage(PipelineStage):
    """混排阶段：按内容类型比例混合输出最终推荐结果。"""

    def __init__(
        self,
        strategy: str = "weighted_round_robin",
        slots: list[dict] | None = None,
    ):
        self._strategy = strategy
        self._slots = slots or [
            {"content_type": "article", "ratio": 0.5},
            {"content_type": "video", "ratio": 0.3},
            {"content_type": "post", "ratio": 0.2},
        ]

    def name(self) -> str:
        return "mixer"

    def process(self, ctx: RecContext) -> RecContext:
        if not ctx.candidates:
            return ctx

        page_size = ctx.page_size

        if self._strategy == "weighted_round_robin":
            ctx.candidates = self._weighted_round_robin(ctx.candidates, page_size)
        else:
            # 默认按分数截断
            ctx.candidates = ctx.candidates[:page_size]

        logger.debug(f"混排完成", output=len(ctx.candidates))
        return ctx

    def _weighted_round_robin(self, candidates: list, page_size: int) -> list:
        """加权轮询混排：按内容类型比例分配位置。"""
        # 按内容类型分组
        groups: dict[str, list] = {}
        for item in candidates:
            ctype = item.features.get("content_type", "article")
            groups.setdefault(ctype, []).append(item)

        # 每个类型保持分数排序
        for group in groups.values():
            group.sort(key=lambda x: x.score, reverse=True)

        # 按比例分配数量
        result = []
        slot_map = {s["content_type"]: s["ratio"] for s in self._slots}

        # 计算每个类型的分配数量
        allocations = {}
        remaining = page_size
        types_with_content = [t for t in slot_map if t in groups]

        if not types_with_content:
            return candidates[:page_size]

        for ctype in types_with_content:
            alloc = max(1, int(page_size * slot_map[ctype]))
            allocations[ctype] = min(alloc, len(groups[ctype]))

        # 轮询填充
        pointers = {t: 0 for t in types_with_content}
        while len(result) < page_size:
            placed = False
            for ctype in types_with_content:
                if len(result) >= page_size:
                    break
                ptr = pointers[ctype]
                if ptr < allocations.get(ctype, 0) and ptr < len(groups[ctype]):
                    result.append(groups[ctype][ptr])
                    pointers[ctype] += 1
                    placed = True
            if not placed:
                break

        return result
