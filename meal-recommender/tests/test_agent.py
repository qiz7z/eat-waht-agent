"""Agent 模块测试"""

import pytest
from unittest.mock import patch, MagicMock
from agent.agent import MealRecommenderAgent


class TestMealRecommenderAgent:
    """测试 MealRecommenderAgent"""
    
    def test_init_without_api_key(self):
        """测试无 API Key 初始化"""
        agent = MealRecommenderAgent(api_key="")
        assert agent.is_ready is False
    
    def test_fallback_response(self):
        """测试无 API 时的回退响应"""
        agent = MealRecommenderAgent(api_key="")
        response = agent.invoke("想吃辣的")
        assert "麻辣烫" in response
    
    def test_reset(self):
        """测试重置"""
        agent = MealRecommenderAgent(api_key="")
        agent.invoke("辣")
        agent.reset()
        history = agent.get_chat_history()
        assert history == []
    
    @patch('agent.agent.ChatOpenAI')
    def test_invoke_with_api(self, mock_chat_openai):
        """测试有 API Key 时调用"""
        mock_llm = MagicMock()
        mock_chat_openai.return_value = mock_llm
        
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            agent = MealRecommenderAgent(api_key='test-key')
            assert agent.is_ready is True
