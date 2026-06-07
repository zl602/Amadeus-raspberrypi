import time
import subprocess
import os
import st7789

# 屏幕与视频流参数 - 确保分辨率与你的显示逻辑一致
WIDTH, HEIGHT = 320, 320
LOGICAL_WIDTH, LOGICAL_HEIGHT = 320, 240
FPS = 30.0

def start_ffmpeg_pipeline(video_path):
    # 🚀 优化点：使用 -fflags nobuffer 减少输入缓冲，flags=neighbor 减少缩放带来的 CPU 损耗
    cmd = [
        "ffmpeg", "-fflags", "nobuffer", "-i", video_path,
        "-vf", f"scale={LOGICAL_WIDTH}:{LOGICAL_HEIGHT}:flags=neighbor",        
        "-pix_fmt", "rgb565be",        
        "-f", "rawvideo", "-v", "quiet", "-"                                        
    ]
    frame_size = LOGICAL_WIDTH * LOGICAL_HEIGHT * 2
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, bufsize=frame_size * 5)
    return process, frame_size

def start_audio_pipeline(video_path):
    # 使用 ffplay 独立驱动音频
    audio_cmd = ["ffplay", "-nodisp", "-autoexit", "-v", "quiet", video_path]
    return subprocess.Popen(audio_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def play_video_with_audio(video_path, amadeus_ui, button_manager):
    if not os.path.exists(video_path):
        print(f"❌ [Player] 找不到文件: {video_path}")
        return False

    print(f"\n🚀 [Player] 开始独占播放: {video_path}")
    
    # 1. 锁死 UI 渲染通道
    amadeus_ui.request_access(True)
    
    # 2. 硬件初始化同步
    amadeus_ui.disp.reset()
    amadeus_ui.disp.begin()
    
    video_process = None
    audio_process = None
    
    try:
        video_process, frame_size = start_ffmpeg_pipeline(video_path)
        audio_process = start_audio_pipeline(video_path)
        video_start_time = time.time()
        
        frame_count = 0
        frame_delay = 1.0 / FPS

        while True:
            # 安全退出
            if button_manager.get_triggered_button() == "Y":
                break
            
            # 3. 智能丢帧逻辑：如果当前时间超过预期时间太多，直接丢弃该帧
            elapsed = time.time() - video_start_time
            expected_time = (frame_count + 1) * frame_delay
            
            if elapsed > expected_time + frame_delay:
                # 严重滞后：直接跳帧，不执行任何 SPI 写入
                video_process.stdout.read(frame_size)
                frame_count += 1
                continue
            
            raw_bytes = video_process.stdout.read(frame_size)
            if not raw_bytes or len(raw_bytes) < frame_size:
                break
                
            frame_count += 1
            
            # 4. 显存写入
            amadeus_ui.disp.set_window(0, 0, LOGICAL_WIDTH - 1, LOGICAL_HEIGHT - 1)
            amadeus_ui.disp.command(0x2C) 
            amadeus_ui.disp.data(raw_bytes)

    except Exception as e:
        print(f"❌ [Player Error]: {e}")
    finally:
        # 1. 彻底杀死进程组，确保不会留有僵尸进程占用资源
        if video_process:
            video_process.terminate()
            video_process.stdout.close()
        if audio_process:
            audio_process.kill()
        
        # 2. 给底层驱动一点喘息时间
        time.sleep(0.5) 
        
        # 3. 重新强制初始化显示屏，这是防止“卡死”的关键
        amadeus_ui.disp.reset()
        amadeus_ui.disp.begin()
        
        # 4. 归还控制权
        amadeus_ui.request_access(False)
        amadeus_ui.render_and_refresh()
        print("🔄 [Player] 播放完毕，硬件已复位。")