"""推荐引擎 - 基于大语言模型生成餐饮推荐"""

from typing import Dict, List, Optional
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from .config import build_chat_openai_kwargs, get_llm_config
from .models import UserPreferences, Recommendation, RecommendationItem


# 推荐提示词模板
RECOMMENDATION_PROMPT = """你是一个专门为中国大学生推荐餐饮的 AI 助手。

## 用户偏好
{preferences}

## 当前上下文
{context}

## 推荐规则
1. 根据用户口味、预算、天气、心情等因素给出个性化推荐
2. 推荐必须符合大学生的消费水平和用餐场景
3. 主要推荐 1 个最符合用户需求的选项
4. 备选方案 2 个，提供不同选择
5. 推荐理由要具体，结合用户的偏好说明为什么推荐这个
6. 推荐内容应该包括：菜品名称、推荐理由、预估价格、详细说明

## 输出格式
请严格按照以下 JSON 格式返回结果，不要添加任何其他内容：

{{
  "primary": {{
    "name": "主要推荐的菜品或餐厅类型",
    "reason": "推荐理由，结合用户偏好说明",
    "details": "详细说明，包括具体可以点什么、在哪吃等",
    "price_estimate": "预估价格"
  }},
  "alternatives": [
    {{
      "name": "备选方案 1",
      "reason": "备选理由",
      "details": "备选的详细说明",
      "price_estimate": "备选价格"
    }},
    {{
      "name": "备选方案 2",
      "reason": "备选理由",
      "details": "备选的详细说明",
      "price_estimate": "备选价格"
    }}
  ],
  "summary": "一句话总结推荐理由"
}}

请根据用户的具体情况给出合适的推荐。"""


class RecommendationEngine:
    """推荐引擎 - 调用大模型生成推荐结果"""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """初始化推荐引擎
        
        Args:
            model_name: 模型名称，默认使用统一配置
            api_key: API Key，默认使用统一配置
            base_url: API Base URL，默认使用统一配置
        """
        self._llm_config = get_llm_config(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
        )
        self._llm = None
        self._initialize_llm()
    
    def _initialize_llm(self):
        """初始化大语言模型"""
        if self._llm_config.is_configured:
            self._llm = ChatOpenAI(**build_chat_openai_kwargs(self._llm_config))
    
    def generate_recommendation(
        self,
        preferences: UserPreferences,
        context: Dict[str, str]
    ) -> Recommendation:
        """生成推荐结果
        
        Args:
            preferences: 用户偏好
            context: 上下文信息
            
        Returns:
            Recommendation: 推荐结果
        """
        if not self._llm:
            # 如果没有配置 API，返回默认推荐
            return self._get_default_recommendation(preferences, context)
        
        try:
            # 构建提示词
            prompt = RECOMMENDATION_PROMPT.format(
                preferences=preferences.get_summary(),
                context=json.dumps(context, ensure_ascii=False),
            )
            
            # 调用大模型
            messages = [
                SystemMessage(content="你是一个专业的餐饮推荐助手。"),
                HumanMessage(content=prompt),
            ]
            
            response = self._llm.invoke(messages, timeout=self._llm_config.timeout)
            
            # 解析响应
            return self._parse_response(response.content)
            
        except Exception as e:
            # API 调用失败时静默回退到默认推荐
            return self._get_default_recommendation(preferences, context)
    
    def _parse_response(self, response: str) -> Recommendation:
        """解析大模型的响应
        
        Args:
            response: 大模型的文本响应
            
        Returns:
            Recommendation: 解析后的推荐结果
        """
        try:
            # 尝试提取 JSON
            json_str = response
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].strip()
            
            data = json.loads(json_str)
            
            primary_data = data.get("primary", {})
            alternatives_data = data.get("alternatives", [])
            
            primary = RecommendationItem(
                name=primary_data.get("name", ""),
                reason=primary_data.get("reason", ""),
                details=primary_data.get("details", ""),
                price_estimate=primary_data.get("price_estimate", ""),
            )
            
            alternatives = []
            for alt_data in alternatives_data[:2]:  # 最多 2 个备选
                alternatives.append(RecommendationItem(
                    name=alt_data.get("name", ""),
                    reason=alt_data.get("reason", ""),
                    details=alt_data.get("details", ""),
                    price_estimate=alt_data.get("price_estimate", ""),
                ))
            
            return Recommendation(
                primary=primary,
                alternatives=alternatives,
                summary=data.get("summary", ""),
            )
            
        except Exception:
            # 解析失败返回空推荐
            return Recommendation()
    
    def _get_default_recommendation(
        self,
        preferences: UserPreferences,
        context: Dict[str, str]
    ) -> Recommendation:
        """获取默认推荐（当 API 不可用时的回退方案）
        
        Args:
            preferences: 用户偏好
            context: 上下文信息
            
        Returns:
            Recommendation: 默认推荐结果
        """
        # 根据口味和预算给出简单推荐
        taste = preferences.taste or "随意"
        budget = preferences.budget or "10-30 元"
        meal_time = preferences.meal_time or context.get("meal_time", "午餐")
        
        # 简单的推荐映射
        recommendations = {
            "清淡": {
                "primary": "清汤面/粥配小菜",
                "reason": f"清淡口味适合{meal_time}，养胃又舒服",
                "alt1": "三明治 + 酸奶",
                "alt2": "轻食沙拉",
            },
            "重口": {
                "primary": "麻辣烫/冒菜",
                "reason": f"重口味首选，{meal_time}来一碗超满足",
                "alt1": "烤肉拌饭",
                "alt2": "重庆小面",
            },
            "辣": {
                "primary": "火锅/串串",
                "reason": f"无辣不欢，{meal_time}安排上",
                "alt1": "麻辣香锅",
                "alt2": "酸菜鱼",
            },
        }
        
        rec = recommendations.get(taste, recommendations["清淡"])
        
        return Recommendation(
            primary=RecommendationItem(
                name=rec["primary"],
                reason=rec["reason"],
                details=f"预算{budget}，可以根据偏好选择具体品类",
                price_estimate=budget,
            ),
            alternatives=[
                RecommendationItem(name=rec["alt1"], reason="同样符合你的口味"),
                RecommendationItem(name=rec["alt2"], reason="也可以考虑"),
            ],
            summary=f"根据你的口味（{taste}）和预算（{budget}），推荐{rec['primary']}。",
        )
