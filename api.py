"""FastAPI 标准接口 - 提供可被前端或第三方系统调用的 Agent API"""

from typing import Dict
import os
import time
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from agent.agent import MealRecommenderAgent
from agent.logging_config import get_logger
from agent.food_data_manager import get_food_manager
from agent.crawler import run_crawler


logger = get_logger(__name__)


def _sanitize_log_message(message: str, max_length: int = 100) -> str:
    """对日志消息进行脱敏处理，避免记录敏感信息。
    
    处理策略：
    1. 截断过长的消息
    2. 移除可能的邮箱地址
    3. 移除可能的手机号
    4. 对特殊字符进行掩码
    """
    if not message:
        return ""
    
    # 截断过长的消息
    if len(message) > max_length:
        message = message[:max_length] + "..."
    
    # 移除邮箱地址（简单模式）
    import re
    message = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', message)
    
    # 移除手机号（中国大陆手机号）
    message = re.sub(r'\b1[3-9]\d{9}\b', '[PHONE]', message)
    
    # 移除身份证号（简单模式）
    message = re.sub(r'\b\d{17}[\dXx]\b', '[ID_CARD]', message)
    
    return message
app = FastAPI(
    title="吃什么推荐 Agent API",
    description="面向中国大学生的餐饮推荐 Agent 标准 API。",
    version="1.2.0",
)

# CORS 配置（可通过环境变量控制）
# 生产环境应该限制来源，不要使用 "*"
_cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
_origins = [o.strip() for o in _cors_origins.split(",")] if _cors_origins else ["*"]

# 允许的方法（可通过环境变量控制）
_cors_methods = os.getenv("CORS_ALLOW_METHODS", "GET,POST,PUT,DELETE,OPTIONS")
_methods = [m.strip() for m in _cors_methods.split(",")] if _cors_methods else ["*"]

# 允许的头部（可通过环境变量控制）
_cors_headers = os.getenv("CORS_ALLOW_HEADERS", "Content-Type,Authorization")
_headers = [h.strip() for h in _cors_headers.split(",")] if _cors_headers else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=_methods,
    allow_headers=_headers,
)

# 创建定时任务调度器
scheduler = BackgroundScheduler()

def scheduled_crawler_job():
    """定时爬虫任务"""
    try:
        logger.info("定时任务触发：开始爬取食物数据...")
        # 爬取多个主要城市
        cities = ["北京", "上海", "广州", "深圳", "成都", "杭州"]
        total_added = 0
        total_updated = 0
        
        for city in cities:
            try:
                result = run_crawler(city=city)
                if result.get("success"):
                    stats = result.get("stats", {})
                    total_added += stats.get("added", 0)
                    total_updated += stats.get("updated", 0)
                    logger.info("城市 %s 爬取完成：新增 %d，更新 %d", 
                              city, stats.get("added", 0), stats.get("updated", 0))
                time.sleep(2)  # 避免请求过快
            except Exception as e:
                logger.error("爬取城市 %s 失败: %s", city, e)
        
        logger.info("定时爬取完成：总计新增 %d，更新 %d", total_added, total_updated)
        
    except Exception as e:
        logger.error("定时爬虫任务失败: %s", e)

# 启动时自动检查并更新数据库
@app.on_event("startup")
async def startup_event():
    """应用启动时自动检查数据库更新"""
    try:
        food_manager = get_food_manager()
        if food_manager.should_update():
            logger.info("数据库需要更新，自动运行爬虫...")
            # 在后台线程中运行爬虫，避免阻塞启动
            import threading
            def update_in_background():
                try:
                    result = run_crawler(city="北京")
                    logger.info("自动更新完成: %s", result.get("message", ""))
                except Exception as e:
                    logger.error("自动更新失败: %s", e)
            
            thread = threading.Thread(target=update_in_background, daemon=True)
            thread.start()
        else:
            logger.info("数据库已是最新状态，跳过自动更新")
        
        # 启动定时任务调度器
        # 每天凌晨2点运行爬虫任务
        scheduler.add_job(
            scheduled_crawler_job,
            CronTrigger(hour=2, minute=0),  # 每天2:00
            id="daily_crawler",
            name="每日食物数据爬取",
            replace_existing=True
        )
        
        # 每周一早上8点也运行一次（可选）
        scheduler.add_job(
            scheduled_crawler_job,
            CronTrigger(day_of_week="mon", hour=8, minute=0),
            id="weekly_crawler",
            name="每周食物数据爬取",
            replace_existing=True
        )
        
        scheduler.start()
        logger.info("定时任务调度器已启动，爬取任务已安排")
        
    except Exception as e:
        logger.error("启动时检查更新失败: %s", e)


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
    logger.info("chat_request session_id=%s message=%s", session_id, _sanitize_log_message(req.message))

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


# ============================================================
# 食物数据库相关 API
# ============================================================

