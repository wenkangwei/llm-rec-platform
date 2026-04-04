"""gRPC 服务端 — 分布式部署时启用

当前阶段使用 HTTP (FastAPI) 通信。
当需要按模块拆分到不同机器时，启用 gRPC 服务。
Protobuf 编译后生成文件在 protocols/generated/python/ 中。
"""

from __future__ import annotations

import asyncio
from typing import Any

from concurrent import futures

from utils.logger import get_struct_logger

logger = get_struct_logger("server.grpc")

try:
    import grpc
    from protocols.generated.python import common_pb2
    from protocols.generated.python import common_pb2_grpc
    from protocols.generated.python import recommendation_pb2
    from protocols.generated.python import recommendation_pb2_grpc
    from protocols.generated.python import feature_service_pb2
    from protocols.generated.python import feature_service_pb2_grpc
    from protocols.generated.python import model_service_pb2
    from protocols.generated.python import model_service_pb2_grpc
    from protocols.generated.python import llm_service_pb2
    from protocols.generated.python import llm_service_pb2_grpc
    from protocols.generated.python import social_service_pb2
    from protocols.generated.python import social_service_pb2_grpc

    HAS_GRPC = True
except ImportError:
    HAS_GRPC = False
    logger.warning("grpcio 或 protobuf 生成文件未就绪，gRPC 服务不可用")


class RecServiceServicer:
    """推荐服务 gRPC Servicer。

    实现 PipelineStage 的 process_grpc 接口，
    支持分布式部署时各阶段独立运行在不同节点。
    """

    def __init__(self, pipeline_executor: Any = None, components_health: dict | None = None):
        self._executor = pipeline_executor
        self._components_health = components_health or {}
        self._server: Any = None

    def Recommend(self, request: Any, context: Any) -> Any:
        """推荐请求处理。"""
        if not HAS_GRPC:
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details("protobuf 文件未编译")
            return recommendation_pb2.RecResponse() if HAS_GRPC else None

        try:
            header = request.header
            request_id = header.request_id if header else ""
            user_id = header.user_id if header else ""
            scene = header.scene if header else "home_feed"

            # 同步调用异步 executor
            if self._executor:
                ctx = asyncio.run(self._execute_pipeline(user_id, scene, request_id))
                items = []
                for c in ctx.candidates[:50]:
                    items.append(recommendation_pb2.RecItem(
                        item_id=c.get("item_id", ""),
                        score=c.get("score", 0.0),
                        source=c.get("source", ""),
                    ))
                return recommendation_pb2.RecResponse(
                    request_id=request_id,
                    items=items,
                    total=len(items),
                    has_more=len(ctx.candidates) > 50,
                )

            return recommendation_pb2.RecResponse(request_id=request_id)
        except Exception as e:
            logger.error("gRPC Recommend 失败", error=str(e))
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return recommendation_pb2.RecResponse()

    def Search(self, request: Any, context: Any) -> Any:
        """搜索请求处理。"""
        if not HAS_GRPC:
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details("protobuf 文件未编译")
            return None

        header = request.header if request.header else None
        query = request.query if request.query else ""
        request_id = header.request_id if header else ""

        return recommendation_pb2.RecResponse(
            request_id=request_id,
            items=[],
            total=0,
        )

    def Track(self, request: Any, context: Any) -> Any:
        """行为上报处理。"""
        if not HAS_GRPC:
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details("protobuf 文件未编译")
            return None

        logger.info("gRPC Track 收到行为上报")
        return common_pb2.Empty()

    def HealthCheck(self, request: Any, context: Any) -> Any:
        """健康检查。"""
        if not HAS_GRPC:
            context.set_code(grpc.StatusCode.UNIMPLEMENTED)
            context.set_details("protobuf 文件未编译")
            return None

        all_healthy = all(self._components_health.values()) if self._components_health else True
        if not all_healthy:
            context.set_code(grpc.StatusCode.UNAVAILABLE)
            context.set_details("部分组件不健康")
        return common_pb2.Empty()

    async def _execute_pipeline(self, user_id: str, scene: str, request_id: str) -> Any:
        """执行推荐链路。"""
        from protocols.schemas.context import RecContext
        ctx = RecContext(
            request_id=request_id,
            user_id=user_id,
            scene=scene,
        )
        return await self._executor.execute(ctx)


