"""偏好收集器 - 管理多轮对话收集用户偏好"""

from typing import Dict, List, Optional, Tuple
from .models import UserPreferences


# 偏好收集问题序列
COLLECTION_QUESTIONS = [
    {
        "key": "taste",
        "question": "想吃点什么口味的？清淡、重口、辣的、还是随，你决定。",
        "options": ["清淡", "重口", "辣", "不辣", "随意"],
    },
    {
        "key": "budget",
        "question": "今天预算多少？",
        "options": ["10 元以下", "10-30 元", "30-50 元", "50 元以上"],
    },
    {
        "key": "health",
        "question": "有什么饮食特殊需求吗？比如减肥、增肌、素食之类的。",
        "options": ["减肥", "增肌", "素食", "无特殊需求"],
    },
    {
        "key": "social",
        "question": "一个人吃还是和朋友一起？或者赶时间？",
        "options": ["独自", "聚餐", "约会", "赶时间"],
    },
    {
        "key": "mood",
        "question": "现在心情怎么样？这顿想犒劳自己还是随便吃？",
        "options": ["开心", "疲惫", "压力大", "无所谓"],
    },
]


class PreferenceCollector:
    """偏好收集器 - 通过多轮对话收集用户偏好"""
    
    def __init__(self):
        self._preferences = UserPreferences()
        self._current_question_index = 0
        self._collected_keys: set = set()
    
    @property
    def preferences(self) -> UserPreferences:
        """获取当前收集的偏好"""
        return self._preferences
    
    @property
    def is_complete(self) -> bool:
        """是否收集完成（至少需要口味和预算）"""
        return self._preferences.is_complete()
    
    @property
    def current_question(self) -> Optional[Dict]:
        """获取当前问题"""
        if self._current_question_index < len(COLLECTION_QUESTIONS):
            return COLLECTION_QUESTIONS[self._current_question_index]
        return None
    
    def get_next_question(self) -> Optional[Dict]:
        """获取下一个需要询问的问题
        
        Returns:
            Optional[Dict]: 下一个问题，如果没有更多问题则返回 None
        """
        if self._current_question_index >= len(COLLECTION_QUESTIONS):
            return None
        return COLLECTION_QUESTIONS[self._current_question_index]
    
    def process_answer(self, answer: str) -> Tuple[bool, Optional[str]]:
        """处理用户回答
        
        Args:
            answer: 用户的回答
            
        Returns:
            Tuple[bool, Optional[str]]: (是否已收集到足够的信息，下一个问题或 None)
        """
        # 尝试匹配当前问题
        if self._current_question_index < len(COLLECTION_QUESTIONS):
            question = COLLECTION_QUESTIONS[self._current_question_index]
            
            # 智能匹配答案
            matched_value = self._match_answer(question, answer)
            if matched_value:
                setattr(self._preferences, question["key"], matched_value)
                self._collected_keys.add(question["key"])
                self._current_question_index += 1
        
        # 检查是否收集到足够的信息（至少口味和预算）
        if self.is_complete:
            return True, None
        
        # 返回下一个问题
        next_q = self.get_next_question()
        return False, next_q
    
    def _match_answer(self, question: Dict, answer: str) -> Optional[str]:
        """智能匹配用户答案
        
        Args:
            question: 问题定义
            answer: 用户回答
            
        Returns:
            Optional[str]: 匹配到的预设值，如果没有匹配到则返回原始回答
        """
        answer_lower = answer.lower().strip()
        
        # 尝试匹配预设选项
        for option in question.get("options", []):
            if option.lower() in answer_lower or answer_lower in option.lower():
                return option
        
        # 处理模糊表达
        fuzz_mappings = {
            "taste": {
                "清淡": ["清淡", "清谈", "轻口味", "不重"],
                "重口": ["重口", "重口味", "味道重"],
                "辣": ["辣", "麻辣", "香辣", "酸辣", "湖南菜", "川菜"],
                "不辣": ["不辣", "微辣", "一点点辣"],
            },
            "budget": {
                "10 元以下": ["10", "十块", "便宜", "省钱"],
                "10-30 元": ["10-30", "20", "二十", "一般", "正常"],
                "30-50 元": ["30-50", "40", "四十", "稍微好点"],
                "50 元以上": ["50", "五十", "多点", "不差钱", "吃好的"],
            },
        }
        
        key = question["key"]
        if key in fuzz_mappings:
            for value, keywords in fuzz_mappings[key].items():
                for kw in keywords:
                    if kw in answer_lower:
                        return value
        
        # 没有匹配到预设值，返回原始回答
        return answer.strip() if answer.strip() else None
    
    def set_preference(self, key: str, value: str) -> None:
        """设置偏好值
        
        Args:
            key: 偏好键名
            value: 偏好值
        """
        if hasattr(self._preferences, key):
            setattr(self._preferences, key, value)
            self._collected_keys.add(key)
    
    def reset(self):
        """重置收集器，开始新的对话"""
        self._preferences = UserPreferences()
        self._current_question_index = 0
        self._collected_keys.clear()
    
    def get_progress(self) -> Dict:
        """获取收集进度
        
        Returns:
            Dict: 包含当前进度的信息
        """
        return {
            "current_index": self._current_question_index,
            "total_questions": len(COLLECTION_QUESTIONS),
            "collected_keys": list(self._collected_keys),
            "is_complete": self.is_complete,
            "preferences_summary": self._preferences.get_summary(),
        }
    
    def extract_from_free_text(self, text: str) -> List[str]:
        """从自由文本中提取偏好信息
        
        用于处理用户一次性提供多个偏好的情况
        
        Args:
            text: 用户输入的自由文本
            
        Returns:
            List[str]: 提取到的偏好键列表
        """
        extracted = []
        text_lower = text.lower().strip()
        
        for question in COLLECTION_QUESTIONS:
            key = question["key"]
            # 直接尝试匹配预设值和模糊关键词
            matched = self._match_answer(question, text)
            if matched:
                setattr(self._preferences, key, matched)
                self._collected_keys.add(key)
                extracted.append(key)
        
        return extracted
