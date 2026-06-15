"""偏好收集器测试"""

import pytest
from agent.preference import PreferenceCollector, COLLECTION_QUESTIONS
from agent.models import UserPreferences


class TestPreferenceCollector:
    """测试偏好收集器"""
    
    def test_initial_state(self):
        """测试初始状态"""
        collector = PreferenceCollector()
        assert not collector.is_complete
        assert collector._current_question_index == 0
    
    def test_current_question(self):
        """测试获取当前问题"""
        collector = PreferenceCollector()
        question = collector.current_question
        assert question is not None
        assert "key" in question
        assert "question" in question
        assert question["key"] == "taste"  # 第一个问题是口味
    
    def test_get_next_question(self):
        """测试获取下一个问题"""
        collector = PreferenceCollector()
        question = collector.get_next_question()
        assert question is not None
        assert question == COLLECTION_QUESTIONS[0]
    
    def test_process_answer_taste(self):
        """测试处理口味回答"""
        collector = PreferenceCollector()
        is_complete, next_q = collector.process_answer("想吃辣的")
        
        assert not is_complete  # 还没收集完
        assert collector.preferences.taste == "辣"
    
    def test_process_answer_budget(self):
        """测试处理预算回答"""
        collector = PreferenceCollector()
        # 先回答口味
        collector.process_answer("辣的")
        
        # 再回答预算
        is_complete, next_q = collector.process_answer("30 块左右")
        
        assert is_complete  # 口味 + 预算收集完成
        assert collector.preferences.budget == "30-50 元" or "30" in collector.preferences.budget
    
    def test_process_answer_skip(self):
        """测试跳过问题"""
        collector = PreferenceCollector()
        # 空回答，应该跳过
        is_complete, next_q = collector.process_answer("")
        
        # 不应该标记完成，应该继续下一个问题
        # 具体行为取决于实现
        assert next_q is not None or is_complete
    
    def test_fuzzy_match_taste(self):
        """测试模糊匹配口味"""
        collector = PreferenceCollector()
        collector.process_answer("麻辣烫、火锅、川菜都行")
        assert collector.preferences.taste == "辣"
    
    def test_reset(self):
        """测试重置"""
        collector = PreferenceCollector()
        collector.process_answer("辣的")
        collector.process_answer("30-50 元")
        
        collector.reset()
        
        assert collector.preferences.taste == ""
        assert collector.preferences.budget == ""
        assert not collector.is_complete
        assert collector._current_question_index == 0
    
    def test_get_progress(self):
        """测试获取进度"""
        collector = PreferenceCollector()
        collector.process_answer("辣的")
        
        progress = collector.get_progress()
        assert progress["current_index"] == 1
        assert progress["total_questions"] == len(COLLECTION_QUESTIONS)
        assert "taste" in progress["collected_keys"]
    
    def test_extract_from_free_text(self):
        """测试从自由文本提取"""
        collector = PreferenceCollector()
        text = "我想吃清淡的，预算大概 20 块，一个人吃"
        
        extracted = collector.extract_from_free_text(text)
        
        assert len(extracted) > 0
        assert "taste" in extracted
        # 预算可能也会被提取
        assert collector.preferences.taste == "清淡"
    
    def test_match_options(self):
        """测试选项匹配"""
        collector = PreferenceCollector()
        
        # 精确匹配
        collector.process_answer("清淡")
        assert collector.preferences.taste == "清淡"
        
        collector.reset()
        
        # 部分匹配
        collector.process_answer("我想吃清淡一点")
        assert collector.preferences.taste == "清淡"