def create_grpc_server(
    host: str = "[::]:50051",
    max_workers: int = 10,
    pipeline_executor: Any = None,
    components_health: dict | None = None,
) -> Any:
    """创建 gRPC 服务器。"""
    if not HAS_GRPC:
        logger.warning("grpcio 未安装，gRPC 服务不可用")
        return None

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    servicer = RecServiceServicer(pipeline_executor, components_health)

    # 注册各服务 servicer
    recommendation_pb2_grpc.add_RecommendationServiceServicer_to_server(
        _RecommendationServiceServicer(servicer), server
    )

    server.add_insecure_port(host)
    logger.info("gRPC 服务器已创建", host=host, max_workers=max_workers)
    return server


def start_grpc_server(
    host: str = "[::]:50051",
    max_workers: int = 10,
    pipeline_executor: Any = None,
    components_health: dict | None = None,
) -> Any:
    """创建并启动 gRPC 服务器。"""
    server = create_grpc_server(host, max_workers, pipeline_executor, components_health)
    if server:
        server.start()
        logger.info("gRPC 服务器已启动", host=host)
    return server


# ===== 适配器类：将 RecServiceServicer 方法映射到各 gRPC service stub =====

class _RecommendationServiceServicer(recommendation_pb2_grpc.RecommendationServiceServicer if HAS_GRPC else object):
    """推荐服务 gRPC Servicer。"""

    def __init__(self, servicer: RecServiceServicer):
        self._servicer = servicer

    def Recommend(self, request, context):
        return self._servicer.Recommend(request, context)

    def Search(self, request, context):
        return self._servicer.Search(request, context)

    def Track(self, request, context):
        return self._servicer.Track(request, context)

    def HealthCheck(self, request, context):
        return self._servicer.HealthCheck(request, context)


class _FeatureServiceServicer(feature_service_pb2_grpc.FeatureServiceServicer if HAS_GRPC else object):
    """特征服务 gRPC Servicer。"""

    def __init__(self, servicer: RecServiceServicer):
        self._servicer = servicer

    def GetFeatures(self, request, context):
        # TODO: 委托给 FeaturePlatform
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("FeatureService.GetFeatures 尚未实现")
        return feature_service_pb2.FeatureResponse()

    def BatchGetFeatures(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("FeatureService.BatchGetFeatures 尚未实现")
        return feature_service_pb2.FeatureBatchResponse()


class _ModelServiceServicer(model_service_pb2_grpc.ModelServiceServicer if HAS_GRPC else object):
    """模型服务 gRPC Servicer。"""

    def __init__(self, servicer: RecServiceServicer):
        self._servicer = servicer

    def Predict(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("ModelService.Predict 尚未实现")
        return model_service_pb2.PredictResponse()

    def GetEmbedding(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("ModelService.GetEmbedding 尚未实现")
        return model_service_pb2.EmbeddingResponse()


class _LLMServiceServicer(llm_service_pb2_grpc.LLMServiceServicer if HAS_GRPC else object):
    """LLM 服务 gRPC Servicer。"""

    def __init__(self, servicer: RecServiceServicer):
        self._servicer = servicer

    def Generate(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("LLMService.Generate 尚未实现")
        return llm_service_pb2.GenerateResponse()

    def Embed(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("LLMService.Embed 尚未实现")
        return llm_service_pb2.EmbedResponse()


class _SocialServiceServicer(social_service_pb2_grpc.SocialServiceServicer if HAS_GRPC else object):
    """社交服务 gRPC Servicer。"""

    def __init__(self, servicer: RecServiceServicer):
        self._servicer = servicer

    def GetSocialGraph(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("SocialService.GetSocialGraph 尚未实现")
        return social_service_pb2.SocialGraphResponse()

    def GetInteractionStrength(self, request, context):
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("SocialService.GetInteractionStrength 尚未实现")
        return social_service_pb2.InteractionResponse()
