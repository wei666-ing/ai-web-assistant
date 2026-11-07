import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")

# 定义一个函数，接收用户的问题 (prompt)，返回 AI 的回答
def ask_deepseek(messages):
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization":f"Bearer {api_key}",
        "Content-Type":"application/json",
    }

    #任务1：把prompt 变量放进 message里
    data = {
        "model": "deepseek-chat",
        "messages":messages
    }
    #任务2：发送请求，获取结果
    resp = requests.post(url, headers=headers, json=data, timeout=30)

    #任务3：判断一下状态码是不是 200，如果不是，打印错误并返回None
    if resp.status_code == 200:
        result = resp.json()
        #提取并返回模型回复的文本
        return result["choices"][0]["message"]["content"]
    else:
        print(f"请求失败:{resp.status_code}", resp.json())
        return None

#测试一下这个函数
if __name__ == "__main__":
    print("=== AI助手已启动 (输入 'exit' 退出) ===")

    #1.准备一个空列表，用来存所有的聊天记录
    history_messages = []

    #2.开启死循环，让你能一直聊
    while True:
        #接收你的输入
        user_input = input("\n你:")

        #如果输入 exit,就退出循环
        if user_input.lower() == "exit":
            print("再见！")
            break

        #3.把你说的话存进列表
        history_messages.append({"role": "user", "content": user_input})

        #4.调用函数，把整个列表发给 AI
        print("AI 思考中...")
        ai_reply = ask_deepseek(history_messages)

        if ai_reply:
            print(f"AI:{ai_reply}")
            #5.极其重要：把AI的回答也存进列表，否则下一句它就忘了自己刚说了啥
            history_messages.append({"role": "assistant", "content": ai_reply})

def ask_deepseek_stream(messages):
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": "deepseek-chat",
        "messages": messages,
        "stream": True   # 关键：告诉大模型开启流式输出
    }

    # 关键：设置 stream=True，不让 requests 一次性下载全部数据
    resp = requests.post(url, headers=headers, json=data, stream=True, timeout=30)

    if resp.status_code ==200:
        # 逐行读取服务器的响应
        for line in resp.iter_lines():
            if line:
                decode_line = line.decode("utf-8")
                if decode_line.startswith("data:"):
                    json_str = decode_line[6:]
                    if json_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(json_str)
                        delta = chunk["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except Exception:
                        pass
    else:
        yield "请求失败，请检查控制台。"