"""ChatSessionManager — 对话会话管理"""

from __future__ import annotations

import json
import re
import time
from typing import Any

from llm.agent.base import AgentResult, AgentTask, Tool
from llm.agent.executor import ReActAgent
from llm.agent.tools.pipeline_control import PipelineControlTool
from llm.agent.tools.monitor_query import MonitorQueryTool
from llm.agent.tools.config_update import ConfigUpdateTool
from llm.base import LLMBackend
from llm.chat.schemas import ChatAction, ChatMessage, ChatSession, Intent, IntentType
from llm.prompt.manager import get_prompt_manager
from utils.hash import generate_request_id
from utils.logger import get_struct_logger

logger = get_struct_logger("llm.chat.manager")


_DEFAULT_SESSION_TTL = 3600  # 会话默认过期时间（秒）
_MAX_SESSIONS = 1000  # 最大会话数


class ChatSessionManager:
    """对话会话管理器：意图识别 → 工具调用 → 结果反馈。"""

    def __init__(self, llm: LLMBackend, pipeline_state: dict[str, Any] | None = None,
                 session_ttl: int = _DEFAULT_SESSION_TTL, max_sessions: int = _MAX_SESSIONS):
        self._llm = llm
        self._sessions: dict[str, ChatSession] = {}
        self._pipeline_state = pipeline_state or {}
        self._metrics_store: dict[str, Any] = {}
        self._session_ttl = session_ttl
        self._max_sessions = max_sessions

        # 初始化工具
        self._tools: list[Tool] = [
            PipelineControlTool(pipeline_state),
            MonitorQueryTool(self._metrics_store),
            ConfigUpdateTool(),
        ]

        # 初始化 ReAct Agent
        self._agent = ReActAgent(llm, self._tools, max_iterations=5)

    def create_session(self, user_id: str) -> ChatSession:
        """创建新会话。"""
        self.cleanup_expired_sessions()

        # 达到上限时淘汰最旧会话
        if len(self._sessions) >= self._max_sessions:
            oldest_id = min(self._sessions, key=lambda k: self._sessions[k].updated_at)
            del self._sessions[oldest_id]

        session_id = generate_request_id()
        now = time.time()
        session = ChatSession(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        """获取会话（已过期返回 None）。"""
        session = self._sessions.get(session_id)
        if session and time.time() - session.updated_at > self._session_ttl:
            del self._sessions[session_id]
            return None
        return session

    def cleanup_expired_sessions(self) -> int:
        """清理过期会话，返回清理数量。"""
        now = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - s.updated_at > self._session_ttl
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)

    async def chat(self, session_id: str, user_message: str) -> str:
        """处理用户消息，返回回复。"""
        session = self._sessions.get(session_id)
        if not session:
            return "会话不存在，请先创建会话。"

        # 记录用户消息
        session.messages.append(ChatMessage(
            role="user", content=user_message, timestamp=time.time()
        ))

        # 意图识别（LLM 语义识别，失败时降级到关键词）
        intent = await self._classify_intent_llm(user_message)
        logger.info(f"意图识别: {intent.type.value}", confidence=intent.confidence)

        # 执行动作
        if intent.type == IntentType.UNKNOWN:
            # 直接用 LLM 回答
            prompt = get_prompt_manager().render("chat_assistant", user_question=user_message)
            answer = await self._llm.generate(prompt)
        else:
            # 通过 Agent 执行
            task = AgentTask(
                task_id=generate_request_id(),
                description=user_message,
                context={"intent": intent.type.value, **intent.entities},
            )
            result = await self._agent.run(task)
            answer = result.answer if result.answer else str(result.steps)

        # 记录助手回复
        session.messages.append(ChatMessage(
            role="assistant", content=answer, timestamp=time.time()
        ))
        session.updated_at = time.time()

        return answer

    async def _classify_intent_llm(self, message: str) -> Intent:
        """基于 LLM 的语义意图分类，失败时降级到关键词匹配。"""
        try:
            prompt = get_prompt_manager().render(
                "intent_classify", user_message=message
            )
            response = await self._llm.generate(prompt)
            return self._parse_intent_response(response, message)
        except Exception as e:
            logger.warning(f"LLM 意图识别失败，降级到关键词匹配: {e}")
            return self._classify_intent_keyword(message)

    def _parse_intent_response(self, response: str, message: str) -> Intent:
        """解析 LLM 返回的意图 JSON。"""
        # 提取 JSON（兼容 LLM 输出多余文本的情况）
        json_match = re.search(r'\{[^}]+\}', response)
        if not json_match:
            logger.warning(f"无法解析意图响应: {response[:200]}")
            return self._classify_intent_keyword(message)

        try:
            data = json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.warning(f"意图 JSON 解析失败: {json_match.group()}")
            return self._classify_intent_keyword(message)

        intent_str = data.get("intent", "unknown")
        confidence = float(data.get("confidence", 0.0))
        reason = data.get("reason", "")

        # 映射到 IntentType
        intent_map = {
            "strategy": IntentType.STRATEGY,
            "monitor": IntentType.MONITOR,
            "debug": IntentType.DEBUG,
            "config": IntentType.CONFIG,
            "unknown": IntentType.UNKNOWN,
        }
        intent_type = intent_map.get(intent_str, IntentType.UNKNOWN)

        entities = self._extract_entities(message)
        logger.debug(f"LLM 意图: {intent_type.value}, confidence={confidence}, reason={reason}")
        return Intent(type=intent_type, confidence=confidence, entities=entities)

    @staticmethod
    def _classify_intent_keyword(message: str) -> Intent:
        """关键词兜底的意图分类。"""
        _KEYWORDS: dict[IntentType, list[str]] = {
            IntentType.STRATEGY: [
                "关闭", "启用", "开启", "调整", "权重", "召回", "排序",
                "切换", "策略", "通道", "模型",
            ],
            IntentType.MONITOR: [
                "延迟", "P99", "QPS", "覆盖率", "指标", "监控",
                "性能", "耗时", "正常", "异常",
            ],
            IntentType.DEBUG: [
                "分析", "为什么", "偏少", "推荐结果", "诊断", "调试",
                "用户", "问题",
            ],
            IntentType.CONFIG: [
                "配置", "版本", "回滚", "实验", "A/B", "参数",
                "环境",
            ],
        }

        scores: dict[IntentType, int] = {}
        for intent_type, keywords in _KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in message)
            if score > 0:
                scores[intent_type] = score

        if not scores:
            return Intent(type=IntentType.UNKNOWN, confidence=0.0)

        best_intent = max(scores, key=scores.get)
        total = sum(scores.values())
        confidence = scores[best_intent] / total if total > 0 else 0.0
        return Intent(type=best_intent, confidence=confidence)

    @staticmethod
    def _extract_entities(message: str) -> dict[str, Any]:
        """简单实体提取。"""
        import re
        entities: dict[str, Any] = {}

        # 提取用户 ID
        user_match = re.search(r"用户\s*(\w+)", message)
        if user_match:
            entities["user_id"] = user_match.group(1)

        # 提取数字
        num_match = re.search(r"([\d.]+)", message)
        if num_match:
            entities["value"] = float(num_match.group(1))

        return entities

    def update_metrics(self, metrics: dict[str, Any]) -> None:
        """更新监控指标。"""
        self._metrics_store.update(metrics)
