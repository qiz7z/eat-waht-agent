"""数据模型定义"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class UserPreferences:
    """用户偏好数据模型"""
    taste: str = ""           # 口味偏好 (清淡/重口/辣/不辣/随意)
    budget: str = ""          # 预算范围 (10 元以下/10-30 元/30-50 元/50 元以上)
    meal_time: str = ""       # 就餐时间 (早餐/午餐/晚餐/夜宵)
    weather: str = ""         # 天气情况 (晴天/雨天/高温/寒冷)
    mood: str = ""            # 心情状态 (开心/疲惫/压力大/无所谓)
    health: str = ""          # 健康需求 (减肥/增肌/素食/无特殊需求)
    social: str = ""          # 社交场景 (独自/聚餐/约会/赶时间)
    count: int = 1            # 就餐人数
    
    def is_complete(self) -> bool:
        """检查偏好是否收集完成（至少需要口味和预算）"""
        return bool(self.taste) and bool(self.budget)
    
    def get_summary(self) -> str:
        """获取偏好摘要"""
        parts = []
        if self.taste:
            parts.append(f"口味：{self.taste}")
        if self.budget:
            parts.append(f"预算：{self.budget}")
        if self.meal_time:
            parts.append(f"时间：{self.meal_time}")
        if self.weather:
            parts.append(f"天气：{self.weather}")
        if self.mood:
            parts.append(f"心情：{self.mood}")
        if self.health:
            parts.append(f"健康：{self.health}")
        if self.social:
            parts.append(f"场景：{self.social}")
        if self.count > 1:
            parts.append(f"人数：{self.count}")
        return " | ".join(parts) if parts else "无特殊偏好"


@dataclass
class RecommendationItem:
    """单个推荐项"""
    name: str = ""            # 推荐名称
    reason: str = ""          # 推荐理由
    details: str = ""         # 详细说明
    price_estimate: str = ""  # 预估价格
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "reason": self.reason,
            "details": self.details,
            "price_estimate": self.price_estimate,
        }


@dataclass
class Recommendation:
    """推荐结果数据模型"""
    primary: Optional[RecommendationItem] = None   # 主要推荐
    alternatives: List[RecommendationItem] = field(default_factory=list)  # 备选方案
    summary: str = ""                              # 推荐理由总结
    
    def is_valid(self) -> bool:
        """检查推荐是否有效"""
        return self.primary is not None and bool(self.primary.name)
    
    def format_output(self) -> str:
        """格式化输出推荐结果"""
        if not self.is_valid():
            return "抱歉，暂时没有合适的推荐。"
        
        lines = []
        lines.append("## 为你推荐")
        lines.append("")
        lines.append(f"### 🎯 首选：{self.primary.name}")
        lines.append(f"**推荐理由**：{self.primary.reason}")
        if self.primary.details:
            lines.append(f"**详情**：{self.primary.details}")
        if self.primary.price_estimate:
            lines.append(f"**预估价格**：{self.primary.price_estimate}")
        
        if self.alternatives:
            lines.append("")
            lines.append("### 💡 其他选择")
            for i, alt in enumerate(self.alternatives, 1):
                lines.append(f"**{i}. {alt.name}** - {alt.reason}")
        
        if self.summary:
            lines.append("")
            lines.append(f"---")
            lines.append(f"**总结**：{self.summary}")
        
        return "\n".join(lines)
