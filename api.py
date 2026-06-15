"""FastAPI 标准接口 - 提供可被前端或第三方系统调用的 Agent API"""

from typing import Dict
import os
import time
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.agent import MealRecommenderAgent
from agent.logging_config import get_logger


logger = get_logger(__name__)
app = FastAPI(
    title="吃什么推荐 Agent API",
    description="面向中国大学生的餐饮推荐 Agent 标准 API。",
    version="1.1.0",
)

# CORS 配置（可通过环境变量控制）
_cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
_origins = [o.strip() for o in _cors_origins.split(",")] if _cors_origins else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 会话管理（带 TTL 自动清理）
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "3600"))  # 默认 1 小时
MAX_SESSIONS = int(os.getenv("MAX_SESSIONS", "200"))


class _SessionEntry:
    """单个会话条目，记录 agent 和最后活跃时间"""

    __slots__ = ("agent", "last_active")

    def __init__(self, agent: MealRecommenderAgent):
        self.agent = agent
        self.last_active = time.time()

    def touch(self):
        self.last_active = time.time()


_sessions: Dict[str, _SessionEntry] = {}


def _evict_expired():
    """清理过期和超限会话"""
    now = time.time()
    expired = [
        sid for sid, entry in _sessions.items()
        if now - entry.last_active > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        entry = _sessions.pop(sid, None)
        if entry and entry.agent._session:
            entry.agent._session.cleanup()
        logger.info("evicted_expired_session session_id=%s", sid)

    # 如果仍然超过上限，移除最旧的
    while len(_sessions) > MAX_SESSIONS:
        oldest_sid = min(_sessions, key=lambda k: _sessions[k].last_active)
        entry = _sessions.pop(oldest_sid, None)
        if entry and entry.agent._session:
            entry.agent._session.cleanup()
        logger.info("evicted_overflow_session session_id=%s", oldest_sid)


class ChatRequest(BaseModel):
    """聊天请求。"""

    message: str = Field(..., min_length=1, description="用户输入")
    session_id: str | None = Field(None, description="会话 ID，不传则自动创建")


class ChatResponse(BaseModel):
    """聊天响应。"""

    session_id: str
    response: str
    history: list[dict[str, str]]
    is_ready: bool


class ResetRequest(BaseModel):
    """重置请求。"""

    session_id: str = Field(..., description="需要重置的会话 ID")


class HealthResponse(BaseModel):
    """健康检查响应。"""

    status: str
    active_sessions: int


def _get_or_create_agent(session_id: str | None = None) -> tuple[str, MealRecommenderAgent]:
    _evict_expired()

    if session_id and session_id in _sessions:
        entry = _sessions[session_id]
        entry.touch()
        return session_id, entry.agent

    new_session_id = session_id or str(uuid.uuid4())
    agent = MealRecommenderAgent()
    _sessions[new_session_id] = _SessionEntry(agent)
    logger.info("created_session session_id=%s ready=%s", new_session_id, agent.is_ready)
    return new_session_id, agent


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """健康检查。"""
    return HealthResponse(status="ok", active_sessions=len(_sessions))


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """发送消息给 Agent。"""
    session_id, agent = _get_or_create_agent(req.session_id)
    logger.info("chat_request session_id=%s message=%s", session_id, req.message)

    try:
        response = agent.invoke(req.message)
    except Exception as exc:
        logger.exception("chat_failed session_id=%s", session_id)
        raise HTTPException(status_code=500, detail="Agent 调用失败") from exc

    logger.info("chat_response session_id=%s ready=%s response_len=%s", session_id, agent.is_ready, len(response))
    return ChatResponse(
        session_id=session_id,
        response=response,
        history=agent.get_chat_history(),
        is_ready=agent.is_ready,
    )


@app.post("/reset", response_model=ChatResponse)
def reset(req: ResetRequest) -> ChatResponse:
    """重置指定会话。"""
    if req.session_id not in _sessions:
        raise HTTPException(status_code=404, detail="session_id 不存在")

    entry = _sessions[req.session_id]
    entry.agent.reset()
    entry.touch()
    logger.info("reset_session session_id=%s", req.session_id)
    return ChatResponse(
        session_id=req.session_id,
        response="已重置，可以重新开始推荐。",
        history=entry.agent.get_chat_history(),
        is_ready=entry.agent.is_ready,
    )


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, str]:
    """删除指定会话。"""
    entry = _sessions.pop(session_id, None)
    if entry is None:
        raise HTTPException(status_code=404, detail="session_id 不存在")

    if entry.agent._session:
        entry.agent._session.cleanup()
    logger.info("deleted_session session_id=%s", session_id)
    return {"status": "deleted", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
