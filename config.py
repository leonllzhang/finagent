import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv("QWEN_API_KEY")
    BASE_URL = os.getenv("QWEN_BASE_URL")

   
    MODEL_NAME = "qwen-max"