class FoodRankingsResponse(BaseModel):
    """食物排行榜响应。"""
    
    success: bool
    count: int
    foods: list[dict]


@app.get("/food_rankings", response_model=FoodRankingsResponse)
def get_food_rankings(limit: int = 10) -> FoodRankingsResponse:
    """获取热门食物排行榜。"""
    try:
        food_manager = get_food_manager()
        trending = food_manager.get_trending_foods(limit=limit)
        
        foods = []
        for i, food in enumerate(trending):
            foods.append({
                "rank": i + 1,
                "name": food["name"],
                "category": food.get("category", ""),
                "price_range": food.get("price_range", ""),
                "popularity": food.get("popularity", 0),
                "tags": food.get("tags", [])
            })
        
        return FoodRankingsResponse(
            success=True,
            count=len(foods),
            foods=foods
        )
    except Exception as e:
        logger.exception("get_food_rankings_failed")
        raise HTTPException(status_code=500, detail=f"获取排行榜失败: {str(e)}")


class SearchFoodRequest(BaseModel):
    """搜索食物请求。"""
    
    taste: str = Field("", description="口味偏好")
    budget: str = Field("", description="预算范围")
    meal_time: str = Field("", description="用餐时间")
    category: str = Field("", description="食物类别")
    limit: int = Field(10, ge=1, le=50, description="返回数量")


class SearchFoodResponse(BaseModel):
    """搜索食物响应。"""
    
    success: bool
    count: int
    results: list[dict]


@app.post("/search_food", response_model=SearchFoodResponse)
def search_food(req: SearchFoodRequest) -> SearchFoodResponse:
    """搜索食物数据库。"""
    try:
        food_manager = get_food_manager()
        results = food_manager.search_foods(
            taste=req.taste,
            budget=req.budget,
            meal_time=req.meal_time,
            category=req.category,
            limit=req.limit
        )
        
        formatted_results = []
        for food in results:
            formatted_results.append({
                "name": food["name"],
                "category": food.get("category", ""),
                "price_range": food.get("price_range", ""),
                "description": food.get("description", ""),
                "popularity": food.get("popularity", 0),
                "tags": food.get("tags", [])
            })
        
        return SearchFoodResponse(
            success=True,
            count=len(formatted_results),
            results=formatted_results
        )
    except Exception as e:
        logger.exception("search_food_failed")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


class UpdateDataRequest(BaseModel):
    """更新数据请求。"""
    
    city: str = Field("北京", description="城市名称")
    force: bool = Field(False, description="是否强制更新")


class UpdateDataResponse(BaseModel):
    """更新数据响应。"""
    
    success: bool
    message: str
    stats: dict


@app.post("/update_data", response_model=UpdateDataResponse)
def update_data(req: UpdateDataRequest) -> UpdateDataResponse:
    """更新食物数据库（触发爬虫）。"""
    try:
        result = run_crawler(city=req.city)
        return UpdateDataResponse(
            success=result["success"],
            message=result["message"],
            stats=result.get("stats", {})
        )
    except Exception as e:
        logger.exception("update_data_failed")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")

@app.post("/trigger_crawler")
def trigger_crawler():
    """手动触发爬虫任务（测试用）"""
    try:
        # 在后台线程中运行爬虫
        import threading
        def run_in_background():
            scheduled_crawler_job()
        
        thread = threading.Thread(target=run_in_background, daemon=True)
        thread.start()
        
        return {
            "success": True,
            "message": "爬虫任务已触发，正在后台运行",
            "note": "任务将在后台执行，可通过日志查看进度"
        }
    except Exception as e:
        logger.exception("trigger_crawler_failed")
        raise HTTPException(status_code=500, detail=f"触发失败: {str(e)}")

@app.get("/crawler_status")
def get_crawler_status():
    """获取爬虫任务状态"""
    try:
        food_manager = get_food_manager()
        last_update = food_manager._last_update
        food_count = len(food_manager.load_database())
        
        return {
            "success": True,
            "last_update": last_update.isoformat() if last_update else None,
            "food_count": food_count,
            "needs_update": food_manager.should_update(),
            "scheduler_jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in scheduler.get_jobs()
            ]
        }
    except Exception as e:
        logger.exception("get_crawler_status_failed")
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@app.get("/food_stats")
def get_food_stats() -> dict:
    """获取食物数据库统计信息。"""
    try:
        food_manager = get_food_manager()
        foods = food_manager.load_database()
        
        # 统计各类别数量
        categories = {}
        for food in foods:
            cat = food.get("category", "未分类")
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total_foods": len(foods),
            "categories": categories,
            "last_update": food_manager._last_update.isoformat() if food_manager._last_update else None,
            "should_update": food_manager.should_update()
        }
    except Exception as e:
        logger.exception("get_food_stats_failed")
        raise HTTPException(status_code=500, detail=f"获取统计失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
