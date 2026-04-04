"""gRPC 服务端 — 分布式部署时启用

当前阶段使用 HTTP (FastAPI) 通信。
当需要按模块拆分到不同机器时，启用 gRPC 服务。
Protobuf 定义已在 protocols/proto/ 中准备好。
"""

from __future__ import annotations

from typing import Any

from concurrent import futures

from utils.logger import get_struct_logger

logger = get_struct_logger("server.grpc")


class RecServiceServicer:
    """推荐服务 gRPC Servicer。

    实现 PipelineStage 的 process_grpc 接口，
    支持分布式部署时各阶段独立运行在不同节点。

    启用步骤：
    1. pip install grpcio grpcio-tools
    2. python -m grpc_tools.protoc -I protocols/proto \\
           --python_out=protocols/generated/python \\
           --grpc_python_out=protocols/generated/python \\
           protocols/proto/*.proto
    3. 取消下方 import 并启动 gRPC 服务
    """

    def __init__(self, pipeline_executor: Any = None):
        self._executor = pipeline_executor
        self._server: Any = None

    def Recommend(self, request: Any, context: Any) -> Any:
        """推荐请求处理。"""
        # from protocols.generated.python import rec_pb2, rec_pb2_grpc
        # 将 gRPC request 转换为 RecContext
        # 执行 pipeline
        # 转换结果为 gRPC response
        raise NotImplementedError("需要先编译 protobuf 文件")

    def Search(self, request: Any, context: Any) -> Any:
        """搜索请求处理。"""
        raise NotImplementedError("需要先编译 protobuf 文件")

    def Track(self, request: Any, context: Any) -> Any:
        """行为上报处理。"""
        raise NotImplementedError("需要先编译 protobuf 文件")

    def HealthCheck(self, request: Any, context: Any) -> Any:
        """健康检查。"""
        raise NotImplementedError("需要先编译 protobuf 文件")


def create_grpc_server(
    host: str = "[::]:50051",
    max_workers: int = 10,
    pipeline_executor: Any = None,
) -> Any:
    """创建 gRPC 服务器。

    Args:
        host: 监听地址
        max_workers: 最大并发 worker 数
        pipeline_executor: Pipeline 执行器实例

    Returns:
        gRPC Server 实例（未启动）
    """
    try:
        import grpc
        from concurrent import futures

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
        servicer = RecServiceServicer(pipeline_executor)

        # 注册 servicer
        # from protocols.generated.python import rec_pb2_grpc
        # rec_pb2_grpc.add_RecommendationServiceServicer_to_server(servicer, server)

        server.add_insecure_port(host)
        logger.info(f"gRPC 服务器已创建", host=host, max_workers=max_workers)
        return server
    except ImportError:
        logger.warning("grpcio 未安装，gRPC 服务不可用")
        return None


def start_grpc_server(
    host: str = "[::]:50051",
    max_workers: int = 10,
    pipeline_executor: Any = None,
) -> Any:
    """创建并启动 gRPC 服务器。"""
    server = create_grpc_server(host, max_workers, pipeline_executor)
    if server:
        server.start()
        logger.info(f"gRPC 服务器已启动", host=host)
    return server
