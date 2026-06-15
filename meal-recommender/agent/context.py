"""上下文服务 - 获取时间、天气等外部上下文信息"""

from datetime import datetime
from typing import Dict, Optional


class ContextService:
    """获取外部上下文信息的服务类"""
    
    # 时间段映射
    MEAL_TIME_RANGES = {
        "早餐": (5, 9),
        "午餐": (11, 13),
        "晚餐": (17, 19),
        "夜宵": (21, 23),
    }
    
    def __init__(self):
        self._current_time: Optional[datetime] = None
    
    def get_current_meal_time(self) -> str:
        """获取当前就餐时间段
        
        Returns:
            str: 早餐/午餐/晚餐/夜宵
        """
        now = self._current_time or datetime.now()
        hour = now.hour
        
        for meal_name, (start, end) in self.MEAL_TIME_RANGES.items():
            if start <= hour < end + 2:  # 放宽时间段，避免空白期
                return meal_name
        
        # 默认根据时间段判断
        if 0 <= hour < 5:
            return "夜宵"
        elif 5 <= hour < 11:
            return "早餐"
        elif 11 <= hour < 14:
            return "午餐"
        elif 14 <= hour < 21:
            return "晚餐"
        else:
            return "夜宵"
    
    def get_weather_info(self, location: str = "") -> Dict[str, str]:
        """获取天气信息
        
        Args:
            location: 位置信息（可选）
            
        Returns:
            Dict: 包含天气信息的字典
        """
        # 注意：这里返回模拟数据，实际可对接天气 API
        weather_data = {
            "condition": "晴天",
            "temperature": "25°C",
            "humidity": "60%",
            "wind": "微风",
        }
        
        # 如果对接了天气 API，可以按 location 获取真实数据
        # 这里暂时返回默认值
        return weather_data
    
    def get_weather_condition(self, location: str = "") -> str:
        """获取天气状况描述（简化版）
        
        Args:
            location: 位置信息（可选）
            
        Returns:
            str: 天气状况（晴天/雨天/高温/寒冷）
        """
        # 实际应用中应该对接天气 API
        # 这里仅作为示例返回默认值
        return "晴天"
    
    def get_context_summary(self, location: str = "") -> str:
        """获取综合上下文描述
        
        Args:
            location: 位置信息（可选）
            
        Returns:
            str: 上下文描述
        """
        meal_time = self.get_current_meal_time()
        weather = self.get_weather_condition(location)
        now = self._current_time or datetime.now()
        
        return f"{meal_time}时间 | 天气：{weather} | 时间：{now.strftime('%H:%M')}"
    
    @classmethod
    def for_testing(cls, fixed_time: datetime) -> 'ContextService':
        """创建一个固定时间的上下文服务（用于测试）
        
        Args:
            fixed_time: 固定的时间
            
        Returns:
            ContextService: 上下文服务实例
        """
        service = cls()
        service._current_time = fixed_time
        return service
