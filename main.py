from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from typing import List

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

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
            # TODO: 这里将添加语音识别和AI模型处理逻辑
            await manager.broadcast(f"收到消息: {data}")
    except Exception as e:
        manager.disconnect(websocket)


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

    