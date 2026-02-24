import os
from dotenv import load_dotenv
load_dotenv()

class WeeklyConfig:
    API_KEY = os.getenv("QWEN_API_KEY")
    BASE_URL = os.getenv("QWEN_BASE_URL")
    MODEL_NAME = "qwen-max"
    
    # 筛选参数
    TOP_N_FILTER = 30  # 初筛保留前30只进入AI分析
    DB_PATH = "weekly_market.db"