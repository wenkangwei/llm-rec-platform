"""LLM Agent 对话接口 — HTTP SSE + WebSocket"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.websockets import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from utils.logger import get_struct_logger

logger = get_struct_logger("routes.chat")

router = APIRouter()


class ChatRequest(BaseModel):
    """HTTP 对话请求。"""
    session_id: str | None = None
    user_id: str = "admin"
    message: str


class ChatHTTPResponse(BaseModel):
    """HTTP 对话响应。"""
    session_id: str
    reply: str


@router.post("/chat", response_model=ChatHTTPResponse)
async def chat_http(req: ChatRequest, request: Request) -> ChatHTTPResponse:
    """HTTP 对话接口。

    通过自然语言控制推荐链路策略和查询监控指标。
    """
    manager = getattr(request.app.state, "chat_manager", None)
    if not manager:
        return ChatHTTPResponse(session_id="error", reply="对话服务未初始化")

    # 获取或创建会话
    session = None
    if req.session_id:
        session = manager.get_session(req.session_id)
    if not session:
        session = manager.create_session(req.user_id)

    # 处理消息
    reply = await manager.chat(session.session_id, req.message)

    return ChatHTTPResponse(session_id=session.session_id, reply=reply)


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request) -> StreamingResponse:
    """SSE 流式对话接口。"""
    manager = getattr(request.app.state, "chat_manager", None)
    if not manager:
        return StreamingResponse(
            _sse_error("对话服务未初始化"),
            media_type="text/event-stream",
        )

    session = None
    if req.session_id:
        session = manager.get_session(req.session_id)
    if not session:
        session = manager.create_session(req.user_id)

    async def generate():
        yield _sse_event("session_id", session.session_id)
        reply = await manager.chat(session.session_id, req.message)
        # 模拟流式输出
        chunk_size = 20
        for i in range(0, len(reply), chunk_size):
            yield _sse_event("chunk", reply[i:i + chunk_size])
            await asyncio.sleep(0.05)
        yield _sse_event("done", "")

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    """WebSocket 实时对话接口。

    支持自然语言实时交互控制链路策略。
    """
    await websocket.accept()
    session_id = None
    chat_manager = getattr(websocket.app.state, "chat_manager", None)

    if not chat_manager:
        await websocket.send_json({"error": "对话服务未初始化"})
        await websocket.close()
        return

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"error": "无效的 JSON"})
                continue

            user_id = msg.get("user_id", "admin")
            message = msg.get("message", "")

            if not message:
                await websocket.send_json({"error": "消息不能为空"})
                continue

            # 创建或获取会话
            if not session_id:
                session = chat_manager.create_session(user_id)
                session_id = session.session_id
                await websocket.send_json({"type": "session_created", "session_id": session_id})

            # 处理消息
            reply = await chat_manager.chat(session_id, message)
            await websocket.send_json({"type": "reply", "content": reply})

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开: {session_id}")


def _sse_event(event: str, data: str) -> str:
    return f"event: {event}\ndata: {json.dumps({'content': data})}\n\n"


async def _sse_error(msg: str):
    yield _sse_event("error", msg)
