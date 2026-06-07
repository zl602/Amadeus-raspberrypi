import time
import threading
import subprocess
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ui_manager_hr import AmadeusDisplay
from button import AmadeusButtonManager
from llm_api_ops import ask_amadeus_stream
from video import play_video_with_audio
from local_api import TTSClient
from record_stt import run_asr_session
from bluetooth import connect

# 全局资源管理：使用线程池替代直接创建线程，防止系统句柄溢出
executor = ThreadPoolExecutor(max_workers=3)
ui_lock = threading.Lock()

class AppState:
    def __init__(self):
        self.is_chatting = False
        self.client = TTSClient(base_url="http://100.105.58.16:8000", api_key="324511")

state = AppState()

def run_llm_conversation(amadeus_ui, prompt_text, sync_voice):
    if amadeus_ui.is_locked: return
    
    state.is_chatting = True
    try:
        prompt_text_with_voice = f"[{sync_voice}]{prompt_text}"
        with ui_lock:
            amadeus_ui.render_and_refresh()
        
        detected_emotion, japanese, chinese = ask_amadeus_stream(prompt_text_with_voice)
        
        with ui_lock:
            amadeus_ui.update_status(text_content=japanese, emotion=detected_emotion)
            amadeus_ui.sprite_manager.start_speaking(on_frame_changed_callback=amadeus_ui.render_and_refresh)

        # 播放逻辑：保留你的原始时长控制逻辑
        if sync_voice != "Mute":
            audio_path = state.client.speak(japanese)
            if audio_path:
                # 使用 subprocess.run 确保进程等待并回收
                subprocess.run(["ffplay", "-nodisp", "-autoexit", "-v", "quiet", audio_path])
        else:
            time.sleep(len(japanese) * 0.14)
            
    except Exception as e:
        print(f"[LLM Error] {e}")
    finally:
        with ui_lock:
            amadeus_ui.sprite_manager.stop_speaking()
            state.is_chatting = False
            amadeus_ui.render_and_refresh()

async def main():
    amadeus_ui = AmadeusDisplay()
    buttons = AmadeusButtonManager()
    loop = asyncio.get_running_loop()
    
    await asyncio.sleep(0.5)
    with ui_lock:
        amadeus_ui.update_status(text_content="SYSTEM READY", emotion="normal")
        amadeus_ui.render_and_refresh()
    
    sync_voice = "Short"
    
    try:
        while True:
            # 1. 录音触发 (使用 await asyncio.sleep)
            if buttons.is_pressed("X"):
                await asyncio.sleep(0.05)
                if buttons.is_pressed("X"): 
                    final_text = await run_asr_session("wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_async", buttons)
                    if final_text and final_text.strip():
                        executor.submit(run_llm_conversation, amadeus_ui, final_text, sync_voice)
            
            # 2. 视频选择分支
            triggered = buttons.get_triggered_button()
            if triggered == "A":
                video_list = {"Y":"sg_op.mp4","X":"steins_gate_0_op.mp4", "A": "sg_game.mp4", "B": "badapple.mp4"}
                with ui_lock:
                    amadeus_ui.update_status(text_content="SELECT VIDEO...", emotion="sided_thinking")
                    amadeus_ui.render_and_refresh()
                
                # 异步等待选择
                start_time = time.time()
                while time.time() - start_time < 10:
                    btn = buttons.get_triggered_button()
                    if btn in video_list:
                        await loop.run_in_executor(None, play_video_with_audio, video_list[btn], amadeus_ui, buttons)
                        # 强制清理僵尸进程，保证SPI总线不再被占用
                        os.system("pkill -9 ffplay; pkill -9 ffmpeg")
                        break
                    await asyncio.sleep(0.1) # 必须异步 sleep
                
                with ui_lock:
                    amadeus_ui.update_status(text_content="SYSTEM STANDBY", emotion="normal")
                    amadeus_ui.render_and_refresh()

            # 3. 模式切换
            elif triggered == "B":
                a = {"Full":"Short", "Short": "Mute", "Mute":"Full"}
                sync_voice = a[sync_voice]
                with ui_lock:
                    amadeus_ui.update_status(text_content=f"Mode: {sync_voice}", emotion=amadeus_ui.current_emotion)
                    amadeus_ui.render_and_refresh()

            # 4. 退出逻辑
            elif triggered == "Y":
                with ui_lock:
                    amadeus_ui.update_status(text_content="EL\nPSY\nCONGROO", emotion="eyes_closed")
                    amadeus_ui.render_and_refresh()
                await asyncio.create_subprocess_exec(
                    'python3', 'bluetooth.py',
                    stdout=asyncio.subprocess.DEVNULL,  # 如果不需要看蓝牙脚本的输出，可以静音
                    stderr=asyncio.subprocess.DEVNULL
                )
                print("后台进程已触发，主业务继续运行！")
                

            # 全局循环步长：必须异步
            await asyncio.sleep(0.05)
    finally:
        buttons.close()
        executor.shutdown(wait=False)

if __name__ == "__main__":
    asyncio.run(main())
