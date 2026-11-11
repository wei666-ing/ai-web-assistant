import os
import requests
import chromadb
from dotenv import load_dotenv

load_dotenv()
bailian_key = os.getenv("BAILIAN_API_KEY")

def get_embedding(text):
    """把文字发给百炼，拿回向量数组"""
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {bailian_key}",
        "Content-Type": "application/json"
    }
    data = {"model": "text-embedding-v3", "input": text}
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code == 200:
        return resp.json()["data"][0]["embedding"]
    return None

def build_knowledge_base():
    # 1. 连接本地的 Chroma 向量数据库
    # 数据会保存在当前目录下的 chroma_db 文件夹里
    client = chromadb.PersistentClient(path="./chroma_db")
    
    # 2. 创建一个集合（类似于数据库的表），如果已存在则获取
    collection = client.get_or_create_collection(name="my_knowledge")
    
    # 3. 读取我们的文本文件
    with open("knowledge.txt", "r", encoding="utf-8") as f:
        content = f.read()
        
    # 4. 简单切分：我们按句号切分，把每句话作为一个独立的片段
    # （真实企业里会按字数或段落切分，这里为了简单）
    chunks = [chunk.strip() for chunk in content.split("。") if chunk.strip()]
    
    print(f"共读取到 {len(chunks)} 个文本片段，准备向量化入库...")
    
    # 5. 循环把每一段变成向量，并存入数据库
    for i, chunk in enumerate(chunks):
        vector = get_embedding(chunk)
        if vector:
            # add 方法：把 ID、文本内容、向量一起存进去
            collection.add(
                ids=[f"id_{i}"],
                documents=[chunk],
                embeddings=[vector]
            )
            print(f"成功入库片段 {i+1}: {chunk[:10]}...")
            
    print("🎉 知识库构建完成！")

if __name__ == "__main__":
    build_knowledge_base()