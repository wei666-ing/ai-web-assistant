import os
import requests
import chromadb
from dotenv import load_dotenv

load_dotenv()
bailian_key = os.getenv("BAILIAN_API_KEY")
deepseek_key = os.getenv("DEEPSEEK_API_KEY")

def get_embedding(text):
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
    headers = {"Authorization": f"Bearer {bailian_key}", "Content-Type": "application/json"}
    data = {"model": "text-embedding-v3", "input": text}
    resp = requests.post(url, headers=headers, json=data)
    return resp.json()["data"][0]["embedding"]

def ask_deepseek_with_context(question, context):
    """把检索到的资料和问题一起发给大模型"""
    url = "https://api.deepseek.com/chat/completions"
    headers = {"Authorization": f"Bearer {deepseek_key}", "Content-Type": "application/json"}
    
    # 构建提示词（Prompt）这是 RAG 的灵魂
    prompt = f"""请根据以下参考资料回答用户的问题。如果参考资料中没有相关信息，请直接回答“我不知道”。
    
参考资料：
{context}

用户问题：{question}"""

    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}]
    }
    resp = requests.post(url, headers=headers, json=data)
    return resp.json()["choices"][0]["message"]["content"]

def main():
    question = input("👤 请输入你的问题: ")
    
    # 1. 把问题变成向量
    q_vector = get_embedding(question)
    
    # 2. 去 ChromaDB 里找最相似的文本
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_collection(name="my_knowledge")
    
    # query 方法：传入问题向量，获取最相似的 1 个结果（n_results=1）
    results = collection.query(query_embeddings=[q_vector], n_results=1)
    
    # 提取检索到的文本片段
    context = results["documents"][0][0]
    print(f"🔍 检索到的相关参考资料: {context}")
    
    # 3. 交给大模型生成回答
    print("🤖 AI 正在思考...\n")
    answer = ask_deepseek_with_context(question, context)
    
    print(f"💡 AI 的回答:\n{answer}")

if __name__ == "__main__":
    main()