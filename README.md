# 🚀 基于 DeepSeek 的 Web 端 AI 聊天助手

这是一个基于 Python 全栈开发的 AI 聊天应用。前端使用原生 HTML/CSS/JavaScript 构建，后端采用 FastAPI 框架，成功接入 DeepSeek 大语言模型 API。项目实现了**带上下文记忆的多轮对话**，并支持**基于 SSE 的流式输出（打字机效果）**与**Markdown 实时渲染**。

## 🛠️ 技术栈
- **前端**：HTML5, CSS3, 原生 JavaScript (Fetch API, ReadableStream)
- **后端**：Python 3, FastAPI, Uvicorn
- **鉴权**：JWT（PyJWT）+ bcrypt 密码哈希
- **大模型**：DeepSeek API (兼容 OpenAI 格式)
- **第三方库**：marked.js (Markdown 解析，已改为本地引入，见下方“常见问题”)
- **环境管理**：python-dotenv

## ✨ 核心功能与亮点
1. **流式打字机输出**：基于 SSE (Server-Sent Events) 技术，后端使用 `StreamingResponse`，前端利用 `ReadableStream` 实时渲染，大幅降低首字延迟。
2. **上下文记忆**：前端维护 `chatHistory` 数组，每次请求携带完整历史消息，实现流畅的多轮连贯对话。
3. **富文本渲染**：使用本地引入的 `marked.js`，将大模型输出的 Markdown 格式实时渲染为标题、列表、表格和代码块。
4. **安全防护**：使用 `.env` 文件隔离 API Key，通过 `.gitignore` 防止敏感信息泄露。
5. **用户鉴权与多租户隔离**：注册 / 登录后签发 JWT，前端存于 `localStorage` 并在每次请求带上 `Authorization: Bearer <token>`；聊天、知识库上传、历史读写接口全部由 `get_current_user` 守卫，未登录返回 401，聊天记录按 `user_id` 隔离。

## 📸 项目演示
*(把你刚才发我的那张带代码高亮的截图，直接拖拽到这里，GitHub 会自动生成图片链接)*

## ⚙️ 本地运行指南
1. 克隆本项目：
   ```bash
   git clone https://github.com/wei666-ing/ai-web-assistant.git
   cd ai-web-assistant
   ```
2. 安装依赖：
   ```bash
   python -m pip install fastapi uvicorn requests python-dotenv pypdf chromadb pyjwt bcrypt python-multipart
   ```
3. 在项目根目录新建 `.env`，填入自己的 Key 和 JWT 密钥：
   ```
   DEEPSEEK_API_KEY=sk-你的 DeepSeek Key
   BAILIAN_API_KEY=sk-你的百炼 Key（RAG 向量化用）
   JWT_SECRET_KEY=你的随机密钥（至少 32 位）
   ```
   `JWT_SECRET_KEY` 可用下面这条命令生成：
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   ```
   > 这项是必填的：缺失或少于 32 位，`main.py` 会在启动时直接报错退出（避免弱密钥上线）。
   > 更换该密钥会让已签发的 Token 全部失效，前端会提示重新登录。
4. 启动服务：
   ```bash
   python -m uvicorn main:app --reload
   ```
5. 浏览器访问 `http://127.0.0.1:8000`（**不要直接双击 index.html**），首次使用先在页面顶部注册账号再登录。

## 🔐 接口一览

| 接口 | 方法 | 是否需要 Token |
|---|---|---|
| `/register` `/login` | POST | 否 |
| `/chat/stream` `/chat/rag` `/upload` `/history` `/save_message` | POST / GET | **是** |
| `/docs` | GET | 否（在线接口文档，可点 Authorize 填 Token 调试） |

## 🐞 常见问题

### 页面上显示“请求失败。”

排查顺序：先看浏览器控制台（F12 → Console），再看运行 uvicorn 的终端。

- **直接双击打开了 index.html**：页面处于 `file://` 协议，请求发不到后端。必须通过 `http://127.0.0.1:8000` 访问。
- **uvicorn 没启动或端口被占用**：终端里没有 `Uvicorn running on http://127.0.0.1:8000` 就说明后端没起来。
- **“marked is not defined”**：原先 index.html 从 jsdelivr / bootcdn 加载 marked 和 highlight.js，这两个 CDN 在国内经常连接被重置或 404，库没加载进来，`marked.parse()` 抛错后被 `catch` 统一显示成“请求失败”。

  修复方式：把 marked 下载下来放到 `static/marked.min.js`，由 FastAPI 的 `StaticFiles` 挂载到 `/static` 对外提供，页面改为 `<script src="/static/marked.min.js">`，彻底不依赖外网；同时在代码里加了降级逻辑，渲染库缺失时退化为纯文本，不会再整段变成“请求失败”。当前错误提示也会带上真实原因（如 `请求失败：HTTP 500`），方便定位。

### 换了电脑 / 换了终端后 `ModuleNotFoundError: No module named 'fastapi'`
说明当前 `python` 不是装过依赖的那个解释器。用 `python --version` 和 `python -m pip list` 确认，必要时指定完整路径，例如 `C:\Users\wei\AppData\Local\Programs\Python\Python311\python.exe -m uvicorn main:app --reload`。

### 启动时报 `RuntimeError: 缺少 JWT_SECRET_KEY 或长度不足 32 位`
`.env` 里没配 `JWT_SECRET_KEY`，或配得太短。按上面的命令生成一个随机串补进去即可；`.env` 已被 `.gitignore` 忽略，不会上传。

### 页面提示“登录已过期，请重新登录”
Token 有效期为 24 小时，或服务端更换过 `JWT_SECRET_KEY`。重新登录一次即可，历史记录仍按账号保存在 `chat_history.db` 中。
