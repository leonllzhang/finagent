import os
from dotenv import load_dotenv

load_dotenv()

class StockConfig:
    API_KEY = os.getenv("QWEN_API_KEY")
    BASE_URL = os.getenv("QWEN_BASE_URL")
    MODEL_NAME = "qwen-max"
    
    # 监控列表：symbol 为个股，sector 为该股所属行业的 ETF 代码（用于对比强度）
    MONITOR_LIST = [
        {"symbol": "600031", "sector": "516750"}, # 三一重工 -> 工程机械ETF
        {"symbol": "000333", "sector": "159996"}, # 美的集团 -> 家电ETF
        {"symbol": "600023", "sector": "512670"}, # 浙能电力 -> 电力ETF
        {"symbol": "601229", "sector": "512800"}, # 上海银行 -> 银行ETF
        {"symbol": "000157", "sector": "516750"}, # 中联重科 -> 工程机械ETF
        {"symbol": "600066", "sector": "516110"}, # 宇通客车 -> 汽车ETF
        {"symbol": "003816", "sector": "512670"}, # 中国广核 -> 电力ETF
        {"symbol": "000538", "sector": "561500"}, # 云南白药 -> 中药ETF
        {"symbol": "000425", "sector": "516750"}, # 徐工机械 -> 工程机械ETF
        {"symbol": "601058", "sector": "516020"}, # 赛轮轮胎 -> 化工ETF
    ]
    
    INTERVAL_SECONDS = 300  # 5分钟轮询
    PUSH_THRESHOLD = 75     # AI 置信度超过 75% 触发手机推送