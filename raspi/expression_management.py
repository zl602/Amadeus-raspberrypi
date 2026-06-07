import os
import time
import threading
from PIL import Image

class KurisuSpriteManager:
    """
    红莉栖立绘与嘴型动画异步管理器（树莓派 Pillow 专属纯净版）
    """
    def __init__(self, images_dir="resources/images", target_size=(228, 200)):
        self.images_dir = images_dir
        self.target_size = target_size  # 适配你上半部分立绘框的理想尺寸
        
        self.current_emotion = "normal"
        self.animation_frame = 0
        self.is_speaking = False
        
        # 线程与锁控制器
        self.speaking_thread = None
        self.stop_signal = threading.Event()
        self.lock = threading.Lock()
        
        # 显存优化：缓存已经加载并缩放过的图片，防止高频高负载读取SD卡
        self._sprite_cache = {}

    def _load_character_frame(self, emotion, frame):
        """
        内部底层：读取对应的物理图片，并进行等比例缩放与缓存
        图片命名规则沿用原项目：例如 normal_0.png, blush_1.png
        """
        cache_key = (emotion, frame)
        
        # 检查缓存中是否已经存在
        if cache_key in self._sprite_cache:
            return self._sprite_cache[cache_key]
            
        file_name = f"kurisu_{emotion}{frame+1}.png"
        file_path = os.path.join(self.images_dir, file_name)
        
        # 兜底判定
        if not os.path.exists(file_path):
            # 如果对应帧不存在，尝试拿闭嘴帧(0)顶替
            file_path = os.path.join(self.images_dir, f"kurisu_{emotion}1.png")
            if not os.path.exists(file_path):
                # 如果连这个表情的闭嘴帧都没有，彻底退回 normal_0
                file_path = os.path.join(self.images_dir, "kurisu_normal1.png")
                
        try:
            # 打开立绘（立绘通常是透明背景的 RGBA 格式）
            sprite_img = Image.open(file_path).convert("RGBA")
            # 缩放到适合你树莓派屏幕框的大小
            sprite_img = sprite_img.resize(self.target_size, Image.Resampling.LANCZOS)
            
            # 写入内存缓存
            self._sprite_cache[cache_key] = sprite_img
            return sprite_img
        except Exception as e:
            print(f"❌ [Sprite] 加载立绘文件失败: {e}")
            return None

    def get_current_sprite(self):
        """
        【UI 刷新核心接口】：获取当前时间点完美的立绘全透明图层
        """
        with self.lock:
            return self._load_character_frame(self.current_emotion, self.animation_frame)

    def set_emotion(self, emotion):
        """外部接口：一键切换红莉栖当前的表情"""
        with self.lock:
            self.current_emotion = emotion

    def start_speaking(self, on_frame_changed_callback=None):
        """
        【多线程核心】：异步启动嘴型闪烁动画。用原生 time 替代 QTimer！
        on_frame_changed_callback: 外部传入的屏幕刷新钩子函数，当嘴巴张合时，通知屏幕重绘
        """
        with self.lock:
            if self.is_speaking:
                return
            self.is_speaking = True
            self.stop_signal.clear()
            
        # 开启原生的 Python 后台线程，绝不阻塞主线程
        self.speaking_thread = threading.Thread(
            target=self._speaking_loop, 
            args=(on_frame_changed_callback,),
            daemon=True # 守护线程，主程序挂了它自动退出
        )
        self.speaking_thread.start()

    def stop_speaking(self):
        """一键闭嘴，并重置为第 0 帧（闭嘴状态）"""
        with self.lock:
            if not self.is_speaking:
                return
            self.stop_signal.set()
            self.is_speaking = False
            self.animation_frame = 0

    def _speaking_loop(self, callback):
        """内部线程循环：利用原生 time.sleep 控制 180ms 节奏"""
        while not self.stop_signal.is_set():
            time.sleep(0.05)
            with self.lock:
                self.animation_frame = (self.animation_frame + 1) % 3
            
            if callback:
                # 触发无参数安全重绘
                callback()
