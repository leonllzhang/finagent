import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("QWEN_API_KEY")
    BASE_URL = os.getenv("QWEN_BASE_URL")
    
    # 这里的模型名称根据阿里云官方文档填写：
    # Qwen3 发布后直接改为 "qwen3-72b-instruct" 等
    # 目前最强的是 "qwen-max" 或 "qwen-plus-latest"
    MODEL_NAME = "qwen-max"