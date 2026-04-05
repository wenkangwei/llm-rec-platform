"""Web Chat UI 路由"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
_INDEX_HTML = _STATIC_DIR / "index.html"


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
@router.get("/chat", response_class=HTMLResponse, include_in_schema=False)
async def chat_ui():
    """返回 Web Chat UI 页面。"""
    if _INDEX_HTML.exists():
        return _INDEX_HTML.read_text(encoding="utf-8")
    return HTMLResponse("<h1>UI not found</h1>", status_code=404)
