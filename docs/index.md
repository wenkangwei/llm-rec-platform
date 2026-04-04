# LLM 推荐系统平台

**LLM 驱动的智能推荐系统运维平台**

---

## 核心特性

| 特性 | 说明 |
|------|------|
| **5 级推荐漏斗** | 召回 → 粗排 → 精排 → 重排 → 混排，配置驱动的多阶段流水线 |
| **LLM 多厂商路由** | OpenAI / vLLM / Ollama 多后端优先级调度，自动故障降级 |
| **ReAct Agent 智能运维** | 自然语言对话控制推荐策略、查询监控指标、诊断系统状态 |
| **全链路追踪** | 每请求 Pipeline Trace，阶段延迟 / 召回覆盖率 / 物品打分明细 |
| **A/B 实验框架** | 配置化实验分流，变体级别参数覆盖，无缝集成推荐链路 |
| **特征平台** | 特征注册中心 + 离线/在线特征引擎 + 用户画像管理 |

## 技术栈

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.2%2B-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.2%2B-029E73)](https://lightgbm.readthedocs.io/)
[![Faiss](https://img.shields.io/badge/Faiss-1.7%2B-FF6F00)](https://github.com/facebookresearch/faiss)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![ClickHouse](https://img.shields.io/badge/ClickHouse-24.1-FFCC00)](https://clickhouse.com/)
[![vLLM/Ollama](https://img.shields.io/badge/vLLM%2FOllama-LLM-76B900)](https://github.com/vllm-project/vllm)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)

## 系统架构

```mermaid
flowchart TB
    User(["用户请求"])

    subgraph Server["FastAPI 服务层"]
        Middleware["中间件<br/>CORS / 日志 / 限流 / RequestID"]
        Router["路由分发"]
    end

    subgraph Pipeline["PipelineExecutor 推荐流水线"]
        direction LR
        Recall["召回<br/>Recall"] --> PreRank["粗排<br/>PreRank"]
        PreRank --> Rank["精排<br/>Rank"]
        Rank --> ReRank["重排<br/>ReRank"]
        ReRank --> Mixer["混排<br/>Mixer"]
    end

    subgraph Parallel["并行服务"]
        Agent["LLM Agent<br/>ReAct 智能运维"]
        Chat["Chat 会话<br/>SSE / WebSocket"]
        Feature["特征平台<br/>注册 / 引擎 / 画像"]
        Monitor["监控追踪<br/>Trace / Metrics"]
    end

    subgraph Storage["存储层"]
        Redis[("Redis")]
        MySQL[("MySQL")]
        ClickHouse[("ClickHouse")]
    end

    subgraph LLM["LLM 推理"]
        Router_LLM["多厂商路由<br/>Priority + Fallback"]
        OpenAI["OpenAI"]
        vLLM["vLLM"]
        Ollama["Ollama"]
    end

    User --> Middleware --> Router
    Router --> Pipeline
    Router --> Agent
    Router --> Chat
    Router --> Monitor

    Pipeline --> Feature
    Pipeline --> Storage
    Agent --> Router_LLM
    Chat --> Router_LLM
    Router_LLM --> OpenAI
    Router_LLM --> vLLM
    Router_LLM --> Ollama

    Pipeline --> Response(["推荐响应"])
```

## 快速导航

| 文档 | 说明 |
|------|------|
| [环境安装](quickstart/installation.md) | 克隆项目、安装依赖、环境变量配置 |
| [第一个请求](quickstart/first-request.md) | 启动服务，发送推荐请求和对话请求 |
| [Docker 部署](quickstart/docker-deploy.md) | 一键启动完整服务栈（含监控） |
| [系统总览](architecture/overview.md) | 高层架构图、模块职责、设计原则 |
| [推荐流水线](architecture/pipeline.md) | 5 级漏斗详解、类图、配置加载机制 |
