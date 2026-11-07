from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import FileResponse 
from ai_client import ask_deepseek

app = FastAPI()

class ChatRequest(BaseModel):
    messages: list

@app.post("/chat")
def chat(request: ChatRequest):
    #把前端传来的单句 message 包装成 AI 需要的格式
    reply = ask_deepseek(request.messages)
    return{"reply": reply}

#新增：当用户访问根目录 （http://127/0.0.1：0000）时，返回index.html
@app.get("/")
def read_roat():
    return FileResponse("index.html")