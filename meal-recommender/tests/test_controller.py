"""Agent 控制器测试"""

import pytest
from unittest.mock import patch, MagicMock
from agent.controller import AgentController, ConversationState, WELCOME_MESSAGE


class TestAgentController:
    """测试 Agent 控制器"""
    
    def test_start_conversation(self):
        """测试开始对话"""
        controller = AgentController()
        response = controller.start_conversation()
        
        assert response == WELCOME_MESSAGE
        assert controller.state == ConversationState.COLLECTING
    
    def test_welcome_state(self):
        """测试欢迎状态"""
        controller = AgentController()
        assert controller.state == ConversationState.WELCOME
        
        # 第一次输入应该返回欢迎语并进入收集状态
        response = controller.process_user_input("你好")
        assert response == WELCOME_MESSAGE
    
    def test_collecting_state(self):
        """测试收集状态"""
        controller = AgentController()
        controller.start_conversation()
        
        # 回答口味问题
        response = controller.process_user_input("我想吃辣的")
        
        # 应该进入下一个问题（预算）
        assert "预算" in response or controller.state == ConversationState.RECOMMENDING
    
    @patch('agent.recommendation.RecommendationEngine.generate_recommendation')
    def test_complete_collection(self, mock_generate):
        """测试完成偏好收集"""
        # Mock the recommendation engine to avoid LLM timeout
        from agent.models import Recommendation, RecommendationItem
        mock_generate.return_value = Recommendation(
            primary=RecommendationItem(name="火锅", reason="好吃", details="推荐麻辣锅", price_estimate="30-50 元"),
            alternatives=[
                RecommendationItem(name="串串", reason="也不错"),
                RecommendationItem(name="麻辣烫", reason="便宜实惠"),
            ],
            summary="火锅最佳",
        )
        
        controller = AgentController()
        controller.start_conversation()
        
        # 快速完成口味和预算
        controller.process_user_input("辣的")
        response = controller.process_user_input("30 块")
        
        # 应该生成推荐
        assert controller.state == ConversationState.COMPLETED
        assert "火锅" in response
    
    @patch('agent.recommendation.RecommendationEngine.generate_recommendation')
    def test_reset_conversation(self, mock_generate):
        """测试重置对话"""
        from agent.models import Recommendation, RecommendationItem
        mock_generate.return_value = Recommendation(
            primary=RecommendationItem(name="火锅", reason="好吃", details="推荐麻辣锅", price_estimate="30-50 元"),
            alternatives=[],
            summary="火锅最佳",
        )
        
        controller = AgentController()
        controller.start_conversation()
        controller.process_user_input("辣的")
        controller.process_user_input("30 块")
        
        assert controller.state == ConversationState.COMPLETED
        
        # 重置
        response = controller.process_user_input("重新开始")
        
        assert controller.state == ConversationState.COLLECTING
        assert response == WELCOME_MESSAGE
    
    def test_get_current_state(self):
        """测试获取当前状态"""
        controller = AgentController()
        controller.start_conversation()
        
        state_info = controller.get_current_state()
        
        assert state_info["state"] == ConversationState.COLLECTING
        assert "preferences" in state_info
        assert "progress" in state_info
    
    @patch('agent.recommendation.RecommendationEngine.generate_recommendation')
    def test_completed_interaction(self, mock_generate):
        """测试推荐完成后的交互"""
        from agent.models import Recommendation, RecommendationItem
        mock_generate.return_value = Recommendation(
            primary=RecommendationItem(name="火锅", reason="好吃", details="推荐麻辣锅", price_estimate="30-50 元"),
            alternatives=[
                RecommendationItem(name="串串", reason="也不错"),
                RecommendationItem(name="麻辣烫", reason="便宜实惠"),
            ],
            summary="火锅最佳",
        )
        
        controller = AgentController()
        controller.start_conversation()
        controller.process_user_input("辣的")
        controller.process_user_input("30 块")
        
        assert controller.state == ConversationState.COMPLETED
        
        # 在完成后继续对话
        response = controller.process_user_input("还有别的选择吗")
        
        # 应该有回复
        assert response is not None
        assert len(response) > 0
    
    def test_process_user_input_empty(self):
        """测试处理空输入"""
        controller = AgentController()
        controller.start_conversation()
        
        response = controller.process_user_input("   ")
        # 空输入不应产生错误
        assert response is not None
