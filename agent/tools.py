"""Tools for the meal recommender agent - 使用 per-agent 隔离状态"""

import json
from typing import Dict
from datetime import datetime
from contextvars import ContextVar
import uuid
import threading
from langchain_core.tools import tool

from .logging_config import get_logger
from .food_data_manager import get_food_manager


logger = get_logger(__name__)


# 当前活动的 agent ID（通过 contextvars 实现协程/线程安全隔离）
_current_agent_id: ContextVar[str | None] = ContextVar("agent_id", default=None)


# 全局状态存储 + 线程锁
# 注意：_agent_states 是进程内全局字典，uvicorn 多 worker 模式下无法共享
# 当前设计适用于单 worker 模式，如需多 worker 需使用 Redis 等外部存储
_agent_states: Dict[str, Dict] = {}
_state_lock = threading.Lock()


def _make_fresh_state() -> Dict:
    """创建全新的会话状态"""
    return {
        "taste": "",
        "budget": "",
        "meal_time": "",
        "weather": "",
        "health": "",
        "social": "",
        "mood": "",
        "city": "",
        "school": "",
        "count": 1,
        "has_recommendation": False,
    }


def _get_state() -> Dict:
    """获取当前 agent 状态（无锁，内部调用）"""
    agent_id = _current_agent_id.get()
    if not agent_id:
        return {}
    return _agent_states.get(agent_id, {})


def _save_internal_state(agent_id: str, state: Dict):
    """更新 agent 状态"""
    with _state_lock:
        _agent_states[agent_id] = state


# ============================================================
# 原始函数（供 Agent tool 调用和单元测试使用）
# ============================================================

def _save_preference(key: str, value: str) -> str:
    """保存偏好"""
    agent_id = _current_agent_id.get()
    if not agent_id:
        return "警告：未关联 agent"
    
    state = _get_state()
    state[key] = value
    _save_internal_state(agent_id, state)
    logger.info("tool_save_preference agent_id=%s key=%s value=%s", agent_id, key, value)
    
    return f"已记录：{key} = {value}"


def _get_preferences() -> str:
    """获取已收集的所有偏好"""
    state = _get_state()
    
    parts = []
    if state.get("city"):
        parts.append(f"城市：{state['city']}")
    if state.get("school"):
        parts.append(f"学校：{state['school']}")
    if state.get("taste"):
        parts.append(f"口味：{state['taste']}")
    if state.get("budget"):
        parts.append(f"预算：{state['budget']}")
    if state.get("meal_time"):
        parts.append(f"时间：{state['meal_time']}")
    if state.get("weather"):
        parts.append(f"天气：{state['weather']}")
    if state.get("health"):
        parts.append(f"健康：{state['health']}")
    if state.get("social"):
        parts.append(f"场景：{state['social']}")
    if state.get("mood"):
        parts.append(f"心情：{state['mood']}")
    
    return " | ".join(parts) if parts else "还没有收集到任何偏好信息"


def _get_context_info() -> str:
    """获取当前时间和天气"""
    now = datetime.now()
    hour = now.hour
    
    if 5 <= hour < 10:
        meal_time = "早餐"
    elif 10 <= hour < 14:
        meal_time = "午餐"
    elif 14 <= hour < 20:
        meal_time = "晚餐"
    else:
        meal_time = "夜宵"
    
    # 获取城市信息
    agent_id = _current_agent_id.get()
    city = ""
    if agent_id:
        state = _get_state()
        city = state.get("city", "")
    
    # 根据城市获取天气（简化版，实际可对接天气API）
    if city:
        # 简单的城市天气映射（实际应该调用天气API）
        city_weather = {
            "北京": "晴天",
            "上海": "多云",
            "广州": "阵雨",
            "深圳": "晴天",
            "成都": "阴天",
            "杭州": "小雨",
            "武汉": "多云",
            "南京": "晴天",
            "重庆": "阴天",
            "西安": "晴天",
        }
        weather = city_weather.get(city, "晴天")
    else:
        weather = "晴天"
    
    if agent_id:
        state["meal_time"] = meal_time
        state["weather"] = weather
        _save_internal_state(agent_id, state)
    
    weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    return "当前时间：%s %s %s；当前餐段：%s；天气：%s" % (
        now.strftime('%Y年%m月%d日'),
        weekdays[now.weekday()],
        now.strftime('%H:%M'),
        meal_time,
        weather,
    )


def _reset_preferences() -> str:
    """重置所有偏好"""
    agent_id = _current_agent_id.get()
    if agent_id:
        _save_internal_state(agent_id, _make_fresh_state())
    return "已重置所有偏好，可以重新开始对话。"


