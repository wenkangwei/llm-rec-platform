"""PipelineStage — 推荐链路统一抽象接口

初版使用 function call（直接 Python 调用）。
gRPC 接口已通过 protobuf 定义预留（protocols/proto/*.proto），未来拆分部署时启用。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from protocols.schemas.context import RecContext


class PipelineStage(ABC):
    """推荐链路统一抽象接口。

    所有链路模块（召回、粗排、精排、重排、混排）必须实现此接口。
    接口签名统一：process(ctx: RecContext) -> RecContext

    调用方式：
    - 初版：通过 invoke() 直接 Python function call
    - 未来：invoke() 内部可替换为 gRPC stub 调用，无需修改上游代码
    """

    @abstractmethod
    def name(self) -> str:
        """模块名称。"""

    @abstractmethod
    def process(self, ctx: RecContext) -> RecContext:
        """处理推荐上下文，返回更新后的上下文。

        每个模块只读写 ctx 中属于自己的字段。
        """

    # ===== 初版调用入口：function call =====

    def invoke(self, ctx: RecContext) -> RecContext:
        """统一调用入口（同步）。

        初版：直接调用 self.process(ctx)
        未来：可替换为 gRPC stub 调用，上游无感知。
        """
        return self.process(ctx)

    async def ainvoke(self, ctx: RecContext) -> RecContext:
        """统一调用入口（异步）。

        初版：直接调用 self.process(ctx)
        未来：可替换为 gRPC async stub 调用。
        """
        result = self.process(ctx)
        if hasattr(result, "__await__"):
            result = await result
        return result

    # ===== gRPC 预留（初版不实现） =====

    @property
    def grpc_servicable(self) -> bool:
        """是否支持 gRPC 调用。初版返回 False。"""
        return False

    def process_grpc(self, request_bytes: bytes) -> bytes:
        """gRPC 请求处理（预留）。初版抛出 NotImplementedError。

        未来启用 gRPC 时：
        1. 根据 proto 定义反序列化 request_bytes
        2. 转为 RecContext
        3. 调用 self.process(ctx)
        4. 序列化为 proto response
        """
        raise NotImplementedError(
            f"gRPC 调用未启用。proto 定义见 protocols/proto/，"
            f"启用时实现 {self.__class__.__name__}.process_grpc()"
        )

    # ===== 生命周期 =====

    def warmup(self) -> None:
        """预热（加载模型、连接存储等）。默认空实现。"""

    def health_check(self) -> bool:
        """健康检查。默认返回 True。"""
        return True

    def shutdown(self) -> None:
        """优雅关闭。默认空实现。"""
