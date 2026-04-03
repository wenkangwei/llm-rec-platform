"""Prompt 模板管理"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from utils.logger import get_struct_logger

logger = get_struct_logger("llm.prompt.manager")

# 模板目录
_TEMPLATE_DIR = Path(__file__).parent / "templates"


class PromptManager:
    """Prompt 模板管理：加载、渲染、版本管理。"""

    def __init__(self, template_dir: Path | None = None):
        self._template_dir = template_dir or _TEMPLATE_DIR
        self._cache: dict[str, str] = {}

    def load(self, template_name: str) -> str:
        """加载模板。"""
        if template_name in self._cache:
            return self._cache[template_name]

        path = self._template_dir / f"{template_name}.txt"
        if path.exists():
            content = path.read_text(encoding="utf-8")
            self._cache[template_name] = content
            return content

        logger.warning(f"模板不存在: {template_name}")
        return ""

    def render(self, template_name: str, **kwargs: Any) -> str:
        """渲染模板（简单变量替换）。"""
        template = self.load(template_name)
        if not template:
            return ""

        for key, value in kwargs.items():
            template = template.replace(f"{{{{{key}}}}}", str(value))

        return template

    def register(self, template_name: str, content: str) -> None:
        """注册内存模板。"""
        self._cache[template_name] = content

    def list_templates(self) -> list[str]:
        """列出所有可用模板。"""
        templates = set(self._cache.keys())
        if self._template_dir.exists():
            for f in self._template_dir.glob("*.txt"):
                templates.add(f.stem)
        return sorted(templates)