def _generate_recommendation(force_recommendation: str = "") -> str:
    """根据已收集的偏好生成餐饮推荐
    
    注意：此函数现在调用新的食物数据库系统，而不是使用硬编码的推荐数据。
    为了保持向后兼容性，保留了此函数，但内部实现已改为调用 get_food_recommendations。
    """
    agent_id = _current_agent_id.get()
    state = _get_state()
    
    taste = state.get("taste", "随意")
    budget = state.get("budget", "10-30 元")
    meal_time = state.get("meal_time", "午餐")
    weather = state.get("weather", "晴天")
    
    if force_recommendation:
        if agent_id:
            state["has_recommendation"] = True
            _save_internal_state(agent_id, state)
        return force_recommendation
    
    # 调用新的食物数据库系统
    try:
        food_manager = get_food_manager()
        
        # 搜索候选食物
        candidates = food_manager.search_foods(
            taste=taste if taste != "随意" else "",
            budget=budget,
            meal_time=meal_time,
            limit=5
        )
        
        if not candidates:
            # 如果没有找到，返回默认推荐
            return (
                "抱歉，暂时没有找到完全符合你偏好的食物。\n\n"
                "你可以试试：\n"
                "1. 麻辣烫 - 不知道吃啥就吃麻辣烫，通吃\n"
                "2. 炒饭/炒面 - 快速解决，便宜管饱\n"
                "3. 饺子/馄饨 - 简单又管饱，不踩雷\n\n"
                "不满意可以告诉我，我帮你想想别的～"
            )
        
        # 按热度排序
        candidates.sort(key=lambda x: x.get("popularity", 0), reverse=True)
        
        # 取第一个作为主推荐
        main_food = candidates[0]
        alternatives = candidates[1:3] if len(candidates) > 1 else []
        
        lines = []
        lines.append("好的，帮你想好了！")
        lines.append("")
        lines.append(f"**推荐：{main_food['name']}**")
        lines.append(f"**理由**：符合你的口味偏好，热度高")
        lines.append(f"**价格**：{main_food.get('price_range', '未知')}")
        if main_food.get('description'):
            lines.append(f"**详情**：{main_food['description']}")
        lines.append("")
        
        if alternatives:
            lines.append("备选方案：")
            for i, alt in enumerate(alternatives, 1):
                lines.append(f"  {i}. **{alt['name']}** - {alt.get('description', '美味推荐')}")
        
        lines.append("")
        lines.append("不满意可以告诉我，我帮你想想别的～")
        
        if agent_id:
            state["has_recommendation"] = True
            _save_internal_state(agent_id, state)
            logger.info("tool_generate_recommendation agent_id=%s taste=%s budget=%s", agent_id, taste, budget)
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error("generate_recommendation_failed error=%s", e)
        # 降级到默认推荐
        return (
            "抱歉，推荐系统暂时出现问题。\n\n"
            "你可以试试：\n"
            "1. 麻辣烫 - 不知道吃啥就吃麻辣烫，通吃\n"
            "2. 炒饭/炒面 - 快速解决，便宜管饱\n"
            "3. 饺子/馄饨 - 简单又管饱，不踩雷\n\n"
            "不满意可以告诉我，我帮你想想别的～"
        )


# ============================================================
# Agent 状态管理器（由 MealRecommenderAgent 使用）
# ============================================================

class SessionStateManager:
    """管理每个 agent 的独立 session state"""
    
    def __init__(self):
        self.agent_id = str(uuid.uuid4())
        with _state_lock:
            _agent_states[self.agent_id] = _make_fresh_state()
    
    def get_state(self) -> Dict:
        """获取当前 agent 的状态（按 agent_id 读取，不依赖 context）"""
        with _state_lock:
            return dict(_agent_states.get(self.agent_id, {}))
    
    def reset(self):
        """重置当前 agent 状态"""
        with _state_lock:
            _agent_states[self.agent_id] = _make_fresh_state()
    
    def cleanup(self):
        """清理当前 agent 状态"""
        with _state_lock:
            _agent_states.pop(self.agent_id, None)
    
    def activate(self):
        """设置为当前活动的 agent（工具调用前必须调用）"""
        _current_agent_id.set(self.agent_id)


# ============================================================
# LangChain Tool 包装
# ============================================================

