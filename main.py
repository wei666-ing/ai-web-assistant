from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import FileResponse, StreamingResponse
from ai_client import ask_deepseek, ask_deepseek_stream 
import sqlite3
import requests
import chromadb
import os
from dotenv import load_dotenv

load_dotenv()
bailian_key = os.getenv("BAILIAN_API_KEY")

app = FastAPI()

class ChatRequest(BaseModel):
    messages: list

# ================= 数据库（历史记录）相关 =================
def init_db():
    with sqlite3.connect('chat_history.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT,
                content TEXT
            )
        ''')
        conn.commit()
init_db()

@app.get("/history")
def get_history():
    with sqlite3.connect('chat_history.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT role, content FROM messages")
        rows = cursor.fetchall()
        return [{"role": row[0], "content": row[1]} for row in rows]

@app.post("/save_message")
def save_message(role: str, content: str):
    with sqlite3.connect('chat_history.db') as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
        conn.commit()
    return {"status": "ok"}


# ================= RAG（知识库）相关 =================
def get_embedding(text):
    """把文字发给百炼，拿回向量"""
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/embeddings"
    headers = {"Authorization": f"Bearer {bailian_key}", "Content-Type": "application/json"}
    data = {"model": "text-embedding-v3", "input": text}
    resp = requests.post(url, headers=headers, json=data)
    return resp.json()["data"][0]["embedding"]

@app.post("/chat/rag")
def chat_rag(request: ChatRequest):
    """RAG 问答接口（非流式，一次性返回）"""
    # 1. 获取用户最后一句提问
    question = request.messages[-1]["content"]
    
    # 2. 检索本地知识库
    q_vector = get_embedding(question)
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_collection(name="my_knowledge")
    # n_results=2 表示找最相近的 2 条资料
    results = collection.query(query_embeddings=[q_vector], n_results=2)
    
    # 把找出来的资料拼接成一段文字
    context = "\n".join(results["documents"][0])
    
    # 3. 拼装 Prompt（提示词）
    prompt = f"""请根据以下参考资料回答用户的问题。如果参考资料中没有相关信息，请直接回答“我不知道”。
    
参考资料：
{context}

用户问题：{question}"""

    # 4. 调用 DeepSeek
    reply = ask_deepseek([{"role": "user", "content": prompt}])
    
    return {"reply": reply}


# ================= 原有接口 =================
@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    return StreamingResponse(ask_deepseek_stream(request.messages), media_type="text/event-stream")

@app.get("/")
def read_root():
    return FileResponse("index.html")