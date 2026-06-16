"""Agent 定义 - 基于 LangChain Tool Calling Agent"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

from .config import build_chat_openai_kwargs, get_llm_config
from .logging_config import get_logger
from .tools import get_all_tools, SessionStateManager


logger = get_logger(__name__)


SYSTEM_PROMPT = """你是一个专门为中国大学生推荐餐饮的 AI 助手。

## 你的角色
学生不知道吃什么的时候，你来帮忙推荐。你要像朋友一样跟 ta 聊天，不要像在做问卷调查。

## 你的核心能力
你有一个**本地食物数据库**，包含 75+ 种常见中式食物。

## 重要工具
- `search_food_database`：搜索食物数据库获取推荐
- `get_food_recommendations`：生成个性化推荐
- `get_trending_foods`：获取热门排行榜
- `save_preference`：保存用户偏好
- `get_preferences`：查看用户偏好
- `reset_preferences`：重置偏好

## 位置信息收集
**必须主动询问用户所在城市和学校（具体校区）**。这是推荐的前提条件，因为：
1. 不同城市的美食差异很大
2. 不同学校/校区的周边餐饮环境不同
3. 没有位置信息，推荐会不准确

在对话开始时，你应该主动询问：“你在哪里呀？在哪个城市，哪个学校（校区）？” 
如果用户没有提供位置信息，不要进行推荐，而是先询问位置。

## 时间日期回答
系统会在每次对话时提供当前时间上下文。用户问日期、星期、现在几点时，直接自然回答即可，例如“今天是 6 月 16 日，星期二”。不要说“我已收到系统提示”或暴露内部上下文。
"""

# 对话历史最大长度（防止内存无限增长）
MAX_CHAT_HISTORY = 50


class MealRecommenderAgent:
    """基于 LangChain Tool Calling 的餐饮推荐 Agent"""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self._llm_config = get_llm_config(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
        )
        
        self._graph = None
        self._chat_history: List[Any] = []
        self._is_ready = False
        self._session = None
        
        self._initialize()
    
    def _get_current_time_context(self) -> str:
        """生成当前时间上下文，供模型回答日期时间问题。"""
        now = datetime.now()
        weekdays = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
        return "当前时间：%s年%s月%s日 %s %s:%s" % (
            now.year,
            str(now.month).zfill(2),
            str(now.day).zfill(2),
            weekdays[now.weekday()],
            str(now.hour).zfill(2),
            str(now.minute).zfill(2),
        )
    
    def _initialize(self):
        """初始化 Agent"""
        if not self._llm_config.is_configured:
            self._is_ready = False
            logger.warning("agent_not_ready reason=missing_api_key model=%s", self._llm_config.model)
            return
        
        # 为每个 agent 创建独立的 session state
        self._session = SessionStateManager()
        
        logger.info(
            "initializing_agent model=%s base_url=%s provider=%s",
            self._llm_config.model,
            self._llm_config.base_url or "default",
            self._llm_config.provider,
        )
        llm = ChatOpenAI(**build_chat_openai_kwargs(self._llm_config))
        
        tools = get_all_tools()
        
        self._graph = create_agent(
            model=llm,
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
        )
        
        self._is_ready = True
    
    @property
    def is_ready(self) -> bool:
        """Agent 是否已就绪"""
        return self._is_ready
    
    def invoke(self, user_message: str) -> str:
        """调用 Agent 处理用户消息"""
        logger.info("agent_invoke ready=%s message=%s", self._is_ready, user_message)
        if not self._is_ready:
            return self._get_fallback_response(user_message)
        
        # 激活当前 agent 的 session state（使 tool 能正确读写）
        if self._session:
            self._session.activate()
        
        try:
            # create_agent (langchain >=1.3) 要求 messages 为字典格式: {"role": "...", "content": "..."}
            input_messages = [
                {
                    "role": "system",
                    "content": "%s。用户问日期、星期或时间时，请基于这个上下文自然回答，不要提到系统提示。" % self._get_current_time_context(),
                }
            ]
            for msg in self._chat_history:
                if msg.type == "human":
                    input_messages.append({"role": "user", "content": msg.content})
                elif msg.type == "ai":
                    input_messages.append({"role": "assistant", "content": msg.content})
            input_messages.append({"role": "user", "content": user_message})

            result = self._graph.invoke({
                "messages": input_messages,
            })
            
            messages = result.get("messages", [])
            response = ""
            for msg in reversed(messages):
                if isinstance(msg, dict):
                    is_ai = msg.get("role") == "assistant" or msg.get("type") == "ai"
                    content = msg.get("content", "")
                else:
                    is_ai = getattr(msg, "type", "") == "ai"
                    content = getattr(msg, "content", "")
                if is_ai and content:
                    response = content
                    break
            
            if not response:
                response = "抱歉，我暂时无法回复。"

            # 更新对话历史（追加前检查容量，保持 human/ai 对匹配）
            if len(self._chat_history) >= MAX_CHAT_HISTORY:
                self._chat_history = self._chat_history[-(MAX_CHAT_HISTORY - 2):]
            self._chat_history.append(HumanMessage(content=user_message))
            self._chat_history.append(AIMessage(content=response))
            logger.info("agent_response response_len=%s history_len=%s", len(response), len(self._chat_history))
            
            return response
            
        except Exception:
            logger.exception("agent_invoke_failed")
            return self._get_fallback_response(user_message)
    
    def reset(self):
        """重置 Agent 状态"""
        self._chat_history = []
        if self._session:
            self._session.activate()
            self._session.reset()
    
    def get_chat_history(self) -> List[Dict[str, str]]:
        """获取聊天历史"""
        messages = []
        for msg in self._chat_history:
            if msg.type == "human":
                messages.append({"role": "user", "content": msg.content})
            elif msg.type == "ai":
                messages.append({"role": "assistant", "content": msg.content})
        return messages
    
    def __del__(self):
        """清理 session state
        
        注意：Python 的 __del__ 方法不保证被调用，且调用顺序不可控。
        对于当前项目（单 worker 模式），这不是大问题。
        生产环境建议使用上下文管理器（with 语句）确保资源释放。
        """
        if self._session:
            self._session.cleanup()
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口，确保资源释放"""
        if self._session:
            self._session.cleanup()
        return False  # 不抑制异常
    
    def _get_fallback_response(self, user_message: str) -> str:
        """无 API 时的回退响应"""
        return (
            '收到你说"' + user_message + '"。\n\n'
            "不过我还没有连接到 AI 大脑，需要你配置一下 API Key 才能开始聊天。\n"
            "在 .env 文件中设置 OPENAI_API_KEY 或 DASHSCOPE_API_KEY 即可。\n\n"
            "如果你只是想测试，我可以给你一个简单的推荐：\n"
            "不知道吃什么的话，来碗麻辣烫总没错！"
        )
