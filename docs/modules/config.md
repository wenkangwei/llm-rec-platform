# 配置系统

## 加载流程

```
app.yaml → 扫描 ${path:key} 引用 → 拓扑排序 → 加载子配置 → 环境覆盖 → 引用替换 → 校验
```

## 引用语法

| 语法 | 说明 | 示例 |
|------|------|------|
| `${path/key:field}` | 跨文件引用 | `${llm/llm.yaml:providers}` |
| `${env:VAR:default}` | 环境变量 | `${env:OPENAI_API_KEY:}` |

## 环境覆盖

```
configs/environments/
├── development.yaml    # APP_ENV=development
├── staging.yaml        # APP_ENV=staging
└── production.yaml     # APP_ENV=production
```

深度合并：环境配置覆盖默认值。

## ConfigLoader

```python
from configs.loader import ConfigLoader, init_config

config = init_config("development")
# 或
loader = ConfigLoader(env="production")
config = loader.load()
```

## Settings 单例

```python
from configs.settings import get_settings

settings = get_settings()
db_host = settings.raw["storage"]["redis"]["host"]
```

## 配置 Schema

Pydantic 校验：`AppConfig` 包含 `ServerConfig`、`StorageConfig`、`LLMConfig`、`PipelineConfig`、`FeatureConfig`、`MonitorConfig`、`ExperimentConfig`。
