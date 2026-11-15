import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")

# 1. 初始化官方 SDK 客户端
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com/v1" 
)

def ask_deepseek(messages):
    """非流式对话（原来用 requests 写的）"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"请求失败: {e}")
        return None

def ask_deepseek_stream(messages):
    """流式对话（原来用 requests 写的）"""
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True
        )
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
    except Exception as e:
        yield f"\n[流式请求失败: {e}]"