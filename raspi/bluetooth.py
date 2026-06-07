import asyncio
from bleak import BleakClient

# 你的 AirPods 或蓝牙设备的 MAC 地址
DEVICE_ADDRESS = "40:DA:5C:76:D3:71"

async def connect(address):
    print(f"正在尝试连接设备: {address} ...")
    
    async with BleakClient(address) as client:
        is_connected = client.is_connected
        print(f"连接状态: {'成功' if is_connected else '失败'}")
        
        if is_connected:
            print("\n🎉 成功建立连接！")
            print("按 Ctrl + C 可以安全退出并断开连接。\n")
            
            # 使用无限循环保持程序不退出
            while True:
                # 每隔 5 秒检查一次连接状态，确保设备还在
                if not client.is_connected:
                    print("检测到设备已主动断开连接！")
                    break
                
                print("连接正常，正在保持通信中...")
                await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        # 启动异步事件循环
        asyncio.run(connect(DEVICE_ADDRESS))
    except Exception as e:
        print(f"\n连接过程中出现错误: {e}")
        print("排查建议：")
        print("1. 确保树莓派的蓝牙已经打开 (可以使用 'hciconfig' 或 'bluetoothctl' 检查)")
        print("2. 确保目标设备正处于配对/广播状态")
        print("3. 如果提示权限问题，尝试使用 'sudo python connect_bluetooth.py' 运行")