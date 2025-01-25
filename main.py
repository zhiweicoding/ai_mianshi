from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from typing import List
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI()

# 初始化DeepSeek客户端
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url="https://api.deepseek.com/v1"
)
app.mount("/static", StaticFiles(directory="static"), name="static")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, websocket: WebSocket, message: str):
        await websocket.send_text(message)

    async def stream_response(self, websocket: WebSocket, prompt: str):
        try:
            # 调用DeepSeek API进行流式对话
            stream = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )

            # 逐字输出响应
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    content = chunk.choices[0].delta.content
                    # print(f"DeepSeek流式返回: {content}")  # 添加调试信息
                    await self.send_message(websocket, content)
        except Exception as e:
            error_message = f"错误：{str(e)}"
            print(f"DeepSeek API错误: {error_message}")  # 添加错误调试信息
            await self.send_message(websocket, error_message)

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "AI面试助手服务已启动"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 使用DeepSeek API处理问题并流式输出回答
            await manager.stream_response(websocket, data)
    except Exception as e:
        print(f"WebSocket错误：{str(e)}")
        manager.disconnect(websocket)


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

    