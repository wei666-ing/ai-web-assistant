# 1. 使用官方轻量级的 Python 3.11 镜像
FROM python:3.11-slim

# 2. 设置容器里的工作目录
WORKDIR /app

# 3. 安装所有依赖库（用了清华源加速）
RUN pip install fastapi uvicorn requests python-dotenv chromadb pypdf python-multipart bcrypt pyjwt openai -i https://pypi.tuna.tsinghua.edu.cn/simple

# 4. 把当前目录的所有代码复制进容器的 /app 目录
COPY . .

# 5. 暴露 8000 端口
EXPOSE 8000

# 6. 启动命令（注意 host 必须是 0.0.0.0，否则容器外访问不到）
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]