@tool("save_location")
def save_location(city: str, school: str) -> str:
    """保存用户的位置信息（城市和学校/校区）。这是推荐的前提条件，必须在推荐前获取。
    
    Args:
        city: 城市名称（如"北京"、"上海"）
        school: 学校名称和校区（如"清华大学"、"北京大学东门校区"）
    
    Returns:
        确认信息
    """
    agent_id = _current_agent_id.get()
    if not agent_id:
        return "警告：未关联 agent"
    
    state = _get_state()
    state["city"] = city
    state["school"] = school
    _save_internal_state(agent_id, state)
    logger.info("tool_save_location agent_id=%s city=%s school=%s", agent_id, city, school)
    
    return f"已记录位置信息：{city}，{school}"


@tool("save_preference")
def save_preference(key: str, value: str) -> str:
    """保存用户的偏好信息。当你从用户那里收集到某个偏好时调用。"""
    return _save_preference(key, value)


@tool("get_preferences")
def get_preferences() -> str:
    """获取已收集的所有偏好。推荐前调用，检查信息是否足够。"""
    return _get_preferences()


@tool("get_context_info")
def get_context_info() -> str:
    """获取当前时间和天气。对话开始时调用。"""
    return _get_context_info()


@tool("reset_preferences")
def reset_preferences() -> str:
    """重置所有偏好。用户要求重新开始时调用。"""
    return _reset_preferences()


@tool("generate_recommendation")
def generate_recommendation(force_recommendation: str = "") -> str:
    """根据已收集的偏好生成推荐。确认信息足够后调用。"""
    return _generate_recommendation(force_recommendation)


# ============================================================
# 食物数据库相关工具
# ============================================================

