from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
import os
from dotenv import load_dotenv
from openai import OpenAI
import time
import asyncio

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

@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}

    