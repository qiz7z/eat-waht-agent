"""食物数据管理器 - 负责数据加载、查询和更新"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from .logging_config import get_logger

logger = get_logger(__name__)


class FoodDataManager:
    """管理食物数据库的加载、查询和更新"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # 使用当前文件所在目录的父目录下的data文件夹
            data_dir = Path(__file__).parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "food_database.json"
        self._database: Optional[List[Dict]] = None
        self._last_update: Optional[datetime] = None
        
    def load_database(self) -> List[Dict]:
        """加载食物数据库"""
        if self._database is not None:
            return self._database
            
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._database = data.get("foods", [])
                    last_updated_str = data.get("last_updated")
                    if last_updated_str:
                        self._last_update = datetime.fromisoformat(last_updated_str)
                logger.info("loaded_food_database count=%d", len(self._database))
            except Exception as e:
                logger.error("failed_to_load_database error=%s", e)
                self._database = self._get_default_database()
                self.save_database()
        else:
            logger.info("database_not_found_creating_default")
            self._database = self._get_default_database()
            self.save_database()
            
        return self._database
    
    def search_foods(
        self,
        taste: str = "",
        budget: str = "",
        meal_time: str = "",
        category: str = "",
        limit: int = 10
    ) -> List[Dict]:
        """搜索符合条件的食物"""
        foods = self.load_database()
        results = []
        
        for food in foods:
            # 口味匹配
            if taste:
                taste_profile = food.get("taste_profile", [])
                if isinstance(taste_profile, str):
                    taste_profile = [taste_profile]
                if taste not in taste_profile:
                    continue
                    
            # 预算匹配
            if budget and not self._budget_matches(food.get("price_range", ""), budget):
                continue
                
            # 用餐时间匹配
            if meal_time:
                meal_times = food.get("meal_times", [])
                if isinstance(meal_times, str):
                    meal_times = [meal_times]
                if meal_time not in meal_times:
                    continue
                    
            # 类别匹配
            if category and category != food.get("category", ""):
                continue
                
            results.append(food)
            
            if len(results) >= limit:
                break
                
        return results
    
    def get_trending_foods(self, limit: int = 10) -> List[Dict]:
        """获取热门食物（按热度排序）"""
        foods = self.load_database()
        sorted_foods = sorted(foods, key=lambda x: x.get("popularity", 0), reverse=True)
        return sorted_foods[:limit]
    
    def get_foods_by_category(self, category: str, limit: int = 10) -> List[Dict]:
        """按类别获取食物"""
        foods = self.load_database()
        results = [f for f in foods if f.get("category") == category]
        return results[:limit]
    
    def _budget_matches(self, food_price: str, user_budget: str) -> bool:
        """检查价格是否符合预算"""
        try:
            # 提取用户预算的数字范围
            user_budget_clean = user_budget.replace("元", "").replace("块", "").strip()
            
            if "-" in user_budget_clean:
                # 格式如 "10-30"
                parts = user_budget_clean.split("-")
                user_min = int(parts[0].strip())
                user_max = int(parts[1].strip())
            else:
                # 格式如 "20" 或 "20元"
                user_budget_num = int(user_budget_clean)
                user_min = max(0, user_budget_num - 10)
                user_max = user_budget_num + 10
            
            # 提取食物价格范围
            price_clean = food_price.replace("元", "").replace("块", "").strip()
            
            if "-" in price_clean:
                parts = price_clean.split("-")
                food_min = int(parts[0].strip())
                food_max = int(parts[1].strip())
            else:
                food_price_num = int(price_clean)
                food_min = food_price_num
                food_max = food_price_num
            
            # 检查是否有交集
            return not (food_max < user_min or food_min > user_max)
            
        except (ValueError, IndexError):
            # 解析失败时默认匹配
            return True
    
    def _get_default_database(self) -> List[Dict]:
        """获取默认数据库（离线回退）"""
        return [
            # ========== 快餐类 ==========
            {
                "id": 1,
                "name": "麻辣烫",
                "category": "快餐",
                "taste_profile": ["辣", "重口", "随意"],
                "price_range": "15-25元",
                "meal_times": ["午餐", "晚餐", "夜宵"],
                "description": "自选配菜的麻辣锅，口味可调",
                "popularity": 85,
                "tags": ["热门", "学生最爱", "可定制"]
            },
            {
                "id": 2,
                "name": "黄焖鸡米饭",
                "category": "快餐",
                "taste_profile": ["不辣", "重口"],
                "price_range": "15-20元",
                "meal_times": ["午餐", "晚餐"],
                "description": "鸡肉炖煮入味，搭配米饭",
                "popularity": 80,
                "tags": ["经典", "管饱"]
            },
            {
                "id": 3,
                "name": "冒菜",
                "category": "快餐",
                "taste_profile": ["辣", "重口"],
                "price_range": "15-25元",
                "meal_times": ["午餐", "晚餐"],
                "description": "成都特色，一人份的火锅",
                "popularity": 75,
                "tags": ["成都特色", "一人食"]
            },
            {
                "id": 4,
                "name": "炒饭/炒面",
                "category": "快餐",
                "taste_profile": ["随意"],
                "price_range": "10-18元",
                "meal_times": ["午餐", "晚餐", "夜宵"],
                "description": "经典中式快餐，口味多样",
                "popularity": 70,
                "tags": ["经典", "快速", "便宜"]
            },
            {
                "id": 5,
                "name": "盖浇饭",
                "category": "快餐",
                "taste_profile": ["不辣", "重口"],
                "price_range": "12-20元",
                "meal_times": ["午餐", "晚餐"],
                "description": "米饭配各种浇头",
                "popularity": 72,
                "tags": ["方便", "种类多"]
            },
            
            # ========== 面食类 ==========
            {
                "id": 6,
                "name": "清汤面",
                "category": "面食",
                "taste_profile": ["清淡"],
                "price_range": "8-15元",
                "meal_times": ["早餐", "午餐", "晚餐"],
                "description": "清淡爽口的汤面",
                "popularity": 65,
                "tags": ["清淡", "养胃"]
            },
            {
                "id": 7,
                "name": "重庆小面",
                "category": "面食",
                "taste_profile": ["辣", "重口"],
                "price_range": "10-15元",
                "meal_times": ["早餐", "午餐", "晚餐"],
                "description": "重庆特色麻辣面条",
                "popularity": 78,
                "tags": ["重庆特色", "麻辣"]
            },
            {
                "id": 8,
                "name": "番茄鸡蛋面",
                "category": "面食",
                "taste_profile": ["不辣", "清淡"],
                "price_range": "10-15元",
                "meal_times": ["早餐", "午餐", "晚餐"],
                "description": "酸甜开胃的家常面",
                "popularity": 70,
                "tags": ["家常", "开胃"]
            },
            {
                "id": 9,
                "name": "刀削面",
                "category": "面食",
                "taste_profile": ["不辣", "重口"],
                "price_range": "12-18元",
                "meal_times": ["午餐", "晚餐"],
                "description": "山西特色手工面",
                "popularity": 68,
                "tags": ["山西特色", "手工"]
            },
            {
                "id": 10,
                "name": "热干面",
                "category": "面食",
                "taste_profile": ["重口"],
                "price_range": "8-12元",
                "meal_times": ["早餐", "午餐"],
                "description": "武汉特色芝麻酱面",
                "popularity": 72,
                "tags": ["武汉特色", "早餐首选"]
            },
            
            # ========== 小吃类 ==========
            {
                "id": 11,
                "name": "煎饼果子",
                "category": "小吃",
                "taste_profile": ["不辣", "重口"],
                "price_range": "6-10元",
                "meal_times": ["早餐"],
                "description": "天津特色早餐煎饼",
                "popularity": 82,
                "tags": ["天津特色", "早餐必备"]
            },
            {
                "id": 12,
                "name": "手抓饼",
                "category": "小吃",
                "taste_profile": ["不辣"],
                "price_range": "5-8元",
                "meal_times": ["早餐", "夜宵"],
                "description": "酥脆可口的台湾手抓饼",
                "popularity": 75,
                "tags": ["台湾特色", "酥脆"]
            },
            {
                "id": 13,
                "name": "烤冷面",
                "category": "小吃",
                "taste_profile": ["不辣", "重口"],
                "price_range": "6-10元",
                "meal_times": ["夜宵"],
                "description": "东北特色烤冷面",
                "popularity": 70,
                "tags": ["东北特色", "夜宵"]
            },
            {
                "id": 14,
                "name": "炸鸡",
                "category": "小吃",
                "taste_profile": ["不辣"],
                "price_range": "12-25元",
                "meal_times": ["午餐", "晚餐", "夜宵"],
                "description": "香脆多汁的炸鸡",
                "popularity": 80,
                "tags": ["热门", "夜宵首选"]
            },
            {
                "id": 15,
                "name": "鸡蛋灌饼",
                "category": "小吃",
                "taste_profile": ["不辣"],
                "price_range": "5-8元",
                "meal_times": ["早餐"],
                "description": "金黄酥脆的鸡蛋灌饼",
                "popularity": 68,
                "tags": ["早餐", "快速"]
            },
            
            # ========== 米饭类 ==========
            {
                "id": 16,
                "name": "咖喱饭",
                "category": "米饭",
                "taste_profile": ["重口"],
                "price_range": "15-22元",
                "meal_times": ["午餐", "晚餐"],
                "description": "日式咖喱配米饭",
                "popularity": 72,
                "tags": ["日式", "浓郁"]
            },
            {
                "id": 17,
                "name": "韩式拌饭",
                "category": "米饭",
                "taste_profile": ["不辣", "重口"],
                "price_range": "18-25元",
                "meal_times": ["午餐", "晚餐"],
                "description": "韩式石锅拌饭",
                "popularity": 70,
                "tags": ["韩式", "营养均衡"]
            },
            {
                "id": 18,
                "name": "卤肉饭",
                "category": "米饭",
                "taste_profile": ["不辣", "重口"],
                "price_range": "12-18元",
                "meal_times": ["午餐", "晚餐"],
                "description": "台式卤肉饭",
                "popularity": 75,
                "tags": ["台式", "经典"]
            },
            {
                "id": 19,
                "name": "扬州炒饭",
                "category": "米饭",
                "taste_profile": ["不辣"],
                "price_range": "12-18元",
                "meal_times": ["午餐", "晚餐"],
                "description": "经典蛋炒饭",
                "popularity": 68,
                "tags": ["经典", "家常"]
            },
            {
                "id": 20,
                "name": "鱼香肉丝盖饭",
                "category": "米饭",
                "taste_profile": ["不辣", "重口"],
                "price_range": "15-20元",
                "meal_times": ["午餐", "晚餐"],
                "description": "经典川菜盖饭",
                "popularity": 72,
                "tags": ["川菜", "下饭"]
            },
            
            # ========== 火锅/串串 ==========
            {
                "id": 21,
                "name": "串串香",
                "category": "火锅",
                "taste_profile": ["辣", "重口"],
                "price_range": "25-40元",
                "meal_times": ["午餐", "晚餐", "夜宵"],
                "description": "成都特色串串火锅",
                "popularity": 82,
                "tags": ["成都特色", "聚会首选"]
            },
            {
                "id": 22,
                "name": "麻辣香锅",
                "category": "火锅",
                "taste_profile": ["辣", "重口"],
                "price_range": "25-40元",
                "meal_times": ["午餐", "晚餐"],
                "description": "自选配菜的麻辣香锅",
                "popularity": 78,
                "tags": ["自选", "重口味"]
            },
            {
                "id": 23,
                "name": "小火锅",
                "category": "火锅",
                "taste_profile": ["随意"],
                "price_range": "20-35元",
                "meal_times": ["午餐", "晚餐"],
                "description": "一人份小火锅",
                "popularity": 75,
                "tags": ["一人食", "自选"]
            },
            {
                "id": 24,
                "name": "酸菜鱼",
                "category": "火锅",
                "taste_profile": ["辣", "重口"],
                "price_range": "30-50元",
                "meal_times": ["午餐", "晚餐"],
                "description": "酸辣开胃的酸菜鱼",
                "popularity": 76,
                "tags": ["酸辣", "开胃"]
            },
            {
                "id": 25,
                "name": "水煮肉片",
                "category": "火锅",
                "taste_profile": ["辣", "重口"],
                "price_range": "25-35元",
                "meal_times": ["午餐", "晚餐"],
                "description": "麻辣鲜香的川菜",
                "popularity": 74,
                "tags": ["川菜", "下饭"]
            },
            
            # ========== 烧烤类 ==========
            {
                "id": 26,
                "name": "烤肉拌饭",
                "category": "烧烤",
                "taste_profile": ["重口"],
                "price_range": "18-25元",
                "meal_times": ["午餐", "晚餐"],
                "description": "韩式烤肉拌饭",
                "popularity": 72,
                "tags": ["韩式", "肉食"]
            },
            {
                "id": 27,
                "name": "烤串",
                "category": "烧烤",
                "taste_profile": ["重口", "辣"],
                "price_range": "20-40元",
                "meal_times": ["夜宵"],
                "description": "炭火烤串",
                "popularity": 85,
                "tags": ["夜宵首选", "聚会"]
            },
            {
                "id": 28,
                "name": "烤鱼",
                "category": "烧烤",
                "taste_profile": ["重口", "辣"],
                "price_range": "40-60元",
                "meal_times": ["晚餐"],
                "description": "万州烤鱼",
                "popularity": 70,
                "tags": ["聚会", "大餐"]
            },
            {
                "id": 29,
                "name": "铁板烧",
                "category": "烧烤",
                "taste_profile": ["重口"],
                "price_range": "20-35元",
                "meal_times": ["午餐", "晚餐"],
                "description": "铁板煎烤",
                "popularity": 65,
                "tags": ["现做", "香气"]
            },
            {
                "id": 30,
                "name": "章鱼小丸子",
                "category": "烧烤",
                "taste_profile": ["不辣"],
                "price_range": "8-12元",
                "meal_times": ["夜宵"],
                "description": "日式章鱼烧",
                "popularity": 68,
                "tags": ["日式", "小吃"]
            },
            
            # ========== 饺子/包子类 ==========
            {
                "id": 31,
                "name": "水饺",
                "category": "面点",
                "taste_profile": ["不辣"],
                "price_range": "12-20元",
                "meal_times": ["早餐", "午餐", "晚餐"],
                "description": "手工水饺",
                "popularity": 75,
                "tags": ["经典", "家常"]
            },
            {
                "id": 32,
                "name": "馄饨",
                "category": "面点",
                "taste_profile": ["不辣", "清淡"],
                "price_range": "10-15元",
                "meal_times": ["早餐", "午餐", "晚餐"],
                "description": "皮薄馅大的馄饨",
                "popularity": 70,
                "tags": ["清淡", "养胃"]
            },
            {
                "id": 33,
                "name": "小笼包",
                "category": "面点",
                "taste_profile": ["不辣"],
                "price_range": "10-18元",
                "meal_times": ["早餐", "午餐"],
                "description": "汤汁丰富的小笼包",
                "popularity": 78,
                "tags": ["上海特色", "汁多"]
            },
            {
                "id": 34,
                "name": "肉夹馍",
                "category": "面点",
                "taste_profile": ["不辣", "重口"],
                "price_range": "8-12元",
                "meal_times": ["早餐", "午餐"],
                "description": "陕西特色肉夹馍",
                "popularity": 76,
                "tags": ["陕西特色", "管饱"]
            },
            {
                "id": 35,
                "name": "韭菜盒子",
                "category": "面点",
                "taste_profile": ["不辣"],
                "price_range": "5-8元",
                "meal_times": ["早餐", "午餐"],
                "description": "韭菜鸡蛋馅饼",
                "popularity": 65,
                "tags": ["家常", "早餐"]
            },
            
            # ========== 饮品类 ==========
            {
                "id": 36,
                "name": "珍珠奶茶",
                "category": "饮品",
                "taste_profile": ["不辣"],
                "price_range": "8-15元",
                "meal_times": ["下午茶", "夜宵"],
                "description": "经典珍珠奶茶",
                "popularity": 88,
                "tags": ["热门", "解馋"]
            },
            {
                "id": 37,
                "name": "柠檬水",
                "category": "饮品",
                "taste_profile": ["清淡"],
                "price_range": "5-10元",
                "meal_times": ["下午茶"],
                "description": "清爽柠檬水",
                "popularity": 72,
                "tags": ["清爽", "解暑"]
            },
            {
                "id": 38,
                "name": "鲜榨果汁",
                "category": "饮品",
                "taste_profile": ["清淡"],
                "price_range": "10-20元",
                "meal_times": ["下午茶"],
                "description": "新鲜水果榨汁",
                "popularity": 68,
                "tags": ["健康", "维生素"]
            },
            {
                "id": 39,
                "name": "冰美式",
                "category": "饮品",
                "taste_profile": ["清淡"],
                "price_range": "12-18元",
                "meal_times": ["早餐", "下午茶"],
                "description": "冰美式咖啡",
                "popularity": 75,
                "tags": ["提神", "低卡"]
            },
            {
                "id": 40,
                "name": "酸奶",
                "category": "饮品",
                "taste_profile": ["清淡"],
                "price_range": "5-10元",
                "meal_times": ["下午茶", "夜宵"],
                "description": "酸甜开胃的酸奶",
                "popularity": 70,
                "tags": ["健康", "助消化"]
            },
            
            # ========== 沙拉/轻食类 ==========
            {
                "id": 41,
                "name": "鸡胸肉沙拉",
                "category": "轻食",
                "taste_profile": ["清淡"],
                "price_range": "18-28元",
                "meal_times": ["午餐", "晚餐"],
                "description": "低脂高蛋白的健身餐",
                "popularity": 72,
                "tags": ["健身", "低脂"]
            },
            {
                "id": 42,
                "name": "蔬菜沙拉",
                "category": "轻食",
                "taste_profile": ["清淡"],
                "price_range": "15-25元",
                "meal_times": ["午餐", "晚餐"],
                "description": "新鲜蔬菜沙拉",
                "popularity": 65,
                "tags": ["健康", "低卡"]
            },
            {
                "id": 43,
                "name": "三明治",
                "category": "轻食",
                "taste_profile": ["清淡", "不辣"],
                "price_range": "12-20元",
                "meal_times": ["早餐", "午餐"],
                "description": "经典三明治",
                "popularity": 70,
                "tags": ["快捷", "方便"]
            },
            {
                "id": 44,
                "name": "全麦面包+牛奶",
                "category": "轻食",
                "taste_profile": ["清淡"],
                "price_range": "8-15元",
                "meal_times": ["早餐"],
                "description": "健康早餐组合",
                "popularity": 60,
                "tags": ["健康", "快速"]
            },
            {
                "id": 45,
                "name": "减脂餐",
                "category": "轻食",
                "taste_profile": ["清淡"],
                "price_range": "20-35元",
                "meal_times": ["午餐", "晚餐"],
                "description": "专业减脂餐",
                "popularity": 68,
                "tags": ["健身", "营养均衡"]
            },
            
            # ========== 甜品类 ==========
            {
                "id": 46,
                "name": "冰淇淋",
                "category": "甜品",
                "taste_profile": ["清淡"],
                "price_range": "5-20元",
                "meal_times": ["下午茶", "夜宵"],
                "description": "各种口味冰淇淋",
                "popularity": 78,
                "tags": ["解暑", "甜蜜"]
            },
            {
                "id": 47,
                "name": "蛋糕",
                "category": "甜品",
                "taste_profile": ["清淡"],
                "price_range": "15-40元",
                "meal_times": ["下午茶"],
                "description": "各式蛋糕",
                "popularity": 75,
                "tags": ["庆祝", "甜蜜"]
            },
            {
                "id": 48,
                "name": "水果捞",
                "category": "甜品",
                "taste_profile": ["清淡"],
                "price_range": "12-25元",
                "meal_times": ["下午茶", "夜宵"],
                "description": "新鲜水果配酸奶",
                "popularity": 72,
                "tags": ["健康", "清爽"]
            },
            {
                "id": 49,
                "name": "双皮奶",
                "category": "甜品",
                "taste_profile": ["清淡"],
                "price_range": "8-15元",
                "meal_times": ["下午茶", "夜宵"],
                "description": "顺德特色双皮奶",
                "popularity": 68,
                "tags": ["顺德特色", "嫩滑"]
            },
            {
                "id": 50,
                "name": "红豆沙",
                "category": "甜品",
                "taste_profile": ["清淡"],
                "price_range": "6-10元",
                "meal_times": ["下午茶", "夜宵"],
                "description": "香甜红豆沙",
                "popularity": 62,
                "tags": ["暖胃", "养颜"]
            },
            
            # ========== 粥品类 ==========
            {
                "id": 51,
                "name": "皮蛋瘦肉粥",
                "category": "粥品",
                "taste_profile": ["清淡"],
                "price_range": "8-12元",
                "meal_times": ["早餐", "夜宵"],
                "description": "经典广式粥品",
                "popularity": 72,
                "tags": ["广式", "养胃"]
            },
            {
                "id": 52,
                "name": "小米粥",
                "category": "粥品",
                "taste_profile": ["清淡"],
                "price_range": "5-8元",
                "meal_times": ["早餐"],
                "description": "养胃小米粥",
                "popularity": 65,
                "tags": ["养胃", "健康"]
            },
            {
                "id": 53,
                "name": "八宝粥",
                "category": "粥品",
                "taste_profile": ["清淡"],
                "price_range": "6-10元",
                "meal_times": ["早餐"],
                "description": "营养八宝粥",
                "popularity": 60,
                "tags": ["营养", "暖胃"]
            },
            {
                "id": 54,
                "name": "南瓜粥",
                "category": "粥品",
                "taste_profile": ["清淡"],
                "price_range": "5-8元",
                "meal_times": ["早餐"],
                "description": "香甜南瓜粥",
                "popularity": 58,
                "tags": ["健康", "养颜"]
            },
            {
                "id": 55,
                "name": "生滚鱼片粥",
                "category": "粥品",
                "taste_profile": ["清淡"],
                "price_range": "12-18元",
                "meal_times": ["早餐", "夜宵"],
                "description": "鲜嫩鱼片粥",
                "popularity": 68,
                "tags": ["广式", "鲜美"]
            },
            
            # ========== 外卖快餐 ==========
            {
                "id": 56,
                "name": "汉堡",
                "category": "快餐",
                "taste_profile": ["不辣"],
                "price_range": "15-30元",
                "meal_times": ["午餐", "晚餐", "夜宵"],
                "description": "经典汉堡",
                "popularity": 78,
                "tags": ["西式", "快捷"]
            },
            {
                "id": 57,
                "name": "披萨",
                "category": "快餐",
                "taste_profile": ["不辣"],
                "price_range": "25-50元",
                "meal_times": ["午餐", "晚餐"],
                "description": "意式披萨",
                "popularity": 75,
                "tags": ["西式", "分享"]
            },
            {
                "id": 58,
                "name": "意面",
                "category": "快餐",
                "taste_profile": ["不辣"],
                "price_range": "18-30元",
                "meal_times": ["午餐", "晚餐"],
                "description": "意大利面",
                "popularity": 70,
                "tags": ["西式", "经典"]
            },
            {
                "id": 59,
                "name": "寿司",
                "category": "快餐",
                "taste_profile": ["清淡"],
                "price_range": "20-40元",
                "meal_times": ["午餐", "晚餐"],
                "description": "日式寿司",
                "popularity": 72,
                "tags": ["日式", "精致"]
            },
            {
                "id": 60,
                "name": "紫菜包饭",
                "category": "快餐",
                "taste_profile": ["清淡"],
                "price_range": "12-20元",
                "meal_times": ["午餐", "晚餐"],
                "description": "韩式紫菜包饭",
                "popularity": 68,
                "tags": ["韩式", "方便"]
            },
            
            # ========== 夜宵特色 ==========
            {
                "id": 61,
                "name": "小龙虾",
                "category": "夜宵",
                "taste_profile": ["辣", "重口"],
                "price_range": "40-80元",
                "meal_times": ["夜宵"],
                "description": "麻辣小龙虾",
                "popularity": 82,
                "tags": ["夜宵爆款", "聚会"]
            },
            {
                "id": 62,
                "name": "田螺",
                "category": "夜宵",
                "taste_profile": ["辣", "重口"],
                "price_range": "15-25元",
                "meal_times": ["夜宵"],
                "description": "炒田螺",
                "popularity": 65,
                "tags": ["夜宵", "下酒"]
            },
            {
                "id": 63,
                "name": "炒粉/炒河粉",
                "category": "夜宵",
                "taste_profile": ["不辣", "重口"],
                "price_range": "10-15元",
                "meal_times": ["夜宵"],
                "description": "干炒牛河等",
                "popularity": 72,
                "tags": ["快速", "便宜"]
            },
            {
                "id": 64,
                "name": "卤味",
                "category": "夜宵",
                "taste_profile": ["重口"],
                "price_range": "15-30元",
                "meal_times": ["夜宵"],
                "description": "各种卤味拼盘",
                "popularity": 75,
                "tags": ["下酒", "分享"]
            },
            {
                "id": 65,
                "name": "烧烤+啤酒",
                "category": "夜宵",
                "taste_profile": ["重口"],
                "price_range": "30-60元",
                "meal_times": ["夜宵"],
                "description": "经典夜宵组合",
                "popularity": 88,
                "tags": ["经典组合", "聚会"]
            },
            
            # ========== 地方特色 ==========
            {
                "id": 66,
                "name": "螺蛳粉",
                "category": "地方特色",
                "taste_profile": ["辣", "重口"],
                "price_range": "12-20元",
                "meal_times": ["午餐", "晚餐", "夜宵"],
                "description": "柳州特色螺蛳粉",
                "popularity": 80,
                "tags": ["柳州特色", "酸辣"]
            },
            {
                "id": 67,
                "name": "臭豆腐",
                "category": "地方特色",
                "taste_profile": ["重口"],
                "price_range": "8-15元",
                "meal_times": ["夜宵"],
                "description": "长沙臭豆腐",
                "popularity": 72,
                "tags": ["长沙特色", "闻着臭吃着香"]
            },
            {
                "id": 68,
                "name": "凉皮",
                "category": "地方特色",
                "taste_profile": ["不辣", "辣"],
                "price_range": "8-12元",
                "meal_times": ["午餐", "晚餐"],
                "description": "陕西凉皮",
                "popularity": 75,
                "tags": ["陕西特色", "爽口"]
            },
            {
                "id": 69,
                "name": "羊肉泡馍",
                "category": "地方特色",
                "taste_profile": ["不辣"],
                "price_range": "18-25元",
                "meal_times": ["午餐", "晚餐"],
                "description": "陕西羊肉泡馍",
                "popularity": 70,
                "tags": ["陕西特色", "暖身"]
            },
            {
                "id": 70,
                "name": "酸辣粉",
                "category": "地方特色",
                "taste_profile": ["辣", "重口"],
                "price_range": "8-12元",
                "meal_times": ["午餐", "晚餐", "夜宵"],
                "description": "重庆酸辣粉",
                "popularity": 78,
                "tags": ["重庆特色", "酸辣"]
            },
            
            # ========== 健康/养生 ==========
            {
                "id": 71,
                "name": "蒸蛋",
                "category": "健康餐",
                "taste_profile": ["清淡"],
                "price_range": "8-12元",
                "meal_times": ["早餐", "午餐", "晚餐"],
                "description": "嫩滑蒸蛋",
                "popularity": 65,
                "tags": ["清淡", "养胃"]
            },
            {
                "id": 72,
                "name": "白切鸡",
                "category": "健康餐",
                "taste_profile": ["清淡"],
                "price_range": "18-25元",
                "meal_times": ["午餐", "晚餐"],
                "description": "广东白切鸡",
                "popularity": 70,
                "tags": ["广式", "原汁原味"]
            },
            {
                "id": 73,
                "name": "清蒸鱼",
                "category": "健康餐",
                "taste_profile": ["清淡"],
                "price_range": "25-40元",
                "meal_times": ["午餐", "晚餐"],
                "description": "清蒸鲈鱼等",
                "popularity": 68,
                "tags": ["健康", "高蛋白"]
            },
            {
                "id": 74,
                "name": "蒸蔬菜",
                "category": "健康餐",
                "taste_profile": ["清淡"],
                "price_range": "12-18元",
                "meal_times": ["午餐", "晚餐"],
                "description": "清蒸时蔬",
                "popularity": 55,
                "tags": ["健康", "低卡"]
            },
            {
                "id": 75,
                "name": "杂粮饭",
                "category": "健康餐",
                "taste_profile": ["清淡"],
                "price_range": "10-15元",
                "meal_times": ["午餐", "晚餐"],
                "description": "五谷杂粮饭",
                "popularity": 58,
                "tags": ["健康", "高纤维"]
            },
        ]
    
    def save_database(self):
        """保存数据库到文件"""
        data = {
            "last_updated": datetime.now().isoformat(),
            "foods": self._database
        }
        
        # 确保目录存在
        self.data_dir.mkdir(exist_ok=True)
        
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        self._last_update = datetime.now()
        logger.info("saved_food_database count=%d", len(self._database))
    
    def should_update(self) -> bool:
        """检查是否需要更新数据库"""
        if not self._last_update:
            return True
            
        days_since_update = (datetime.now() - self._last_update).days
        return days_since_update >= 7


# 全局实例
_food_manager: Optional[FoodDataManager] = None


def get_food_manager() -> FoodDataManager:
    """获取食物数据管理器单例"""
    global _food_manager
    if _food_manager is None:
        _food_manager = FoodDataManager()
    return _food_manager
