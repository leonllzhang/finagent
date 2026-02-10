import os
import sys

# 【核心修复】强制抹除所有可能的代理环境变量
for key in list(os.environ.keys()):
    if 'proxy' in key.lower():
        del os.environ[key]

# 额外强制设置为空
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''
os.environ['all_proxy'] = ''

import akshare as ak
import requests # 增加一个最基础的请求测试
from langchain_openai import ChatOpenAI

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import efinance as ef

def test_system():
    print("=== 开始系统自检 (强力脱敏版) ===")

    # 0. 测试最基础的连接
    print("\n[0/3] 测试基础网络连通性 (baidu)...")
    try:
        r = requests.get("https://www.baidu.com", timeout=5)
        print(f"✅ 基础网络正常！状态码: {r.status_code}")
    except Exception as e:
        print(f"❌ 基础网络不通: {e}")

    # 1. 测试 AkShare
    print("\n[1/3] 测试 AkShare 数据获取...")
    try:
        # 换一个更基础的接口试试
        df = ak.stock_zh_a_spot_em() 
        if not df.empty:
            print(f"✅ AkShare 正常！成功获取到股票数据快照。")
        else:
            print("❌ AkShare 获取的数据为空。")
    except Exception as e:
        print(f"❌ AkShare 报错: {e}")

    # 2. 测试 Qwen API
    print("\n[2/3] 测试 Qwen API 连接...")
    # !!! 请在这里填入你的真实 KEY，不要带空格 !!!
    MY_QWEN_KEY = "sk-xxxxxxxxxxxxxxxx" 
    
    if "xxxx" in MY_QWEN_KEY:
        print("⚠️ 跳过 API 测试：请先在脚本中填入真实的 API Key。")
    else:
        try:
            llm = ChatOpenAI(
                model="qwen-max",
                api_key=MY_QWEN_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                timeout=10
            )
            res = llm.invoke("你好")
            print(f"✅ Qwen API 正常！AI回复: {res.content}")
        except Exception as e:
            print(f"❌ Qwen API 报错: {e}")

def test_interfaces():
    print("--- 尝试接口 1: 东方财富 ---")
    try:
        df1 = ak.stock_zh_a_spot_em()
        print(f"✅ 东方财富成功，数据量: {len(df1)}")
    except Exception as e:
        print(f"❌ 东方财富失败: {e}")

    print("\n--- 尝试接口 2: 新浪财经 ---")
    try:
        # 这个接口通常返回 A 股实时行情
        df2 = ak.stock_zh_a_s_spot_em() 
        print(f"✅ 新浪财经成功，数据量: {len(df2)}")
    except Exception as e:
        print(f"❌ 新浪财经失败: {e}")

    print("\n--- 尝试接口 3: 公募基金/ETF (我们项目需要的) ---")
    try:
        df3 = ak.fund_etf_spot_em()
        print(f"✅ ETF 接口成功，数据量: {len(df3)}")
    except Exception as e:
        print(f"❌ ETF 接口失败: {e}")
    
    try:
        # 测试efinance 接口
        df = ef.stock.get_quote_history('510300', klt=5)
        print(df)
        print(f"✅ ETF 接口成功，数据量: {len(df)}")
    except Exception as e:
        print(f"❌ efinance 接口失败: {e}")



if __name__ == "__main__":
    test_system()
    test_interfaces()
    # 获取 510300 的实时价格
    # print(f"测试efinance接口")
