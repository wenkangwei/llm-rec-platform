FROM python:3.11-slim

WORKDIR /app

# 系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]" 2>/dev/null || pip install --no-cache-dir .

# 应用代码
COPY . .

# 编译 Protobuf
RUN python -m grpc_tools.protoc -I protocols/proto \
    --python_out=protocols/generated/python \
    --grpc_python_out=protocols/generated/python \
    protocols/proto/*.proto 2>/dev/null || true

EXPOSE 8000 9090

CMD ["uvicorn", "server.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
