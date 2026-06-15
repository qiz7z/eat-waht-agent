"""FastAPI 标准接口 - 提供可被前端或第三方系统调用的 Agent API"""

from typing import Dict
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
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_sessions: Dict[str, MealRecommenderAgent] = {}


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
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]

    new_session_id = session_id or str(uuid.uuid4())
    agent = MealRecommenderAgent()
    _sessions[new_session_id] = agent
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

    agent = _sessions[req.session_id]
    agent.reset()
    logger.info("reset_session session_id=%s", req.session_id)
    return ChatResponse(
        session_id=req.session_id,
        response="已重置，可以重新开始推荐。",
        history=agent.get_chat_history(),
        is_ready=agent.is_ready,
    )


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, str]:
    """删除指定会话。"""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="session_id 不存在")

    _sessions.pop(session_id, None)
    logger.info("deleted_session session_id=%s", session_id)
    return {"status": "deleted", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
