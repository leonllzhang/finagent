import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    #tushare 的token
    TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")
    # Qwen API 配置
    API_KEY = os.getenv("QWEN_API_KEY")
    BASE_URL = os.getenv("QWEN_BASE_URL")
    MODEL_NAME = "qwen-max"
    
    # 监控配置
    # 510300(沪深300ETF), 513100(纳指ETF), 159941(恒生科技ETF)
    MONITOR_SYMBOLS = ["510300.SH", "510880.SH", "159941.SZ"] 
    INTERVAL_SECONDS = 300  # 5分钟轮询一次
    K_LINE_PERIOD = 5       # 使用5分钟K线