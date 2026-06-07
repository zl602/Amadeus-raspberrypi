import os
import threading
from PIL import Image, ImageDraw, ImageFont
import ST7789 as ST7789
from expression_management import KurisuSpriteManager
import time

class AmadeusDisplay:
    def __init__(self, bg_path="amadeus_bg.png"):
        self.SCR_WIDTH, self.SCR_HEIGHT = 320, 320
        self.SCR_ROTATION = 0
        self.OFFSET_TOP = 256
        
        self.RENDER_W, self.RENDER_H = 320, 240
        self.bg_path = bg_path
        
        # 核心控制变量
        self.hardware_lock = threading.Lock()
        self.is_locked = False  # 🌟【新增】排他锁开关
        
        self.current_text = "Initiating..."
        self.current_emotion="eyes_closed"
        
        self.COLOR_DARK_RED = (130, 0, 0)
        self.COLOR_BRIGHT_RED = (230, 20, 20)
        self.COLOR_TEXT_MAIN = (220, 220, 220)
        
        self.disp = self._init_hardware_screen()
        self.cached_background = self._preload_and_crop_background()
        
        FONT_PATH = "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"
        self.font = ImageFont.truetype(FONT_PATH, 12) if os.path.exists(FONT_PATH) else ImageFont.load_default()
        
        self.sprite_manager = KurisuSpriteManager(images_dir="images", target_size=(115, 200))

        self.logo_render()
        time.sleep(2)
        self.update_status(self.current_text, emotion="eyes_closed")
        self.render_and_refresh()
    def request_access(self, status=True):
        """🌟【核心权限申请】：申请使用 SPI 总线"""
        self.is_locked = status
        if status:
            self.sprite_manager.stop_speaking() # 锁定期间强制闭嘴
        print(f"[UI] SPI 总线权限变更 -> 锁定: {self.is_locked}")

    def _init_hardware_screen(self):
        disp = ST7789.ST7789(
            port=0, cs=1, dc=9, backlight=13, rst=None,
            width=self.SCR_WIDTH, height=self.SCR_HEIGHT,
            rotation=self.SCR_ROTATION, offset_top=self.OFFSET_TOP, spi_speed_hz=60000000, invert = True
        )
        disp.begin()
        disp.reset()
        return disp

    def _preload_and_crop_background(self):
        bg_image = Image.open(self.bg_path)
        orig_w, orig_h = bg_image.size
        ratio = max(self.RENDER_W / orig_w, self.RENDER_H / orig_h)
        new_w, new_h = int(orig_w * ratio), int(orig_h * ratio)
        bg_resized = bg_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        return bg_resized.crop((
            (new_w - self.RENDER_W) / 2, (new_h - self.RENDER_H) / 2,
            (new_w + self.RENDER_W) / 2, (new_h + self.RENDER_H) / 2
        )).convert("RGB")

    def _wrap_text(self, text, max_chars=14):
        wrapped_lines = []
        for line in text.split('\n'):
            for i in range(0, len(line), max_chars):
                wrapped_lines.append(line[i:i+max_chars])
        return "\n".join(wrapped_lines[:10])

    def update_status(self, text_content=None, emotion=None):
        if text_content is not None:
            self.current_text = text_content
        if emotion is not None:
            self.current_emotion = emotion
            self.sprite_manager.set_emotion(emotion)

    def render_and_refresh(self):
        """渲染逻辑加入锁检查"""
        # 🌟【新增保护】：如果被锁住，UI 线程严禁向总线发送数据
        if self.is_locked:
            return

        with self.hardware_lock:
            canvas = self.cached_background.copy()
            ui_overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(ui_overlay)
            
            SEMI_TRANS_RED = (35, 0, 0, 95)
            overlay_draw.rectangle((6, 30, 192, 230), fill=SEMI_TRANS_RED, outline=self.COLOR_DARK_RED, width=2)
            overlay_draw.rectangle((198, 30, 314, 230), fill=SEMI_TRANS_RED, outline=self.COLOR_DARK_RED, width=2)
            
            sprite_img = self.sprite_manager.get_current_sprite()
            if sprite_img:
                ui_overlay.paste(sprite_img, (199, 30), sprite_img)
                
            canvas = Image.alpha_composite(canvas.convert("RGBA"), ui_overlay).convert("RGB")
            draw = ImageDraw.Draw(canvas)
            draw.rectangle((0, 0, self.RENDER_W, 22), fill=(15, 0, 0))
            draw.line((0, 22, self.RENDER_W, 22), fill=self.COLOR_BRIGHT_RED, width=1)
            draw.line((4, 30, 4, 45), fill=self.COLOR_BRIGHT_RED, width=2)
            draw.line((4, 30, 15, 30), fill=self.COLOR_BRIGHT_RED, width=2)
            draw.text((12, 4), "AMADEUS SYSTEM v2.0", fill=(200, 200, 200), font=self.font)
            draw.rectangle((12, 36, 90, 48), fill=(20, 0, 0))
            draw.text((16, 37), "LOG OUTPUT", fill=self.COLOR_BRIGHT_RED, font=self.font)
            display_text = self._wrap_text(self.current_text)
            draw.text((16, 56), display_text, fill=self.COLOR_TEXT_MAIN, font=self.font)
            
            self.disp.display(canvas)
            
    def logo_render(self, image_path="images/logo39.png", display_logo = True):
        """
        自动处理并显示 Logo：自动将图片高度统一缩放至 200，并居中显示
        """
        if self.is_locked:
            return

        # 1. 创建黑色画布
        canvas = Image.new("RGB", (self.RENDER_W, self.RENDER_H), (0, 0, 0))

        if os.path.exists(image_path) and display_logo:
            try:
                with Image.open(image_path) as img:
                    img = img.convert("RGBA")
                    
                    # --- 自动处理逻辑 ---
                    # 如果高度不为 200，则按比例缩放，确保高度为 200
                    target_h = 200
                    if img.height != target_h:
                        ratio = target_h / float(img.height)
                        new_w = int(float(img.width) * float(ratio))
                        img = img.resize((new_w, target_h), Image.Resampling.LANCZOS)
                    
                    # 计算居中坐标
                    x = (self.RENDER_W - img.width) // 2
                    y = (self.RENDER_H - img.height) // 2
                    
                    # 贴图
                    canvas.paste(img, (x, y), img)
            except Exception as e:
                print(f"[UI] Logo处理失败: {e}")

        # 2. 硬件推送
        with self.hardware_lock:
            self.disp.display(canvas)
                
