import os
import requests
from dotenv import load_dotenv

load_dotenv()
bailian_key = os.getenv("BAILIAN_API_KEY")

def get_embedding(text):
    """把文字发给百炼，拿回向量数组"""
    # 注意：百炼的兼容 OpenAI 格式的接口地址
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {bailian_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "text-embedding-v3", # 如果报错没有这个模型，就换成 text-embedding-v2
        "input": text
    }
    
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code == 200:
        result = resp.json()
        # 提取向量数组
        return result["data"][0]["embedding"]
    else:
        print("请求失败:", resp.status_code, resp.text)
        return None

if __name__ == "__main__":
    text = "人工智能是一门极其有前景的学科。"
    print(f"正在将文本向量化: {text}")
    
    vector = get_embedding(text)
    if vector:
        print(f"成功获取向量！向量的长度是: {len(vector)}")
        # 打印前 5 个数字看看长啥样
        print("向量的前5个维度:", vector[:5])