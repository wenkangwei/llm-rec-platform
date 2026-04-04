"""LLM 路由器 — 多后端优先级调度 + 自动降级"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from llm.base import LLMBackend
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.router")


class _ProviderSlot:
    """单个 provider 槽位。"""

    def __init__(self, name: str, backend: LLMBackend, priority: int):
        self.name = name
        self.backend = backend
        self.priority = priority
        self.available = True
        self.last_check_ok: bool | None = None

    def __repr__(self):
        status = "ok" if self.available else "down"
        return f"<{self.name} priority={self.priority} {status}>"


class LLMRouter(LLMBackend):
    """LLM 多后端路由器。

    按 priority 排序，优先使用最高优先级的可用后端。
    请求失败时自动 fallback 到下一个可用后端。
    对下游完全透明 — 本身实现 LLMBackend 接口。

    Usage:
        router = LLMRouter(providers=[...], routing={...})
        await router.warmup()
        result = await router.generate("hello")
    """

    def __init__(self, providers: list[dict[str, Any]], routing: dict[str, Any] | None = None):
        routing = routing or {}
        self._fallback_on_error = routing.get("fallback_on_error", True)
        self._health_check_interval = routing.get("health_check_interval", 60)
        self._slots: list[_ProviderSlot] = []
        self._active_index: int = 0
        self._backend_configs: list[dict[str, Any]] = providers
        self._health_task: asyncio.Task | None = None

    @property
    def active_provider(self) -> str:
        if self._slots:
            return self._slots[self._active_index].name
        return "none"

    def get_status(self) -> dict[str, Any]:
        """返回所有 provider 状态，用于 API 查询。"""
        return {
            "active": self.active_provider,
            "providers": [
                {
                    "name": s.name,
                    "priority": s.priority,
                    "available": s.available,
                }
                for s in self._slots
            ],
        }

    # ===== Lifecycle =====

    async def warmup(self) -> None:
        """初始化所有 provider，按 priority 排序，选第一个可用的作为 active。"""
        from llm.factory import LLMFactory

        for cfg in self._backend_configs:
            try:
                backend = LLMFactory.create_from_provider(cfg)
                await backend.warmup()
                priority = cfg.get("priority", 99)
                slot = _ProviderSlot(
                    name=cfg.get("name", "unknown"),
                    backend=backend,
                    priority=priority,
                )
                # 健康检查
                slot.available = await backend.health_check()
                slot.last_check_ok = slot.available
                self._slots.append(slot)
                status = "available" if slot.available else "unavailable"
                logger.info(f"LLM provider 初始化: {slot.name}", status=status, priority=priority)
            except Exception as e:
                logger.warning(f"LLM provider 初始化失败: {cfg.get('name', 'unknown')}", error=str(e))
                # 创建 slot 但标记不可用
                from llm.backends.mock_backend import MockBackend
                slot = _ProviderSlot(
                    name=cfg.get("name", "unknown"),
                    backend=MockBackend(),
                    priority=cfg.get("priority", 99),
                )
                slot.available = False
                self._slots.append(slot)

        # 按 priority 排序
        self._slots.sort(key=lambda s: s.priority)

        # 找第一个可用的
        self._active_index = 0
        for i, slot in enumerate(self._slots):
            if slot.available:
                self._active_index = i
                break

        if self._slots:
            active = self._slots[self._active_index]
            logger.info(
                f"LLM 路由器就绪",
                active=active.name,
                total_providers=len(self._slots),
                available=sum(1 for s in self._slots if s.available),
            )

        # 启动后台健康检查
        if self._health_check_interval > 0 and len(self._slots) > 1:
            self._health_task = asyncio.create_task(self._periodic_health_check())

    async def shutdown(self) -> None:
        """关闭所有后端。"""
        if self._health_task:
            self._health_task.cancel()
            self._health_task = None

        for slot in self._slots:
            try:
                await slot.backend.shutdown()
            except Exception as e:
                logger.debug(f"关闭 provider 异常: {slot.name}", error=str(e))

    async def health_check(self) -> bool:
        """检查当前活跃后端是否可用。"""
        if not self._slots:
            return False
        return self._slots[self._active_index].available

    # ===== LLMBackend 接口 =====

    async def generate(self, prompt: str, **kwargs) -> str:
        """生成文本，自动 fallback。"""
        return await self._dispatch("generate", prompt, **kwargs)

    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """流式生成，自动 fallback。"""
        slot = self._get_active()
        try:
            async for chunk in slot.backend.generate_stream(prompt, **kwargs):
                yield chunk
            return
        except Exception as e:
            logger.warning(f"provider {slot.name} 流式生成失败", error=str(e))
            if not self._fallback_on_error:
                yield f"[Error: {e}]"
                return

        # fallback
        next_slot = self._find_next_available(self._active_index)
        if next_slot:
            logger.info(f"流式生成 fallback: {slot.name} → {next_slot.name}")
            self._active_index = self._slots.index(next_slot)
            async for chunk in next_slot.backend.generate_stream(prompt, **kwargs):
                yield chunk
        else:
            yield f"[Error: all providers unavailable]"

    async def embed(self, text: str | list[str]) -> list[list[float]]:
        """生成 embedding，自动 fallback。"""
        return await self._dispatch("embed", text)

    # ===== 内部方法 =====

    def _get_active(self) -> _ProviderSlot:
        if not self._slots:
            raise RuntimeError("没有可用的 LLM provider")
        return self._slots[self._active_index]

    async def _dispatch(self, method: str, *args, **kwargs) -> Any:
        """统一调度，带 fallback。"""
        slot = self._get_active()
        try:
            fn = getattr(slot.backend, method)
            return await fn(*args, **kwargs)
        except Exception as e:
            logger.warning(f"provider {slot.name} {method} 失败", error=str(e))
            slot.available = False

            if not self._fallback_on_error:
                # embed 返回 [[]]，generate 返回 ""
                return [[]] if method == "embed" else ""

            next_slot = self._find_next_available(self._active_index)
            if next_slot:
                logger.info(f"fallback: {slot.name} → {next_slot.name} ({method})")
                self._active_index = self._slots.index(next_slot)
                fn = getattr(next_slot.backend, method)
                try:
                    return await fn(*args, **kwargs)
                except Exception as e2:
                    logger.error(f"fallback provider {next_slot.name} 也失败了", error=str(e2))
                    return [[]] if method == "embed" else ""

            logger.error("所有 LLM provider 不可用")
            return [[]] if method == "embed" else ""

    def _find_next_available(self, from_index: int) -> _ProviderSlot | None:
        """从 from_index 之后找下一个可用的 slot（循环查找）。"""
        n = len(self._slots)
        for offset in range(1, n):
            idx = (from_index + offset) % n
            if self._slots[idx].available:
                return self._slots[idx]
        return None

    async def _periodic_health_check(self) -> None:
        """后台定期检查不可用的 provider 是否恢复。"""
        try:
            while True:
                await asyncio.sleep(self._health_check_interval)
                for slot in self._slots:
                    if not slot.available:
                        try:
                            ok = await slot.backend.health_check()
                            if ok:
                                slot.available = True
                                slot.last_check_ok = True
                                logger.info(f"provider 恢复: {slot.name}")
                        except Exception:
                            slot.last_check_ok = False
        except asyncio.CancelledError:
            pass

    def select_provider(self, name: str) -> bool:
        """手动切换到指定 provider。"""
        for i, slot in enumerate(self._slots):
            if slot.name == name:
                if slot.available:
                    self._active_index = i
                    logger.info(f"手动切换 provider: {name}")
                    return True
                else:
                    logger.warning(f"provider {name} 当前不可用")
                    return False
        logger.warning(f"provider 不存在: {name}")
        return False
