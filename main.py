import sqlite3
from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import FileResponse, StreamingResponse
from ai_client import ask_deepseek, ask_deepseek_stream

app = FastAPI()

class ChatRequest(BaseModel):
    messages: list

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
    with sqlite3.connect("chat_history.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO messages (role, content) VALUES (?, ?)", (role, content))
        conn.commit()
    return {"status": "ok"}

@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    return StreamingResponse(ask_deepseek_stream(request.messages), media_type="text/event-stream")

#新增：当用户访问根目录 （http://127/0.0.1：0000）时，返回index.html
@app.get("/")
def read_roat():
    return FileResponse("index.html")