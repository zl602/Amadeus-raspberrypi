import os
import time
import gpiod
from gpiod.line import Value

class AmadeusButtonManager:
    """
    Amadeus 硬件按钮状态监听管理器
    基于 Linux 新版 gpiod 标准驱动封装，集成了批量上拉初始化、状态锁、边缘按下判定。
    """
    def __init__(self, pin_config=None):
        # 默认使用你调校好的物理引脚映射
        if pin_config is None:
            self.pin_config = {
                "A": 5,
                "B": 6,
                "X": 16,  # 暂停继续 / 功能切换
                "Y": 24   # 安全退出
            }
        else:
            self.pin_config = pin_config

        # 1. 批量自动扫描 Linux 的 gpiochip 芯片群
        self.chip, self.request = self._init_gpio_buttons()
        
        # 2. 状态锁：用来记录上一帧每个按钮的电平状态，做边缘触发判定（防连续疯狂重触发）
        self.last_states = {name: Value.INACTIVE for name in self.pin_config}

    def _init_gpio_buttons(self):
        """内部底层函数：自动扫描并批量初始化具有上拉 Bias 的线路"""
        chips = [f for f in os.listdir('/dev/') if f.startswith('gpiochip')]
        if not chips:
            raise RuntimeError("❌ [Buttons] 错误：系统里连一个 GPIO 芯片都没找到！")
        chips.sort()
        target_chip_path = os.path.join('/dev', chips[-1])
        
        print(f"[Buttons] 正在绑定 GPIO 芯片路径: {target_chip_path}")
        chip = gpiod.Chip(target_chip_path)
        
        # 批量为所有引脚配置 INPUT（输入）和 PULL_UP（内部上拉电阻，默认高电平）
        combined_config = {
            pin: gpiod.LineSettings(
                direction=gpiod.line.Direction.INPUT,
                bias=gpiod.line.Bias.PULL_UP
            ) for pin in self.pin_config.values()
        }
        
        request = chip.request_lines(consumer="AmadeusButtons", config=combined_config)
        print("[Buttons] 硬件按钮矩阵上拉配置完毕，进入待命状态。")
        return chip, request

    def get_triggered_button(self):
        """
        【核心对外接口】：非阻塞检测。
        每次主循环调用此函数，都会刷新硬件电平。
        返回: 
            str: "A", "X", "Y" （如果某个按钮恰好发生按下触发事件）
            None: 如果没有任何事情发生
        """
        triggered = None
        
        # 读取当前这一瞬间所有按钮的实时硬件电平
        current_states = {name: self.request.get_value(pin) for name, pin in self.pin_config.items()}
        
        for name in self.pin_config:
            # 判定触发边缘：上一帧处于 ACTIVE（按下），这一帧变成了 INACTIVE（松开/弹起）
            # 这表明用户完成了一次完整的“按下并抬起”动作
            if current_states[name] == Value.INACTIVE and self.last_states[name] == Value.ACTIVE:
                triggered = name
                # 微量消抖，防止由于轻微颤抖导致双击
                time.sleep(0.12)
                break  # 优先响应最先捕捉到的这一个
                
        # 刷新状态锁，留给下一轮循环对比
        self.last_states = current_states
        return triggered

    def close(self):
        if hasattr(self, 'request') and self.request:
            try:
                # gpiod v2.x 的标准释放方法是 release()，或者直接把它从内存中 del
                self.request.release() 
            except Exception as e:
                print(f"⚠️ 释放按钮引脚时遇到小问题: {e}")
                
    def is_pressed(self, name):
        """
        新增接口：直接返回按钮当前的物理状态
        Value.ACTIVE (按下) / Value.INACTIVE (抬起)
        """
        pin = self.pin_config[name]
        return self.request.get_value(pin) == Value.INACTIVE