@tool("search_food_database")
def search_food_database(
    taste: str = "",
    budget: str = "",
    meal_time: str = "",
    category: str = "",
    limit: int = 10
) -> str:
    """搜索本地食物数据库，根据口味、预算、用餐时间等条件筛选食物选项。
    
    Args:
        taste: 口味偏好（辣/清淡/重口/不辣等）
        budget: 预算范围（如 "10-30元"）
        meal_time: 用餐时间（早餐/午餐/晚餐/夜宵）
        category: 食物类别（快餐/小吃/正餐等）
        limit: 返回结果数量，默认10个
    
    Returns:
        JSON 格式的食物列表，包含名称、价格、推荐理由等信息
    """
    try:
        food_manager = get_food_manager()
        results = food_manager.search_foods(
            taste=taste,
            budget=budget,
            meal_time=meal_time,
            category=category,
            limit=limit
        )
        
        if not results:
            return json.dumps({
                "success": False,
                "message": "没有找到符合条件的食物",
                "results": []
            }, ensure_ascii=False)
        
        # 格式化结果
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
        
        return json.dumps({
            "success": True,
            "count": len(formatted_results),
            "results": formatted_results
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error("search_food_database_failed error=%s", e)
        return json.dumps({
            "success": False,
            "message": f"搜索失败: {str(e)}",
            "results": []
        }, ensure_ascii=False)


@tool("get_food_recommendations")
def get_food_recommendations(
    preferences: str,
    count: int = 3
) -> str:
    """基于用户偏好生成个性化食物推荐。结合数据库搜索和算法排序。
    
    Args:
        preferences: 用户偏好摘要（如 "口味：辣，预算：20-30元，时间：午餐"）
        count: 推荐数量，默认3个
    
    Returns:
        结构化的推荐结果，包含主要推荐和备选方案
    """
    try:
        food_manager = get_food_manager()
        
        # 解析用户偏好
        taste = ""
        budget = ""
        meal_time = ""
        
        if "口味" in preferences:
            parts = preferences.split("口味")
            if len(parts) > 1:
                taste_part = parts[1].split("，")[0].split("。")[0]
                taste = taste_part.strip().replace("：", "").replace(":", "")
        
        if "预算" in preferences:
            parts = preferences.split("预算")
            if len(parts) > 1:
                budget_part = parts[1].split("，")[0].split("。")[0]
                budget = budget_part.strip().replace("：", "").replace(":", "")
        
        if "时间" in preferences or "餐" in preferences:
            for keyword in ["时间", "餐"]:
                if keyword in preferences:
                    parts = preferences.split(keyword)
                    if len(parts) > 1:
                        meal_part = parts[1].split("，")[0].split("。")[0]
                        meal_time = meal_part.strip().replace("：", "").replace(":", "")
                        break
        
        # 搜索候选食物
        candidates = food_manager.search_foods(
            taste=taste,
            budget=budget,
            meal_time=meal_time,
            limit=count * 2
        )
        
        if not candidates:
            return json.dumps({
                "success": False,
                "message": "没有找到合适的食物推荐",
                "recommendations": []
            }, ensure_ascii=False)
        
        # 按热度排序
        candidates.sort(key=lambda x: x.get("popularity", 0), reverse=True)
        
        # 取前 N 个
        top_foods = candidates[:count]
        
        # 格式化推荐结果
        recommendations = []
        for i, food in enumerate(top_foods):
            recommendations.append({
                "rank": i + 1,
                "name": food["name"],
                "reason": f"符合你的口味偏好，热度高",
                "price_range": food.get("price_range", ""),
                "description": food.get("description", ""),
                "confidence": min(95, 70 + food.get("popularity", 0) // 10)
            })
        
        return json.dumps({
            "success": True,
            "count": len(recommendations),
            "recommendations": recommendations,
            "summary": f"根据你的偏好，推荐了 {len(recommendations)} 个选择"
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error("get_food_recommendations_failed error=%s", e)
        return json.dumps({
            "success": False,
            "message": f"推荐失败: {str(e)}",
            "recommendations": []
        }, ensure_ascii=False)


@tool("update_food_database")
def update_food_database(
    force_update: bool = False
) -> str:
    """更新食物数据库。检查是否有新数据可用并更新本地缓存。
    
    Args:
        force_update: 是否强制更新（忽略时间检查）
    
    Returns:
        更新状态信息，包括更新时间和数据量
    """
    try:
        food_manager = get_food_manager()
        
        # 检查是否需要更新
        if not force_update and not food_manager.should_update():
            return json.dumps({
                "success": True,
                "message": "数据库已是最新状态",
                "last_update": food_manager._last_update.isoformat() if food_manager._last_update else None,
                "food_count": len(food_manager.load_database())
            }, ensure_ascii=False)
        
        # 保存数据库（触发更新）
        food_manager.save_database()
        
        return json.dumps({
            "success": True,
            "message": "数据库更新完成",
            "last_update": datetime.now().isoformat(),
            "food_count": len(food_manager.load_database())
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error("update_food_database_failed error=%s", e)
        return json.dumps({
            "success": False,
            "message": f"更新失败: {str(e)}",
            "last_update": None,
            "food_count": 0
        }, ensure_ascii=False)


@tool("get_trending_foods")
def get_trending_foods(limit: int = 10) -> str:
    """获取当前热门食物排行榜。
    
    Args:
        limit: 返回数量，默认10个
    
    Returns:
        按热度排序的食物列表
    """
    try:
        food_manager = get_food_manager()
        trending = food_manager.get_trending_foods(limit=limit)
        
        if not trending:
            return json.dumps({
                "success": False,
                "message": "暂无热门食物数据",
                "foods": []
            }, ensure_ascii=False)
        
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
        
        return json.dumps({
            "success": True,
            "count": len(foods),
            "foods": foods
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error("get_trending_foods_failed error=%s", e)
        return json.dumps({
            "success": False,
            "message": f"获取热门食物失败: {str(e)}",
            "foods": []
        }, ensure_ascii=False)


@tool("web_search_restaurant")
def web_search_restaurant(
    query: str,
    location: str = "",
    max_results: int = 5
) -> str:
    """使用搜狗搜索餐厅推荐和美食信息。
    
    Args:
        query: 搜索关键词（如 "麻辣烫"、"火锅"、"学校附近快餐"）
        location: 位置信息（如 "北京"、"五道口"），可选
        max_results: 返回结果数量，默认5个
    
    Returns:
        搜索结果列表，包含标题、链接、摘要
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # 构建搜索查询
        search_query = query
        if location:
            search_query = f"{location} {query} 推荐"
        else:
            search_query = f"{query} 推荐 好吃"
        
        logger.info("web_search_restaurant query=%s location=%s", query, location)
        
        # 使用搜狗搜索
        url = "https://www.sogou.com/web"
        params = {"query": search_query}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 解析搜索结果
        results = soup.find_all("div", class_="vrwrap") or soup.find_all("div", class_="rb")
        
        if not results:
            # 尝试提取 h3 标签
            h3_tags = soup.find_all("h3")
            if h3_tags:
                formatted_results = []
                for i, h3 in enumerate(h3_tags[:max_results]):
                    title = h3.get_text().strip()
                    link = ""
                    parent = h3.find_parent("a")
                    if parent:
                        link = parent.get("href", "")
                    formatted_results.append({
                        "rank": i + 1,
                        "title": title,
                        "link": link,
                        "snippet": ""
                    })
                
                if formatted_results:
                    return json.dumps({
                        "success": True,
                        "query": search_query,
                        "count": len(formatted_results),
                        "results": formatted_results
                    }, ensure_ascii=False)
            
            return json.dumps({
                "success": False,
                "message": "未找到相关搜索结果",
                "results": []
            }, ensure_ascii=False)
        
        # 格式化结果
        formatted_results = []
        for i, result in enumerate(results[:max_results]):
            title_elem = result.find("h3")
            title = title_elem.get_text().strip() if title_elem else ""
            
            link = ""
            if title_elem:
                parent = title_elem.find_parent("a")
                if parent:
                    link = parent.get("href", "")
            
            snippet = ""
            snippet_elem = result.find("p", class_="str_info") or result.find("div", class_="space-txt")
            if snippet_elem:
                snippet = snippet_elem.get_text().strip()[:200]
            
            formatted_results.append({
                "rank": i + 1,
                "title": title,
                "link": link,
                "snippet": snippet
            })
        
        return json.dumps({
            "success": True,
            "query": search_query,
            "count": len(formatted_results),
            "results": formatted_results
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error("web_search_restaurant_failed error=%s", e)
        return json.dumps({
            "success": False,
            "message": f"搜索失败: {str(e)}",
            "results": []
        }, ensure_ascii=False)


@tool("search_food_review")
def search_food_review(
    food_name: str,
    restaurant: str = "",
    max_results: int = 3
) -> str:
    """搜索特定食物或餐厅的评价和推荐。
    
    Args:
        food_name: 食物名称（如 "麻辣烫"、"珍珠奶茶"）
        restaurant: 餐厅名称，可选
        max_results: 返回结果数量，默认3个
    
    Returns:
        评价和推荐列表
    """
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # 构建搜索查询
        search_query = food_name
        if restaurant:
            search_query = f"{restaurant} {food_name}"
        search_query += " 推荐 评价 好吃 怎么样"
        
        logger.info("search_food_review food=%s restaurant=%s", food_name, restaurant)
        
        # 使用搜狗搜索
        url = "https://www.sogou.com/web"
        params = {"query": search_query}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 解析搜索结果
        results = soup.find_all("div", class_="vrwrap") or soup.find_all("div", class_="rb")
        
        if not results:
            # 尝试提取 h3 标签
            h3_tags = soup.find_all("h3")
            if h3_tags:
                formatted_results = []
                for i, h3 in enumerate(h3_tags[:max_results]):
                    title = h3.get_text().strip()
                    link = ""
                    parent = h3.find_parent("a")
                    if parent:
                        link = parent.get("href", "")
                    formatted_results.append({
                        "rank": i + 1,
                        "title": title,
                        "link": link,
                        "snippet": ""
                    })
                
                if formatted_results:
                    return json.dumps({
                        "success": True,
                        "food": food_name,
                        "count": len(formatted_results),
                        "results": formatted_results
                    }, ensure_ascii=False)
            
            return json.dumps({
                "success": False,
                "message": "未找到相关评价",
                "results": []
            }, ensure_ascii=False)
        
        # 格式化结果
        formatted_results = []
        for i, result in enumerate(results[:max_results]):
            title_elem = result.find("h3")
            title = title_elem.get_text().strip() if title_elem else ""
            
            link = ""
            if title_elem:
                parent = title_elem.find_parent("a")
                if parent:
                    link = parent.get("href", "")
            
            snippet = ""
            snippet_elem = result.find("p", class_="str_info") or result.find("div", class_="space-txt")
            if snippet_elem:
                snippet = snippet_elem.get_text().strip()[:200]
            
            formatted_results.append({
                "rank": i + 1,
                "title": title,
                "link": link,
                "snippet": snippet
            })
        
        return json.dumps({
            "success": True,
            "food": food_name,
            "count": len(formatted_results),
            "results": formatted_results
        }, ensure_ascii=False)
        
    except Exception as e:
        logger.error("search_food_review_failed error=%s", e)
        return json.dumps({
            "success": False,
            "message": f"搜索失败: {str(e)}",
            "results": []
        }, ensure_ascii=False)


def get_all_tools():
    """获取所有工具列表"""
    return [
        save_location,
        save_preference,
        get_preferences,
        get_context_info,
        reset_preferences,
        generate_recommendation,
        # 食物数据库相关工具
        search_food_database,
        get_food_recommendations,
        update_food_database,
        get_trending_foods,
        # 网络搜索工具
        web_search_restaurant,
        search_food_review,
    ]
