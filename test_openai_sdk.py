import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# 1. 初始化客户端
# 注意：我们这里调用的是 DeepSeek 官方的接口，所以 base_url 换成 DeepSeek 的。
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1" # 加了 /v1 兼容标准格式
)

# ==========================================
# 测试 1：普通对话（非流式）
# ==========================================
def test_normal():
    print("--- 正在测试普通对话 ---")
    completion = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": "用一句话介绍什么是Python"}
        ]
    )
    print("AI回复:", completion.choices[0].message.content)


# ==========================================
# 测试 2：流式对话（打字机效果）
# ==========================================
def test_stream():
    print("\n--- 正在测试流式对话 ---")
    # 只要加一个 stream=True，就变成了流式！
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": "请写一首关于春天的四句诗"}
        ],
        stream=True 
    )
    
    # 循环获取每一小块数据
    for chunk in response:
        # 拿到每块里真正的内容（可能为空，需要判断）
        content = chunk.choices[0].delta.content
        if content:
            print(content, end="", flush=True) # end="" 保证不换行，flush=True 保证立刻输出


if __name__ == "__main__":
    test_normal()
    test_stream()