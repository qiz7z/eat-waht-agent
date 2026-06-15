"""Tools for the meal recommender agent - 使用 per-agent 隔离状态"""

from typing import Dict
from datetime import datetime
from contextvars import ContextVar
import uuid
import threading
from langchain_core.tools import tool

from .logging_config import get_logger


logger = get_logger(__name__)


# 当前活动的 agent ID（通过 contextvars 实现协程/线程安全隔离）
_current_agent_id: ContextVar[str | None] = ContextVar("agent_id", default=None)


# 全局状态存储 + 线程锁
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
    
    weather = "晴天"
    
    agent_id = _current_agent_id.get()
    if agent_id:
        state = _get_state()
        state["meal_time"] = meal_time
        state["weather"] = weather
        _save_internal_state(agent_id, state)
    
    return f"当前是{meal_time}时间，天气{weather}，实际时间 {now.strftime('%H:%M')}"


def _reset_preferences() -> str:
    """重置所有偏好"""
    agent_id = _current_agent_id.get()
    if agent_id:
        _save_internal_state(agent_id, _make_fresh_state())
    return "已重置所有偏好，可以重新开始对话。"


def _generate_recommendation(force_recommendation: str = "") -> str:
    """根据已收集的偏好生成餐饮推荐"""
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
    
    rec_db = {
        "清淡": {
            "name": "清汤面+荷包蛋",
            "reason": f"清淡口味适合{meal_time}，养胃又舒服",
            "details": "学校食堂的清汤面配一个荷包蛋，加点青菜，暖胃又顶饱。",
            "price": "10-15 元",
            "alternatives": [
                {"name": "三明治+酸奶", "reason": "轻食搭配，清爽不腻"},
                {"name": "鸡胸肉沙拉", "reason": "健康低卡，减脂首选"},
            ],
        },
        "重口": {
            "name": "麻辣烫/冒菜",
            "reason": f"重口味首选，{meal_time}来一碗超满足",
            "details": "自选菜品的麻辣烫，多放麻酱和辣椒，配米饭刚好。",
            "price": "15-25 元",
            "alternatives": [
                {"name": "烤肉拌饭", "reason": "味道浓郁，分量足"},
                {"name": "重庆小面", "reason": "麻辣过瘾，便宜管饱"},
            ],
        },
        "辣": {
            "name": "麻辣烫/串串香",
            "reason": f"无辣不欢，{meal_time}安排上",
            "details": "自选麻辣锅，配各种丸子和蔬菜。配冰可乐更爽。",
            "price": "20-35 元",
            "alternatives": [
                {"name": "麻辣香锅", "reason": "下饭神器，口味丰富"},
                {"name": "酸菜鱼", "reason": "酸辣开胃，鱼嫩汤鲜"},
            ],
        },
        "不辣": {
            "name": "黄焖鸡米饭",
            "reason": f"不辣的好选择，{meal_time}吃刚刚好",
            "details": "鸡肉嫩滑，土豆和香菇入味，汤汁拌饭绝了。",
            "price": "15-20 元",
            "alternatives": [
                {"name": "番茄鸡蛋面", "reason": "酸甜可口，暖胃养胃"},
                {"name": "盖浇饭", "reason": "选择多，性价比高"},
            ],
        },
        "随意": {
            "name": "麻辣烫",
            "reason": f"不知道吃啥就吃麻辣烫，{meal_time}通吃",
            "details": "自选配菜，想吃什么拿什么，口味可清淡可重口。",
            "price": "15-25 元",
            "alternatives": [
                {"name": "炒饭/炒面", "reason": "快速解决，便宜管饱"},
                {"name": "饺子/馄饨", "reason": "简单又管饱，不踩雷"},
            ],
        },
    }
    
    rec = rec_db.get(taste, rec_db["随意"])
    
    lines = []
    lines.append("好的，帮你想好了！")
    lines.append("")
    lines.append(f"**推荐：{rec['name']}**")
    lines.append(f"**理由**：{rec['reason']}")
    lines.append(f"**详情**：{rec['details']}")
    lines.append(f"**价格**：{rec['price']}")
    lines.append("")
    lines.append("备选方案：")
    for i, alt in enumerate(rec["alternatives"], 1):
        lines.append(f"  {i}. **{alt['name']}** - {alt['reason']}")
    lines.append("")
    lines.append("不满意可以告诉我，我帮你想想别的～")
    
    if agent_id:
        state["has_recommendation"] = True
        _save_internal_state(agent_id, state)
        logger.info("tool_generate_recommendation agent_id=%s taste=%s budget=%s", agent_id, taste, budget)
    
    return "\n".join(lines)


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


def get_all_tools():
    """获取所有工具列表"""
    return [
        save_preference,
        get_preferences,
        get_context_info,
        reset_preferences,
        generate_recommendation,
    ]
