"""PipelineStage — 推荐链路统一抽象接口"""

from __future__ import annotations

from abc import ABC, abstractmethod

from protocols.schemas.context import RecContext


class PipelineStage(ABC):
    """推荐链路统一抽象接口。

    所有链路模块（召回、粗排、精排、重排、混排）必须实现此接口。
    接口签名统一：process(ctx: RecContext) -> RecContext
    """

    @abstractmethod
    def name(self) -> str:
        """模块名称。"""

    @abstractmethod
    def process(self, ctx: RecContext) -> RecContext:
        """处理推荐上下文，返回更新后的上下文。

        每个模块只读写 ctx 中属于自己的字段。
        """

    def warmup(self) -> None:
        """预热（加载模型、连接存储等）。默认空实现。"""

    def health_check(self) -> bool:
        """健康检查。默认返回 True。"""
        return True

    def shutdown(self) -> None:
        """优雅关闭。默认空实现。"""
