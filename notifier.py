import requests
import json

class Notifier:
    @staticmethod
    def send_feishu(webhook_url, content):
        """飞书机器人推送"""
        if not webhook_url: return
        headers = {"Content-Type": "application/json"}
        data = {
            "msg_type": "text",
            "content": {
                "text": f"🔔 ETF 监控预警\n{content}"
            }
        }
        try:
            requests.post(webhook_url, json=data, timeout=10)
        except Exception as e:
            print(f"飞书推送失败: {e}")

    @staticmethod
    def send_bark(bark_key, title, content):
        """iOS Bark 推送 (手机端直接弹窗)"""
        if not bark_key: return
        url = f"https://api.day.app/{bark_key}/{title}/{content}"
        try:
            requests.get(url, timeout=10)
        except Exception as e:
            print(f"Bark 推送失败: {e}")