import httpx
from fastapi import FastAPI, Request, Header, HTTPException, Response
from fastapi.responses import StreamingResponse
import subprocess
import json
import httpx
app = FastAPI()

# --- 配置区 ---
SECRET_KEY = "324511"
# 确保这个地址指向你已经在运行的 api_v2.py 服务
TTS_BACKEND_URL = "http://127.0.0.1:9880/tts"

# 参考音频配置（API 会自动使用这些配置）


# 异步客户端，用于高性能转发
client = httpx.AsyncClient(timeout=120.0)

@app.post("/tts")

async def tts_proxy(request: Request, x_api_key: str = Header(None)):
    if x_api_key != SECRET_KEY:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 显式构造参数，确保非空
    params = {
        "text": data.get("text", "こんにちは"),
        "text_lang": data.get("text_lang", "ja"),
        "ref_audio_path": "D:/GPT-SoVITS-v2pro-20250604/ref_audio/001.wav",
        "prompt_text": "あなたに会いに来たの、岡部凛太郎さん じゃなくて、鳳凰院京馬さんだった?",
        "prompt_lang": "ja",
        "streaming_mode": True,
        "media_type": "wav"
    }

    async def generate():
        try:
            async with client.stream("POST", TTS_BACKEND_URL, json=params) as resp:
                if resp.status_code != 200:
                    yield b"Error: Backend returned non-200 status"
                    return
                
                async for chunk in resp.aiter_bytes():
                    yield chunk
        except Exception as e:
            # 捕获连接异常，防止网关直接崩溃导致树莓派接收到截断流
            print(f"Streaming error: {e}")
            yield b"" 

    return StreamingResponse(generate(), media_type="audio/wav")

if __name__ == "__main__":
# 直接启动网关
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)