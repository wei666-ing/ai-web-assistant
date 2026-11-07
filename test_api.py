import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
url = "https://api.deepseek.com/chat/completions"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

data = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "user", "content": "用一句话解释什么是API"}
    ],
}

resp = requests.post(url, headers=headers, json=data, timeout=30)
print("状态码：", resp.status_code)

result = resp.json()
print("模型回复:", result["choices"][0]["message"]["content"])