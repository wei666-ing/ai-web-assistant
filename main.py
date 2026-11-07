from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import FileResponse, StreamingResponse
from ai_client import ask_deepseek, ask_deepseek_stream

app = FastAPI()

class ChatRequest(BaseModel):
    messages: list

@app.post("/chat")
def chat(request: ChatRequest):
    return{"reply": ask_deepseek(request.messages)}

@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    return StreamingResponse(ask_deepseek_stream(request.messages), media_type="text/event-stream")

#新增：当用户访问根目录 （http://127/0.0.1：0000）时，返回index.html
@app.get("/")
def read_roat():
    return FileResponse("index.html")