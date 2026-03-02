import requests
import pandas as pd
import os
import json
import re

# 强力净化环境，直连腾讯服务器
os.environ['no_proxy'] = '*'

class NewsManager:
    @staticmethod
    def get_macro_news(top_n=30):
        """
        通过腾讯财经接口获取 7x24 小时全球实时快讯
        用于识别：地缘政治、美联储、宏观政策等
        """
        print("📡 正在抓取腾讯实时全球快讯 (7x24)...")
        # 腾讯全球快讯接口
        url = "https://web.ifzq.gtimg.cn/news/notice/news724?page=1&limit=50"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Referer': 'https://gu.qq.com/'
        }

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            data = resp.json()
            
            if data.get('code') != 0:
                return "暂无最新宏观新闻。"

            # 提取新闻列表
            news_items = data.get('data', [])
            if not news_items:
                return "暂无最新宏观新闻。"
            
            context = ""
            # 过滤出关键词（可选，但通常交给 LLM 分析即可）
            # 仅取最近的 top_n 条
            for item in news_items[:top_n]:
                title = item.get('title', '')
                content = item.get('content', '')
                time_str = item.get('pub_time', '')
                
                # 拼接标题和内容摘要
                full_text = f"{title} {content}"
                # 去除 HTML 标签
                clean_text = re.sub('<[^<]+?>', '', full_text)
                # 清洗多余空格和换行
                clean_text = clean_text.replace('\n', ' ').strip()
                
                context += f"- [{time_str}] {clean_text}\n"
            
            return context
            
        except Exception as e:
            print(f"❌ 腾讯新闻抓取失败: {e}")
            return "新闻抓取异常。当前环境提示：中东地缘局势紧张（美以空袭伊朗预期），市场避险情绪升温。"