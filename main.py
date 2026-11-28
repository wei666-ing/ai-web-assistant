import io
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column,Session,sessionmaker

import bcrypt
import chromadb
import jwt
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pypdf import PdfReader

from ai_client import ask_deepseek, ask_deepseek_stream

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "chat_history.db")

# JWT 配置：密钥只放在 .env 里，绝不写死在代码中
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY or len(SECRET_KEY) < 32:
    raise RuntimeError("缺少 JWT_SECRET_KEY 或长度不足 32 位，请在 .env 中配置一个安全的随机密钥")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

bailian_key = os.getenv("BAILIAN_API_KEY")

# 用于解析 Token 的依赖
# auto_error=False：没带 Token 时不让 FastAPI 直接抛 403，交给我们自己返回 401，
# 这样 /docs 里测试“不带 Token 访问 /history”看到的就是 401
security = HTTPBearer(auto_error=False)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """守卫：解析前端传过来的 Token，返回 user_id"""
    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录或缺少 Token，请先登录")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        return user_id
    except Exception:
        raise HTTPException(status_code=401, detail="登录已过期或 Token 无效，请重新登录")


# ================= 密码 / Token 工具 =================
def get_password_hash(password: str) -> str:
    """加密密码（bcrypt 只取前 72 字节）"""
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验密码"""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(data: dict) -> str:
    """生成 JWT，24 小时过期"""
    to_encode = data.copy()
    to_encode.update({"exp": datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# 注册和登录的请求体格式
class UserAuth(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    messages: list

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()
# 把 static 目录挂到 /static，前端就能用本地文件，不再依赖外网 CDN
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")


# ================= 数据库（历史记录）相关 =================
def init_db():
    Base.metadata.create_all(bind=engine)
init_db()


# ================= 注册 / 登录 =================
USERNAME_MIN, USERNAME_MAX = 3, 20
PASSWORD_MIN, PASSWORD_MAX = 6, 32
USERNAME_PATTERN = re.compile(r"[A-Za-z0-9_\u4e00-\u9fa5]+")


def validate_user_input(user: UserAuth) -> str:
    """注册信息校验，返回去掉首尾空格的用户名；不合法直接抛 400"""
    username = user.username.strip()
    password = user.password

    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    if not (USERNAME_MIN <= len(username) <= USERNAME_MAX):
        raise HTTPException(status_code=400, detail=f"用户名长度需为 {USERNAME_MIN}-{USERNAME_MAX} 个字符")
    if not USERNAME_PATTERN.fullmatch(username):
        raise HTTPException(status_code=400, detail="用户名只能包含中文、字母、数字和下划线")
    if not password:
        raise HTTPException(status_code=400, detail="密码不能为空")
    if not (PASSWORD_MIN <= len(password) <= PASSWORD_MAX):
        raise HTTPException(status_code=400, detail=f"密码长度需为 {PASSWORD_MIN}-{PASSWORD_MAX} 个字符")
    if not password.strip():
        raise HTTPException(status_code=400, detail="密码不能全为空格")

    return username

@app.post("/register")
def register(user: UserAuth, db: Session = Depends(get_db)):
    # ① 校验格式
    username = validate_user_input(user)

    # ② 查重：去 users 表找有没有同名账号
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已被注册")

    # ③ 建对象（这时它还只在内存里，数据库里没有）
    new_user = User(
        username=username,
        password_hash=get_password_hash(user.password),
    )

    # ④ 写库：add 只是排队，commit 才真正执行 INSERT
    db.add(new_user)
    db.commit()

    return {"message": "注册成功", "username": username}

@app.post("/login")
def login(user: UserAuth, db: Session = Depends(get_db)):
    username = user.username.strip()

    # ① 查账号
    user_row = db.query(User).filter(User.username == username).first()
    if not user_row:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # ② 验密码（用数据库里存的哈希对比）
    if not verify_password(user.password, user_row.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # ③ 签发 token，sub 必须是字符串
    access_token = create_access_token(data={"sub": str(user_row.id)})

    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/history")
def get_history(user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    # 查：只拿当前用户的消息
    rows = db.query(Message).filter(Message.user_id == user_id).all()

    # 转：保持前端要的结构 [{role, content}]
    return [{"role": m.role, "content": m.content} for m in rows]

@app.post("/save_message")
def save_message(role: str, content: str, user_id: int = Depends(get_current_user), db: Session = Depends(get_db)):
    message = Message(user_id=user_id, role=role, content=content)
    db.add(message)
    db.commit()
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
def chat_rag(request: ChatRequest, user_id: int = Depends(get_current_user)):
    """RAG 问答接口（非流式，一次性返回），必须登录"""
    # 1. 获取用户最后一句提问
    question = request.messages[-1]["content"]

    # 2. 检索本地知识库
    q_vector = get_embedding(question)
    client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))
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
def chat_stream(request: ChatRequest, user_id: int = Depends(get_current_user)):
    return StreamingResponse(ask_deepseek_stream(request.messages), media_type="text/event-stream")


@app.get("/")
def read_root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


@app.post("/upload")
async def upload_file(user_id: int = Depends(get_current_user), file: UploadFile = File(...)):
    """上传知识库文件，必须登录"""
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
        client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "chroma_db"))
        collection = client.get_or_create_collection(name="my_knowledge")

        # 为了让每次上传的 ID 不重复，用文件名+时间戳
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


# ================= 直接运行入口 =================
# 不加这一段，在 PyCharm / VS Code 里点“运行 main.py”只会加载一遍代码就静默退出，
# 看起来就是“运行不了”。加上以后 `python main.py` 也能直接把服务起起来。
if __name__ == "__main__":
    import uvicorn

    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "8000"))

    print(f"服务已启动：http://{HOST}:{PORT}  （按 Ctrl+C 停止）")
    uvicorn.run("main:app", host=HOST, port=PORT)
