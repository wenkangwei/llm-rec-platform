"""gRPC 服务（预留）— 未来分布式部署时启用"""

# 当前阶段使用 HTTP (FastAPI) 通信
# 当需要按模块拆分到不同机器时，启用 gRPC 服务
# Protobuf 定义已在 protocols/proto/ 中准备好
#
# 启用步骤：
# 1. pip install grpcio grpcio-tools
# 2. python -m grpc_tools.protoc -I protocols/proto --python_out=protocols/generated/python --grpc_python_out=protocols/generated/python protocols/proto/*.proto
# 3. 实现各 service 的 Servicer 类
