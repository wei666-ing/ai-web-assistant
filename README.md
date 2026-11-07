# 🚀 基于 DeepSeek 的 Web 端 AI 聊天助手

这是一个基于 Python 全栈开发的 AI 聊天应用。前端使用原生 HTML/CSS/JavaScript 构建，后端采用 FastAPI 框架，成功接入 DeepSeek 大语言模型 API。项目实现了**带上下文记忆的多轮对话**，并支持**基于 SSE 的流式输出（打字机效果）**与**Markdown 实时渲染**。

## 🛠️ 技术栈
- **前端**：HTML5, CSS3, 原生 JavaScript (Fetch API, ReadableStream)
- **后端**：Python 3, FastAPI, Uvicorn
- **大模型**：DeepSeek API (兼容 OpenAI 格式)
- **第三方库**：marked.js (Markdown 解析), highlight.js (代码高亮)
- **环境管理**：python-dotenv

## ✨ 核心功能与亮点
1. **流式打字机输出**：基于 SSE (Server-Sent Events) 技术，后端使用 `StreamingResponse`，前端利用 `ReadableStream` 实时渲染，大幅降低首字延迟。
2. **上下文记忆**：前端维护 `chatHistory` 数组，每次请求携带完整历史消息，实现流畅的多轮连贯对话。
3. **富文本渲染**：引入 `marked.js` 和 `highlight.js`，将大模型输出的 Markdown 格式实时渲染为漂亮的排版和带高亮的代码块。
4. **安全防护**：使用 `.env` 文件隔离 API Key，通过 `.gitignore` 防止敏感信息泄露。

## 📸 项目演示
*(把你刚才发我的那张带代码高亮的截图，直接拖拽到这里，GitHub 会自动生成图片链接)*

## ⚙️ 本地运行指南
1. 克隆本项目：
   ```bash
   git clone https://github.com/wei666-ing/ai-web-assistant.git