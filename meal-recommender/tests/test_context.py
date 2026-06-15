"""上下文服务测试"""

import pytest
from datetime import datetime
from agent.context import ContextService


class TestContextService:
    """测试上下文服务"""
    
    def test_get_current_meal_time_morning(self):
        """测试早餐时间段"""
        service = ContextService.for_testing(datetime(2024, 1, 1, 7, 0))
        assert service.get_current_meal_time() == "早餐"
    
    def test_get_current_meal_time_lunch(self):
        """测试午餐时间段"""
        service = ContextService.for_testing(datetime(2024, 1, 1, 12, 0))
        assert service.get_current_meal_time() == "午餐"
    
    def test_get_current_meal_time_dinner(self):
        """测试晚餐时间段"""
        service = ContextService.for_testing(datetime(2024, 1, 1, 18, 0))
        assert service.get_current_meal_time() == "晚餐"
    
    def test_get_current_meal_time_late_night(self):
        """测试夜宵时间段"""
        service = ContextService.for_testing(datetime(2024, 1, 1, 22, 0))
        assert service.get_current_meal_time() == "夜宵"
    
    def test_get_current_meal_time_early_morning(self):
        """测试凌晨时间段归为夜宵"""
        service = ContextService.for_testing(datetime(2024, 1, 1, 2, 0))
        assert service.get_current_meal_time() == "夜宵"
    
    def test_get_weather_info(self):
        """测试天气信息获取"""
        service = ContextService()
        weather = service.get_weather_info()
        assert isinstance(weather, dict)
        assert "condition" in weather
        assert "temperature" in weather
    
    def test_get_weather_condition(self):
        """测试天气状况获取"""
        service = ContextService()
        condition = service.get_weather_condition()
        assert isinstance(condition, str)
        assert condition  # 非空
    
    def test_get_context_summary(self):
        """测试上下文摘要"""
        service = ContextService.for_testing(datetime(2024, 1, 1, 12, 30))
        summary = service.get_context_summary()
        assert "午餐" in summary
        assert "天气" in summary
    
    def test_current_time_default(self):
        """测试默认使用当前时间"""
        service = ContextService()
        # 不应抛出异常
        service.get_current_meal_time()
