.PHONY: install test lint run proto proto-clean docker-build docker-up docker-down clean help

PYTHON ?= python3.10
PIP ?= pip

help: ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 安装依赖（含 dev）
	$(PIP) install -e ".[dev]"

test: ## 运行所有测试
	$(PYTHON) -m pytest tests/ -v --tb=short -q

test-unit: ## 只跑单元测试
	$(PYTHON) -m pytest tests/unit/ -v --tb=short -q

test-e2e: ## 只跑 E2E 测试
	$(PYTHON) -m pytest tests/e2e/ -v --tb=short -q

lint: ## 代码检查
	$(PYTHON) -m ruff check .

lint-fix: ## 自动修复代码风格
	$(PYTHON) -m ruff check --fix .

run: ## 启动开发服务器
	$(PYTHON) -m uvicorn server.app:create_app --factory --host 0.0.0.0 --port 8000 --reload

proto: ## 编译 Protobuf 文件
	$(PYTHON) -m grpc_tools.protoc -I protocols/proto \
		--python_out=protocols/generated/python \
		--grpc_python_out=protocols/generated/python \
		protocols/proto/*.proto

proto-clean: ## 清理 Protobuf 生成文件
	find protocols/generated/python -name '*_pb2*.py' -not -name '__init__.py' -delete

docker-build: ## 构建 Docker 镜像
	docker build -f docker/Dockerfile -t llm-rec-platform:latest .

docker-up: ## 启动所有服务
	docker compose -f docker/docker-compose.yaml up -d

docker-down: ## 停止所有服务
	docker compose -f docker/docker-compose.yaml down

docker-logs: ## 查看服务日志
	docker compose -f docker/docker-compose.yaml logs -f rec-server

clean: ## 清理缓存
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null
	find . -type f -name "*.pyc" -delete 2>/dev/null
	rm -rf *.egg-info build dist .ruff_cache
