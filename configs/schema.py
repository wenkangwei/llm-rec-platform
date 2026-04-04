"""配置 Schema 校验 — Pydantic 模型定义"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    log_level: str = "INFO"


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    pool_size: int = 10
    timeout_ms: int = 100


class MySQLConfig(BaseModel):
    host: str = "localhost"
    port: int = 3306
    user: str = "rec_user"
    password: str = "rec_pass"
    database: str = "rec_platform"
    pool_size: int = 5


class ClickHouseConfig(BaseModel):
    host: str = "localhost"
    port: int = 9000
    user: str = "default"
    password: str = ""
    database: str = "rec_monitor"


class StorageConfig(BaseModel):
    redis: RedisConfig = Field(default_factory=RedisConfig)
    mysql: MySQLConfig = Field(default_factory=MySQLConfig)
    clickhouse: ClickHouseConfig = Field(default_factory=ClickHouseConfig)


class ModelConfig(BaseModel):
    name: str
    version: str = "v1"
    type: str  # recall, rank, prerank
    backend: str = "torch"
    path: str = ""
    input_dim: int = 128


class PipelineStageConfig(BaseModel):
    name: str
    class_path: str = Field(alias="class")
    timeout_ms: int = 50


class RecallChannelConfig(BaseModel):
    enabled: bool = True
    weight: float = 0.1
    class_path: str = Field(alias="class")
    params: dict[str, Any] = Field(default_factory=dict)


class LLMBackendConfig(BaseModel):
    type: str = "openai_compatible"
    base_url: str = "http://localhost:8001/v1"
    api_key: str = "EMPTY"
    timeout_sec: int = 30
    max_retries: int = 2


class LLMProviderConfig(BaseModel):
    """单个 LLM 厂商配置。"""
    name: str
    type: str = "openai_compatible"
    base_url: str = ""
    api_key: str = "EMPTY"
    chat_model: str = "qwen2.5:7b"
    embed_model: str = ""
    timeout_sec: int = 30
    max_retries: int = 2
    priority: int = 1
    protocol: str = "grpc"  # triton 专用


class LLMRoutingConfig(BaseModel):
    """LLM 路由策略配置。"""
    strategy: str = "priority"
    health_check_interval: int = 60
    fallback_on_error: bool = True


class LLMConfig(BaseModel):
    backend: LLMBackendConfig = Field(default_factory=LLMBackendConfig)
    providers: list[LLMProviderConfig] = Field(default_factory=list)
    routing: LLMRoutingConfig = Field(default_factory=LLMRoutingConfig)


class MonitorConfig(BaseModel):
    enabled: bool = True
    sinks: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class ExperimentVariantConfig(BaseModel):
    name: str
    traffic_percent: float = 50.0
    config: dict[str, Any] = Field(default_factory=dict)


class ExperimentDefConfig(BaseModel):
    id: str
    name: str
    layer: str = "default"
    enabled: bool = True
    variants: list[ExperimentVariantConfig] = Field(default_factory=list)


class ExperimentConfig(BaseModel):
    experiments: list[ExperimentDefConfig] = Field(default_factory=list)


class AppConfig(BaseModel):
    """顶层配置 Schema，用于校验加载后的完整配置。"""
    server: ServerConfig = Field(default_factory=ServerConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    models: dict[str, ModelConfig] = Field(default_factory=dict)
    pipeline: dict[str, Any] = Field(default_factory=dict)
    features: dict[str, Any] = Field(default_factory=dict)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    monitor: MonitorConfig = Field(default_factory=MonitorConfig)
    experiment: ExperimentConfig = Field(default_factory=ExperimentConfig)


def validate_config(raw_config: dict[str, Any]) -> AppConfig:
    """校验配置，返回类型安全的 AppConfig。"""
    return AppConfig(**raw_config)
