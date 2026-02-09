from graph import create_graph

def main():
    agent = create_graph()
    
    print("--- 欢迎使用 ETF 实时分析 Agent ---")
    while True:
        symbol = input("\n请输入 ETF 代码 (如 510300) 或退出 (q): ")
        if symbol.lower() == 'q':
            break
            
        try:
            inputs = {"symbol": symbol}
            # 运行并流式输出结果
            for output in agent.stream(inputs):
                for node, state_update in output.items():
                    if node == "analyze":
                        print(f"\n[AI 分析报告]:\n{state_update['analysis']}")
        except Exception as e:
            print(f"发生错误: {e}")

if __name__ == "__main__":
    main()