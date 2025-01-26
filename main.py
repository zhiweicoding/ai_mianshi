from fastapi import FastAPI, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, JSONResponse
import os
from dotenv import load_dotenv
from openai import OpenAI
import time
import asyncio
import hashlib
import hmac
import base64
from urllib.parse import quote
from websocket import create_connection
import json
import tempfile

load_dotenv()

app = FastAPI()

# 初始化DeepSeek客户端
client = OpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url="https://api.deepseek.com/v1"
)
app.mount("/static", StaticFiles(directory="static"), name="static")

async def stream_response(prompt: str):
    try:
        # 记录开始调用API的时间
        api_start_time = time.time()
        print(f"开始调用DeepSeek API，时间：{api_start_time}")

        # 调用DeepSeek API进行流式对话
        stream = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )

        first_response = True
        # 使用迭代器处理响应
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                content = chunk.choices[0].delta.content
                print(content, end="", flush=True)
                if first_response:
                    first_response_time = time.time()
                    print(f"收到第一个响应，时间：{first_response_time}")
                    print(f"API响应延迟：{first_response_time - api_start_time:.2f}秒")
                    first_response = False
                yield f"data: {content}\n\n"
                # await asyncio.sleep(0.05)  # 添加小延迟以确保数据能够正确传输
    except Exception as e:
        error_message = f"错误：{str(e)}"
        print(f"DeepSeek API错误: {error_message}")
        yield f"data: {error_message}\n\n"

@app.get("/")
async def root():
    return {"message": "AI面试助手服务已启动"}

@app.post("/chat")
async def chat_endpoint(request: Request):
    try:
        # 记录接收到用户请求的时间
        request_start_time = time.time()
        print(f"\n收到新的用户请求，时间：{request_start_time}")
        
        data = await request.json()
        question = data.get("question")
        
        return StreamingResponse(
            stream_response(question),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except Exception as e:
        print(f"SSE错误：{str(e)}")
        return {"error": str(e)}

# 讯飞语音识别配置
XF_APP_ID = os.getenv('XF_APP_ID', '')
XF_API_KEY = os.getenv('XF_API_KEY', '')

@app.post("/speech-to-text")
async def speech_to_text(audio: UploadFile = File(...)):
    try:
        # 保存上传的音频文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            content = await audio.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        # 创建讯飞语音识别客户端
        class Client:
            def __init__(self):
                base_url = "ws://rtasr.xfyun.cn/v1/ws"
                ts = str(int(time.time()))
                tt = (XF_APP_ID + ts).encode('utf-8')
                md5 = hashlib.md5()
                md5.update(tt)
                baseString = md5.hexdigest()
                baseString = bytes(baseString, encoding='utf-8')

                apiKey = XF_API_KEY.encode('utf-8')
                signa = hmac.new(apiKey, baseString, hashlib.sha1).digest()
                signa = base64.b64encode(signa)
                signa = str(signa, 'utf-8')
                self.end_tag = "{\"end\": true}"

                self.ws = create_connection(base_url + "?appid=" + XF_APP_ID + "&ts=" + ts + "&signa=" + quote(signa))
                self.result = ""

            def send(self, file_path):
                file_object = open(file_path, 'rb')
                try:
                    while True:
                        chunk = file_object.read(1280)
                        if not chunk:
                            break
                        self.ws.send(chunk)
                        time.sleep(0.04)
                finally:
                    file_object.close()

                self.ws.send(bytes(self.end_tag.encode('utf-8')))

            def recv(self):
                try:
                    while self.ws.connected:
                        result = str(self.ws.recv())
                        if len(result) == 0:
                            break
                        result_dict = json.loads(result)
                        if result_dict["action"] == "result":
                            self.result += result_dict["data"]
                except:
                    pass
                finally:
                    self.ws.close()

        # 执行语音识别
        client = Client()
        client.send(temp_file_path)
        client.recv()

        # 删除临时文件
        os.unlink(temp_file_path)

        return JSONResponse({"text": client.result})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

    