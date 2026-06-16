"""食物数据爬虫模块 - 从公开数据源获取食物信息"""

import json
import time
import random
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from .logging_config import get_logger

logger = get_logger(__name__)


class FoodCrawler:
    """食物数据爬虫"""
    
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            # 使用当前文件所在目录的父目录下的data文件夹
            data_dir = Path(__file__).parent.parent / "data"
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "food_database.json"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }
    
    def crawl_food_rankings(self, city: str = "北京") -> List[Dict]:
        """爬取美食排行榜数据
        
        Args:
            city: 城市名称
            
        Returns:
            食物数据列表
        """
        foods = []
        
        try:
            # 尝试从多个数据源获取
            foods.extend(self._crawl_meishijian(city))
            time.sleep(random.uniform(1, 2))
            
            foods.extend(self._crawl_dianping(city))
            time.sleep(random.uniform(1, 2))
            
        except Exception as e:
            logger.error("crawl_food_rankings_failed city=%s error=%s", city, e)
        
        # 去重
        seen_names = set()
        unique_foods = []
        for food in foods:
            if food["name"] not in seen_names:
                seen_names.add(food["name"])
                unique_foods.append(food)
        
        logger.info("crawled_foods city=%s count=%d", city, len(unique_foods))
        return unique_foods
    
    def _crawl_meishijian(self, city: str) -> List[Dict]:
        """从美食杰爬取数据"""
        foods = []
        
        try:
            # 美食杰热门菜品页面
            url = "https://home.meishij.net/yule/"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # 解析美食列表
            items = soup.find_all("div", class_="list_item") or soup.find_all("li")
            
            for item in items[:20]:
                try:
                    name_tag = item.find("a") or item.find("h3") or item.find("span")
                    if name_tag:
                        name = name_tag.get_text(strip=True)
                        if name and len(name) < 20:
                            foods.append({
                                "id": len(foods) + 1000,
                                "name": name,
                                "category": "家常菜",
                                "taste_profile": ["不辣"],
                                "price_range": "15-25元",
                                "meal_times": ["午餐", "晚餐"],
                                "description": f"热门家常菜：{name}",
                                "popularity": 60 + random.randint(0, 20),
                                "tags": ["热门", "家常"],
                                "source": "meishijian"
                            })
                except Exception:
                    continue
            
        except Exception as e:
            logger.error("crawl_meishijian_failed city=%s error=%s", city, e)
        
        return foods
    
    def _crawl_dianping(self, city: str) -> List[Dict]:
        """从大众点评爬取数据（模拟）"""
        foods = []
        
        try:
            # 大众点评有严格反爬，这里只做模拟
            # 实际使用时需要更复杂的反爬策略
            
            # 模拟一些常见菜品
            mock_foods = [
                {"name": "烤鸭", "category": "北京菜", "price": "68-128元"},
                {"name": "炸酱面", "category": "面食", "price": "12-18元"},
                {"name": "豆汁焦圈", "category": "小吃", "price": "8-12元"},
                {"name": "卤煮火烧", "category": "小吃", "price": "18-25元"},
                {"name": "爆肚", "category": "小吃", "price": "15-22元"},
            ]
            
            for item in mock_foods:
                foods.append({
                    "id": len(foods) + 2000,
                    "name": item["name"],
                    "category": item["category"],
                    "taste_profile": ["不辣", "重口"],
                    "price_range": item["price"],
                    "meal_times": ["午餐", "晚餐"],
                    "description": f"北京特色：{item['name']}",
                    "popularity": 65 + random.randint(0, 15),
                    "tags": ["地方特色", city],
                    "source": "dianping_mock"
                })
                
        except Exception as e:
            logger.error("crawl_dianping_failed city=%s error=%s", city, e)
        
        return foods
    
    def update_database(self, new_foods: List[Dict]) -> Dict:
        """更新本地数据库
        
        Args:
            new_foods: 新的食物数据
            
        Returns:
            更新结果统计
        """
        stats = {"added": 0, "updated": 0, "skipped": 0}
        
        try:
            # 加载现有数据库
            existing_foods = []
            if self.db_path.exists():
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    existing_foods = data.get("foods", [])
            
            # 创建现有食物的索引（按名称）
            existing_index = {food["name"]: i for i, food in enumerate(existing_foods)}
            
            # 添加新食物
            for food in new_foods:
                name = food["name"]
                if name in existing_index:
                    # 已存在，更新热度
                    idx = existing_index[name]
                    existing_foods[idx]["popularity"] = max(
                        existing_foods[idx].get("popularity", 0),
                        food.get("popularity", 0)
                    )
                    stats["updated"] += 1
                else:
                    # 新食物，添加
                    food["id"] = len(existing_foods) + 1
                    existing_foods.append(food)
                    stats["added"] += 1
            
            # 保存数据库
            self.data_dir.mkdir(exist_ok=True)
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump({
                    "last_updated": datetime.now().isoformat(),
                    "foods": existing_foods
                }, f, ensure_ascii=False, indent=2)
            
            logger.info(
                "database_updated added=%d updated=%d total=%d",
                stats["added"], stats["updated"], len(existing_foods)
            )
            
        except Exception as e:
            logger.error("update_database_failed error=%s", e)
            stats["error"] = str(e)
        
        return stats


def run_crawler(city: str = "北京") -> Dict:
    """运行爬虫并更新数据库
    
    Args:
        city: 城市名称
        
    Returns:
        运行结果
    """
    logger.info("starting_crawler city=%s", city)
    
    crawler = FoodCrawler()
    
    # 爬取数据
    new_foods = crawler.crawl_food_rankings(city)
    
    if not new_foods:
        return {
            "success": True,
            "message": "没有获取到新数据",
            "stats": {"added": 0, "updated": 0, "skipped": 0}
        }
    
    # 更新数据库
    stats = crawler.update_database(new_foods)
    
    return {
        "success": True,
        "message": f"爬取完成，新增 {stats['added']} 个食物，更新 {stats['updated']} 个",
        "stats": stats
    }


if __name__ == "__main__":
    # 直接运行爬虫
    result = run_crawler()
    print(json.dumps(result, ensure_ascii=False, indent=2))
