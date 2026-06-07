import httpx
import subprocess
import time
import os
from pathlib import Path
from typing import Optional

class TTSClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

        self.cache_dir = Path("./audio_cache")
        # 确保缓存目录存在
        self.cache_dir.mkdir(exist_ok=True)
    def _download_to_cache(self, client: httpx.Client, text: str) -> bool:
        """流式播放，成功返回 True，失败返回 False"""
        try:
            headers = {"x-api-key": self.api_key}
            payload = {"text": text}
            
            # 开启播放进程
            process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-i", "pipe:0"],
                stdin=subprocess.PIPE,
                stderr=subprocess.DEVNULL
            )
            
            with client.stream("POST", f"{self.base_url}/tts", json=payload, headers=headers) as resp:
                resp.raise_for_status()
                for chunk in resp.iter_bytes():
                    process.stdin.write(chunk)
            
            process.stdin.close()
            time.sleep(0.5)
            process.wait()
            return True # 播放成功
            
        except Exception as e:
            print(f"流式播放错误: {e}")
            return False

    def speak(self, text: str):
        timeout = httpx.Timeout(60.0, connect=10.0)
        with httpx.Client(timeout=timeout) as client:
            # 这里接收的是布尔值
            success = self._download_to_cache(client, text)
            
            if success:
                print("语音播放流程已结束。")
            else:
                print("合成失败，请检查网络或服务器状态")

if __name__ == "__main__":
    # 请替换为你的 Tailscale IP
    PC_IP = "100.105.58.16"
    client = TTSClient(f"http://{PC_IP}:8000", "******")
    
    # 测试对话
    client.speak("hiiii。")
