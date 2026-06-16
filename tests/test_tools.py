"""LangChain Tools 测试"""

import pytest
from agent.tools import (
    _save_preference as save_preference_fn,
    _get_preferences as get_preferences_fn,
    _get_context_info as get_context_info_fn,
    _reset_preferences as reset_preferences_fn,
    _generate_recommendation as generate_recommendation_fn,
    SessionStateManager,
    _current_agent_id,
)


class TestToolsWithSession:
    """测试 Agent Tools（带 session state）"""
    
    def setup_method(self):
        """每次测试前创建独立的 session"""
        self._session = SessionStateManager()
        self._session.activate()
    
    def teardown_method(self):
        """清理 session"""
        self._session.cleanup()
    
    def test_save_preference_taste(self):
        """测试保存口味偏好"""
        result = save_preference_fn("taste", "辣")
        assert result == "已记录：taste = 辣"
        state = self._session.get_state()
        assert state["taste"] == "辣"
    
    def test_save_preference_budget(self):
        """测试保存预算"""
        save_preference_fn("budget", "30-50 元")
        state = self._session.get_state()
        assert state["budget"] == "30-50 元"
    
    def test_get_preferences_empty(self):
        """测试空偏好"""
        result = get_preferences_fn()
        assert "还没有" in result
    
    def test_get_preferences_with_values(self):
        """测试有值时获取偏好"""
        save_preference_fn("taste", "辣")
        save_preference_fn("budget", "15-25 元")
        
        result = get_preferences_fn()
        assert "口味：辣" in result
        assert "预算：15-25 元" in result
    
    def test_get_context_info(self):
        """测试获取上下文信息"""
        result = get_context_info_fn()
        assert "时间" in result
        assert "天气" in result
        
        state = self._session.get_state()
        assert state["meal_time"] != ""
        assert state["weather"] != ""
    
    def test_reset_preferences(self):
        """测试重置偏好"""
        save_preference_fn("taste", "辣")
        
        result = reset_preferences_fn()
        assert "重置" in result
        
        state = self._session.get_state()
        assert state["taste"] == ""
        assert state["budget"] == ""
    
    def test_generate_recommendation_spicy(self):
        """测试辣口味推荐"""
        save_preference_fn("taste", "辣")
        save_preference_fn("budget", "20-30 元")
        
        result = generate_recommendation_fn()
        assert "麻辣烫" in result or "串串" in result
        assert "备选" in result
    
    def test_generate_recommendation_light(self):
        """测试清淡口味推荐"""
        save_preference_fn("taste", "清淡")
        save_preference_fn("budget", "10-15 元")
        
        result = generate_recommendation_fn()
        # 推荐系统现在调用食物数据库，返回的结果可能不同
        # 只要包含推荐内容即可
        assert "推荐" in result or "帮你想好了" in result
    
    def test_generate_recommendation_default(self):
        """测试默认推荐"""
        result = generate_recommendation_fn()
        assert "麻辣烫" in result
    
    def test_generate_recommendation_sets_flag(self):
        """测试推荐后设置标记"""
        generate_recommendation_fn()
        state = self._session.get_state()
        assert state["has_recommendation"] is True
    
    def test_session_isolation(self):
        """测试不同 agent 之间状态隔离"""
        session_a = SessionStateManager()
        session_b = SessionStateManager()
        
        session_a.activate()
        save_preference_fn("taste", "辣")
        
        session_b.activate()
        save_preference_fn("taste", "清淡")
        
        state_a = session_a.get_state()
        state_b = session_b.get_state()
        
        assert state_a["taste"] == "辣"
        assert state_b["taste"] == "清淡"
        
        session_a.cleanup()
        session_b.cleanup()
