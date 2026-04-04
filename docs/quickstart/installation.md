# 环境安装

本页说明如何在本地搭建 LLM 推荐系统平台的开发环境。

## 前置条件

| 工具 | 最低版本 | 用途 |
|------|----------|------|
| Python | 3.10+ | 运行时环境 |
| pip | 23.0+ | 包管理 |
| Git | 2.30+ | 版本控制 |

!!! tip "Python 版本检查"
    ```bash
    python --version
    # Python 3.10.x 或更高
    ```

## 克隆项目

```bash
git clone <repository-url> llm-rec-platform
cd llm-rec-platform
```

## 安装依赖

推荐使用虚拟环境：

=== "venv"

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/macOS
    # .venv\Scripts\activate   # Windows
    ```

=== "conda"

    ```bash
    conda create -n rec-platform python=3.10 -y
    conda activate rec-platform
    ```

安装项目及开发依赖：

```bash
pip install -e ".[dev]"
```

这会安装以下核心依赖：

| 类别 | 依赖 |
|------|------|
| Web 框架 | FastAPI, Uvicorn, Starlette |
| 数据校验 | Pydantic v2, pydantic-settings |
| 深度学习 | PyTorch, LightGBM |
| 向量检索 | Faiss |
| LLM | LangChain, LangGraph, OpenAI SDK |
| 存储 | Redis, PyMySQL, ClickHouse Driver |
| 监控 | Prometheus Client |

## 环境变量

项目通过 `${env:VAR_NAME:default}` 语法在 YAML 配置中引用环境变量，支持不设置时使用默认值。

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `APP_ENV` | `development` | 运行环境：`development` / `staging` / `production` |
| `REDIS_HOST` | `localhost` | Redis 地址 |
| `MYSQL_HOST` | `localhost` | MySQL 地址 |
| `CLICKHOUSE_HOST` | `localhost` | ClickHouse 地址 |
| `GLM_API_KEY` | _(空)_ | 智谱 API Key |
| `OPENAI_API_KEY` | _(空)_ | OpenAI API Key |

创建 `.env` 文件（可选）：

```bash
cat > .env << 'EOF'
APP_ENV=development
REDIS_HOST=localhost
MYSQL_HOST=localhost
CLICKHOUSE_HOST=localhost
EOF
```

!!! info "无需 LLM Key 也可启动"
    平台采用优雅降级设计——LLM 后端不可用时自动降级为 Mock 后端，不影响推荐链路运行。

## 验证安装

```bash
# 检查包是否可导入
python -c "from server.app import create_app; print('OK')"

# 检查配置加载
python -c "from configs.settings import get_settings; s = get_settings(); print(s.server.host, s.server.port)"
# 预期输出: 0.0.0.0 8000
```

## 下一步

- [第一个推荐请求](first-request.md) — 启动服务并发送请求
- [Docker 部署](docker-deploy.md) — 使用 Docker Compose 一键启动完整服务栈
