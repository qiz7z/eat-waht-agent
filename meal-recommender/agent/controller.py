"""Agent 控制器 - 管理推荐流程，协调偏好收集和推荐生成"""

from typing import Dict, List, Optional
from .models import UserPreferences, Recommendation
from .preference import PreferenceCollector
from .recommendation import RecommendationEngine
from .context import ContextService


# 对话状态枚举
class ConversationState:
    WELCOME = "welcome"          # 欢迎状态
    COLLECTING = "collecting"    # 收集偏好中
    RECOMMENDING = "recommending" # 生成推荐中
    COMPLETED = "completed"       # 推荐完成
    RESET = "reset"               # 重新开始


# 欢迎语
WELCOME_MESSAGE = """🍽️ 嗨！不知道吃什么？我来帮你！

简单聊几句，帮你挑顿合胃口的。
- 口味偏好？预算多少？
- 心情怎么样？一个人还是和朋友？

直接告诉我你的想法就行 🎯"""

# 推荐完成后的提示
AFTER_RECOMMENDATION_MESSAGE = """💡 不满意可以告诉我，我再帮你想想别的～

或者输入"重新开始"再来一轮推荐！"""


class AgentController:
    """Agent 控制器 - 协调各个模块的处理流程"""
    
    def __init__(self):
        self._state = ConversationState.WELCOME
        self._collector = PreferenceCollector()
        self._engine = RecommendationEngine()
        self._context_service = ContextService()
        self._current_recommendation: Optional[Recommendation] = None
    
    @property
    def state(self) -> str:
        """获取当前对话状态"""
        return self._state
    
    def start_conversation(self) -> str:
        """开始对话
        
        Returns:
            str: 欢迎语
        """
        self._state = ConversationState.COLLECTING
        
        # 自动设置就餐时间
        meal_time = self._context_service.get_current_meal_time()
        self._collector.set_preference("meal_time", meal_time)
        
        # 自动设置天气
        weather = self._context_service.get_weather_condition()
        self._collector.set_preference("weather", weather)
        
        return WELCOME_MESSAGE
    
    def process_user_input(self, user_input: str) -> str:
        """处理用户输入
        
        Args:
            user_input: 用户输入的消息
            
        Returns:
            str: 回复消息
        """
        # 检查是否要重新开始
        if "重新开始" in user_input or "reset" in user_input.lower():
            self._reset()
            return self.start_conversation()
        
        if self._state == ConversationState.WELCOME:
            return self.start_conversation()
        
        if self._state == ConversationState.COLLECTING:
            return self._handle_collecting(user_input)
        
        if self._state == ConversationState.COMPLETED:
            return self._handle_completed(user_input)
        
        return WELCOME_MESSAGE
    
    def _handle_collecting(self, user_input: str) -> str:
        """处理偏好收集阶段
        
        Args:
            user_input: 用户输入
            
        Returns:
            str: 回复消息
        """
        # 处理用户回答
        is_complete, next_question = self._collector.process_answer(user_input)
        
        if is_complete:
            # 偏好收集完成，生成推荐
            self._state = ConversationState.RECOMMENDING
            return self._generate_and_return_recommendation()
        else:
            # 继续收集
            if next_question:
                return next_question["question"]
            else:
                # 理论上不会到这里，但作为安全措施
                self._state = ConversationState.RECOMMENDING
                return self._generate_and_return_recommendation()
    
    def _generate_and_return_recommendation(self) -> str:
        """生成并返回推荐结果
        
        Returns:
            str: 格式化的推荐结果
        """
        preferences = self._collector.preferences
        context = {
            "meal_time": preferences.meal_time,
            "weather": preferences.weather,
        }
        
        # 生成推荐
        self._current_recommendation = self._engine.generate_recommendation(
            preferences=preferences,
            context=context,
        )
        
        # 格式化输出
        output = self._current_recommendation.format_output()
        output += f"\n\n{AFTER_RECOMMENDATION_MESSAGE}"
        
        self._state = ConversationState.COMPLETED
        return output
    
    def _handle_completed(self, user_input: str) -> str:
        """处理推荐完成后的交互
        
        Args:
            user_input: 用户输入
            
        Returns:
            str: 回复消息
        """
        # 用户可能想再要推荐或重新开始
        if "换一个" in user_input or "再来" in user_input or "其他" in user_input:
            # 从备选中选一个或重新推荐
            if self._current_recommendation and self._current_recommendation.alternatives:
                alts = self._current_recommendation.alternatives
                response = "💡 看看这些备选：\n\n"
                for i, alt in enumerate(alts, 1):
                    response += f"**{i}. {alt.name}** - {alt.reason}\n"
                    if alt.details:
                        response += f"   {alt.details}\n"
                response += f"\n{AFTER_RECOMMENDATION_MESSAGE}"
                return response
            else:
                return '没有其他备选了，要不要重新开始一轮推荐？输入"重新开始"即可。'
        
        # 默认的温柔回复
        return '有任何想法随时告诉我～ 或者直接说"重新开始"再来一轮！'
    
    def _reset(self):
        """重置控制器状态"""
        self._state = ConversationState.WELCOME
        self._collector.reset()
        self._current_recommendation = None
    
    def get_current_state(self) -> Dict:
        """获取当前对话状态详情
        
        Returns:
            Dict: 包含状态信息的字典
        """
        return {
            "state": self._state,
            "preferences": self._collector.preferences.get_summary(),
            "progress": self._collector.get_progress(),
            "has_recommendation": self._current_recommendation is not None,
        }
