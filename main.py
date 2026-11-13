from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File
from pypdf import PdfReader
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from ai_client import ask_deepseek, ask_deepseek_stream 
import sqlite3
import requests
import chromadb
import io
import os
from dotenv import load_dotenv

load_dotenv()
bailian_key = os.getenv("BAILIAN_API_KEY")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI()

# 把 static 目录挂到 /static，前端就能用本地文件，不再依赖外网 CDN
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

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
    collection = client.get_or_create_collection(name="my_knowledge")
    results = collection.query(query_embeddings=[q_vector], n_results=1)
    
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
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # 1. 读取上传的文件内容
        content = await file.read()
        text = ""
        
        # 2. 解析文本：判断是 PDF 还是 TXT
        if file.filename.endswith(".pdf"):
            # 如果是 PDF，用 pypdf 提取文字
            reader = PdfReader(io.BytesIO(content))
            for page in reader.pages:
                text += page.extract_text() + "\n"
        else:
            # 如果是 TXT，直接解码
            text = content.decode("utf-8")
            
        if not text.strip():
            return {"success": False, "error": "文件内容为空或无法解析"}

        # 3. 将文本按句号切分成小块
        chunks = [chunk.strip() for chunk in text.split("。") if chunk.strip()]
        
        # 4. 向量化并存入 ChromaDB
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_or_create_collection(name="my_knowledge")
        
        # 为了让每次上传的 ID 不重复，用文件名+时间戳
        import time
        base_id = f"{file.filename}_{int(time.time())}"
        
        for i, chunk in enumerate(chunks):
            # 调用咱们在 main.py 里写好的 get_embedding 函数
            vector = get_embedding(chunk)
            if vector:
                collection.add(
                    ids=[f"{base_id}_{i}"],
                    documents=[chunk],
                    embeddings=[vector]
                )
                
        return {"success": True, "message": f"成功解析并收录 {len(chunks)} 条文本片段"}

    except Exception as e:
        print("解析文件出错:", e)
        return {"success": False, "error": str(e)}