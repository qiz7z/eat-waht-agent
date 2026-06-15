"""Agent 定义 - 基于 LangChain Tool Calling Agent"""

from typing import Dict, List, Optional, Any

from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

from .config import build_chat_openai_kwargs, get_llm_config
from .tools import get_all_tools, SessionStateManager, _current_agent_id


SYSTEM_PROMPT = """你是一个专门为中国大学生推荐餐饮的 AI 助手。

## 你的角色
学生不知道吃什么的时候，你来帮忙推荐。你要像朋友一样跟 ta 聊天，不要像在做问卷调查。

## 你的工作流程
1. 先了解用户的口味、预算、时间等基本需求
2. 根据这些信息给出推荐（1 个主推荐 + 2 个备选）
3. 推荐后继续互动，看用户是否满意

## 规则
- 每次只问一个问题，不要太啰嗦
- 用户如果说了推荐需要的全部信息（口味 + 预算），就可以推荐
- 如果用户已经拿到推荐结果，但说想换一个或再看看，可以展示备选方案或重新推荐
- 语气轻松友好，像朋友聊天一样
- 用户说"重新开始"时，先调用 reset_preferences 工具再重新走流程
- 对话开始时先调用 get_context_info 了解当前时间段和天气"""

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
    
    def _initialize(self):
        """初始化 Agent"""
        if not self._llm_config.is_configured:
            self._is_ready = False
            return
        
        # 为每个 agent 创建独立的 session state
        self._session = SessionStateManager()
        
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
        if not self._is_ready:
            return self._get_fallback_response(user_message)
        
        # 激活当前 agent 的 session state（使 tool 能正确读写）
        if self._session:
            self._session.activate()
        
        try:
            result = self._graph.invoke({
                "messages": self._chat_history + [HumanMessage(content=user_message)],
            })
            
            messages = result.get("messages", [])
            response = ""
            for msg in reversed(messages):
                if msg.type == "ai" and msg.content:
                    response = msg.content
                    break
            
            if not response:
                response = "抱歉，我暂时无法回复。"
            
            # 更新对话历史（追加前检查容量，保持 human/ai 对匹配）
            if len(self._chat_history) >= MAX_CHAT_HISTORY:
                self._chat_history = self._chat_history[-(MAX_CHAT_HISTORY - 2):]
            self._chat_history.append(HumanMessage(content=user_message))
            self._chat_history.append(AIMessage(content=response))
            
            return response
            
        except Exception:
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
        """清理 session state"""
        if self._session:
            self._session.cleanup()
    
    def _get_fallback_response(self, user_message: str) -> str:
        """无 API 时的回退响应"""
        return (
            '收到你说"' + user_message + '"。\n\n'
            "不过我还没有连接到 AI 大脑，需要你配置一下 API Key 才能开始聊天。\n"
            "在 .env 文件中设置 OPENAI_API_KEY 或 DASHSCOPE_API_KEY 即可。\n\n"
            "如果你只是想测试，我可以给你一个简单的推荐：\n"
            "不知道吃什么的话，来碗麻辣烫总没错！"
        )
