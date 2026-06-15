"""数据模型测试"""

import pytest
from datetime import datetime
from agent.models import UserPreferences, Recommendation, RecommendationItem


class TestUserPreferences:
    """测试用户偏好数据模型"""
    
    def test_default_values(self):
        """测试默认值"""
        prefs = UserPreferences()
        assert prefs.taste == ""
        assert prefs.budget == ""
        assert prefs.meal_time == ""
        assert prefs.count == 1
    
    def test_is_complete_empty(self):
        """测试空偏好未完成"""
        prefs = UserPreferences()
        assert not prefs.is_complete()
    
    def test_is_complete_with_taste_and_budget(self):
        """测试有口味和预算则完成"""
        prefs = UserPreferences(taste="辣", budget="30-50 元")
        assert prefs.is_complete()
    
    def test_is_complete_missing_budget(self):
        """测试只有口味未完成"""
        prefs = UserPreferences(taste="辣")
        assert not prefs.is_complete()
    
    def test_get_summary_empty(self):
        """测试空偏好摘要"""
        prefs = UserPreferences()
        assert prefs.get_summary() == "无特殊偏好"
    
    def test_get_summary_with_values(self):
        """测试有值的偏好摘要"""
        prefs = UserPreferences(
            taste="辣",
            budget="30-50 元",
            meal_time="午餐",
            weather="晴天",
            mood="开心",
        )
        summary = prefs.get_summary()
        assert "口味：辣" in summary
        assert "预算：30-50 元" in summary
        assert "时间：午餐" in summary


class TestRecommendationItem:
    """测试推荐项数据模型"""
    
    def test_default_values(self):
        """测试默认值"""
        item = RecommendationItem()
        assert item.name == ""
        assert item.reason == ""
    
    def test_to_dict(self):
        """测试转字典"""
        item = RecommendationItem(
            name="火锅",
            reason="适合聚餐",
            details="推荐麻辣火锅",
            price_estimate="50-80 元",
        )
        result = item.to_dict()
        assert result["name"] == "火锅"
        assert result["reason"] == "适合聚餐"
        assert result["details"] == "推荐麻辣火锅"
        assert result["price_estimate"] == "50-80 元"


class TestRecommendation:
    """测试推荐结果数据模型"""
    
    def test_default_values(self):
        """测试默认值"""
        rec = Recommendation()
        assert rec.primary is None
        assert rec.alternatives == []
        assert rec.summary == ""
    
    def test_is_valid_no_primary(self):
        """测试无主推荐无效"""
        rec = Recommendation()
        assert not rec.is_valid()
    
    def test_is_valid_with_primary(self):
        """测试有主推荐有效"""
        rec = Recommendation(
            primary=RecommendationItem(name="火锅", reason="好吃"),
        )
        assert rec.is_valid()
    
    def test_is_valid_empty_name(self):
        """测试主推荐名称为空无效"""
        rec = Recommendation(
            primary=RecommendationItem(name="", reason="好吃"),
        )
        assert not rec.is_valid()
    
    def test_format_output(self):
        """测试格式化输出"""
        rec = Recommendation(
            primary=RecommendationItem(
                name="火锅",
                reason="适合聚餐",
                details="推荐麻辣锅",
                price_estimate="60 元",
            ),
            alternatives=[
                RecommendationItem(name="烤肉", reason="也不错"),
            ],
            summary="火锅最佳",
        )
        output = rec.format_output()
        assert "火锅" in output
        assert "适合聚餐" in output
        assert "烤肉" in output
        assert "火锅最佳" in output
    
    def test_format_output_invalid(self):
        """测试无效推荐格式化"""
        rec = Recommendation()
        output = rec.format_output()
        assert "暂时没有合适的推荐" in output
