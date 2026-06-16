"""日志配置 - 记录 Agent 运行链路和错误信息"""

import logging
import os
import threading
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.getenv("LOG_FILE", "agent.log")

_configured = False
_lock = threading.Lock()


def setup_logging() -> None:
    """初始化应用日志。"""
    global _configured
    if _configured:
        return
    
    with _lock:
        # 双重检查锁定
        if _configured:
            return
        
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = LOG_DIR / LOG_FILE

        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL, logging.INFO),
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_path, encoding="utf-8"),
            ],
        )
        _configured = True


def get_logger(name: str) -> logging.Logger:
    """获取项目日志器。"""
    setup_logging()
    return logging.getLogger(name)
