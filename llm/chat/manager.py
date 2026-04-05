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
from llm.agent.tools.db_query import DBQueryTool
from llm.agent.tools.recommend_test import RecommendTestTool
from llm.base import LLMBackend
from llm.chat.cache import QueryCache
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
                 mysql_store=None,
                 session_ttl: int = _DEFAULT_SESSION_TTL, max_sessions: int = _MAX_SESSIONS):
        self._llm = llm
        self._sessions: dict[str, ChatSession] = {}
        self._pipeline_state = pipeline_state or {}
        self._metrics_store: dict[str, Any] = {}
        self._session_ttl = session_ttl
        self._max_sessions = max_sessions

        # 查询缓存
        self._cache = QueryCache(max_size=200, ttl_seconds=300)

        # 初始化工具
        self._tools: list[Tool] = [
            PipelineControlTool(pipeline_state),
            MonitorQueryTool(self._metrics_store),
            ConfigUpdateTool(),
            DBQueryTool(mysql_store),
            RecommendTestTool(),
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

        # 缓存检查（最先执行）
        cached = self._cache.get(user_message)
        if cached:
            session.messages.append(ChatMessage(
                role="assistant", content=cached, timestamp=time.time()
            ))
            session.updated_at = time.time()
            return cached

        # 快速路径：推荐测试直达
        rec_direct = await self._try_recommend_direct(user_message)
        if rec_direct is not None:
            answer = rec_direct
        else:
            # 快速路径：数据库查询直达，跳过 ReAct 循环
            db_direct = await self._try_db_direct(user_message)
            if db_direct is not None:
                answer = db_direct
            else:
                # 关键词先匹配，命中高置信度直接走 agent
                kw_intent = self._classify_intent_keyword(user_message)

                if kw_intent.confidence >= 0.5:
                    intent = kw_intent
                    logger.info(f"意图识别(关键词): {intent.type.value}", confidence=intent.confidence)
                else:
                    intent = await self._classify_intent_llm(user_message)
                    logger.info(f"意图识别(LLM): {intent.type.value}", confidence=intent.confidence)

                if intent.type == IntentType.UNKNOWN:
                    prompt = get_prompt_manager().render("chat_assistant", user_question=user_message)
                    answer = await self._llm.generate(prompt)
                else:
                    task = AgentTask(
                        task_id=generate_request_id(),
                        description=user_message,
                        context={"intent": intent.type.value, **intent.entities},
                    )
                    result = await self._agent.run(task)
                    answer = result.answer if result.answer else str(result.steps)

        # 缓存写入
        self._cache.put(user_message, answer)

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
                "用户", "问题", "数据库", "内容池", "数据", "多少条",
                "内容", "统计", "分布", "质量", "评分", "来源",
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

    async def _try_db_direct(self, message: str) -> str | None:
        """检测数据库相关消息，直接执行 db_query 工具，跳过 ReAct 循环。

        返回格式化的结果字符串，或 None 表示不走直达路径。
        """
        _DB_KEYWORDS = [
            "数据库", "内容池", "多少条", "多少内容", "内容数量",
            "数据统计", "数据分布", "来源分布", "质量分布",
            "内容概览", "数据概览", "最近入库",
            "即梦", "rss", "来源的内容",
        ]
        if not any(kw in message for kw in _DB_KEYWORDS):
            return None

        # 找 db_query 工具
        db_tool = None
        for t in self._tools:
            if t.name() == "db_query":
                db_tool = t
                break
        if not db_tool:
            return None

        # 确定查询类型
        query_map = {
            "多少": "items_count", "数量": "items_count", "分布": "items_count",
            "统计": "items_stats", "概览": "items_count", "最近": "items_recent",
            "来源": "items_count", "质量": "items_count",
        }
        query_type = "items_count"  # default
        for kw, qt in query_map.items():
            if kw in message:
                query_type = qt

        # 检测来源类型
        source = ""
        for s in ("rss", "jimeng", "即梦", "web", "hot_keyword"):
            if s in message.lower() or s in message:
                source = "jimeng" if s == "即梦" else s
                if source:
                    query_type = "items_by_source"
                break

        try:
            result = await db_tool.execute({"query": query_type, "source": source})
        except Exception:
            return None

        if not result or "error" in result:
            return None

        # 格式化输出
        return self._format_db_result(result, message)

    @staticmethod
    def _format_db_result(result: dict, message: str) -> str:
        """将 db_query 结果格式化为友好文本。"""
        data = result.get("data", [])
        if not data:
            return "数据库中暂无数据。"

        lines = []
        row_count = result.get("row_count", len(data))

        # 判断结果类型并格式化
        if "cnt" in (data[0] if data else {}) and "source_type" in (data[0] if data else {}):
            lines.append(f"内容池共有 {sum(r.get('cnt', 0) for r in data)} 条内容，分布如下：")
            for r in data:
                avg = r.get("avg_score", "")
                score_str = f"，平均质量 {avg}" if avg else ""
                lines.append(f"  - {r.get('source_type', '?')}: {r.get('cnt', 0)} 条{score_str}")
        elif "total" in (data[0] if data else {}):
            r = data[0]
            lines.append(f"内容池统计：共 {r.get('total', 0)} 条内容")
            if "rewritten_count" in r:
                lines.append(f"  - 已改写: {r['rewritten_count']}")
            if "avg_quality" in r:
                lines.append(f"  - 平均质量分: {r['avg_quality']}")
            if "total_exposures" in r:
                lines.append(f"  - 总曝光: {r['total_exposures']}")
        else:
            # 通用表格格式
            lines.append(f"查询到 {row_count} 条记录：")
            for i, r in enumerate(data[:10], 1):
                parts = [f"{k}={v}" for k, v in r.items() if v is not None and k != "sql"]
                lines.append(f"  {i}. {' | '.join(parts)}")
            if row_count > 10:
                lines.append(f"  ... 共 {row_count} 条")

        return "\n".join(lines)

    async def _try_recommend_direct(self, message: str) -> str | None:
        """检测推荐测试相关消息，直接执行推荐请求，跳过 ReAct 循环。"""
        _REC_KEYWORDS = [
            "推荐测试", "测试推荐", "跑一次推荐", "推荐请求",
            "试一下推荐", "推荐效果", "跑个推荐", "执行推荐",
        ]
        if not any(kw in message for kw in _REC_KEYWORDS):
            return None

        # 找 recommend_test 工具
        rec_tool = None
        for t in self._tools:
            if t.name() == "recommend_test":
                rec_tool = t
                break
        if not rec_tool:
            return None

        # 提取参数
        params: dict[str, Any] = {}
        # 提取用户 ID
        user_match = re.search(r"用户\s*(\w+)", message)
        if user_match:
            params["user_id"] = user_match.group(1)
        # 提取场景
        for scene_name in ("home_feed", "follow_feed", "community_feed"):
            if scene_name in message:
                params["scene"] = scene_name
                break
        # 提取数量
        num_match = re.search(r"(\d+)\s*条", message)
        if num_match:
            params["num"] = min(int(num_match.group(1)), 50)

        try:
            result = await rec_tool.execute(params)
        except Exception as e:
            return f"推荐测试执行失败: {e}"

        if not result or "error" in result:
            return f"推荐测试失败: {result.get('error', '未知错误')}" if result else "推荐测试失败"

        return self._format_recommend_result(result)

    @staticmethod
    def _format_recommend_result(result: dict) -> str:
        """将推荐测试结果格式化为友好文本。"""
        lines = []
        latency = result.get("latency_ms", 0)
        total = result.get("total_candidates", 0)
        degraded = result.get("degraded", False)
        experiment = result.get("experiment_id", "")

        lines.append(f"推荐测试完成 | 总耗时: {latency}ms | 候选数: {total}")
        if experiment:
            lines.append(f"  实验: {experiment} / {result.get('variant', '')}")
        if degraded:
            lines.append(f"  降级阶段: {', '.join(result.get('degraded_stages', []))}")

        # 阶段指标
        stage_metrics = result.get("stage_metrics", [])
        if stage_metrics:
            lines.append("  各阶段耗时:")
            for sm in stage_metrics:
                lines.append(
                    f"    {sm['stage']}: {sm['latency_ms']}ms "
                    f"(输入: {sm['input']} → 输出: {sm['output']})"
                )

        # 推荐结果
        items = result.get("items", [])
        if items:
            lines.append(f"  Top-{len(items)} 推荐:")
            for i, item in enumerate(items, 1):
                lines.append(
                    f"    {i}. {item['item_id']} | "
                    f"分数: {item['score']} | 来源: {item['source']}"
                )
        else:
            lines.append("  未产生推荐结果")

        return "\n".join(lines)
