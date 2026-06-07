import os
import re
import time
from openai import OpenAI
from character_skill import build_prompt_bundle

# ==========================================
# ⚙️ 1. 核心配置区域（请填写你的 API Key）
# ==========================================
DEEPSEEK_API_KEY = "sk-edf4d6174ca542eca584cc4b51ab4a63"
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
MODEL_NAME = "deepseek-chat"

# 20种红莉栖合法表情列表（用于正则校验）
VALID_EMOTIONS = {
    "normal", "angry", "sided_angry", "blush", "sided_blush", 
    "happy", "sad", "surprised", "sided_surprised", "side", 
    "sided_thinking", "annoyed", "sided_worried", "eyes_closed", 
    "sided_eyes_closed", "sided_pleasant", "disappointed", 
    "indifferent", "pissed", "winking"
}

# ==========================================
# 🧠 2. 动态拼装来源于 Skill 的系统提示词
# ==========================================
# 调用你指定的原版函数，获取整套 Prompt 捆绑包
prompt_bundle = build_prompt_bundle()

# 核心：抽取原项目中专门负责强制命令大模型输出「[表情]日语|中文」的那个关键提示词！
AMADEUS_SYSTEM_PROMPT = prompt_bundle.bilingual_generation_prompt

# 将从 Skill 中提炼出的硬核提示词压入大模型历史
chat_history = [{"role": "system", "content": AMADEUS_SYSTEM_PROMPT}]

# ==========================================
# 🔍 3. 流式文本高能切分器（核心 Parser 纯净版）
# ==========================================
def clean_and_parse_stream(raw_buffer):
    """
    流式拦截器：输入当前接收到的总缓冲区文本，
    实时解析出当前的【表情】、【日语文本】、【中文文本】
    """
    current_emotion = "normal"
    japanese_text = ""
    chinese_text = ""
    
    # 1. 实时提取表情标签
    emotion_match = re.search(r'\[([a-zA-Z_]+)\]', raw_buffer)
    if emotion_match:
        extracted = emotion_match.group(1).lower()
        if extracted in VALID_EMOTIONS:
            current_emotion = extracted
    
    # 2. 剥离掉表情符号，处理后面的核心文本
    text_content = re.sub(r'\[[^\]]*\]', '', raw_buffer)
    
    # 3. 根据半角竖线 `|` 实时切分双语
    if '|' in text_content:
        parts = text_content.split('|', 1)
        japanese_text = parts[0].strip()
        chinese_text = parts[1].strip()
    else:
        # 如果大模型还没吐出 `|`，说明当前吐出来的全都是前半句的日语
        japanese_text = text_content.strip()
        chinese_text = ""
        
    return current_emotion, japanese_text, chinese_text

# ==========================================
# 🚀 4. DeepSeek 流式请求与打印驱动引擎
# ==========================================
def ask_amadeus_stream(user_input):
    global chat_history
    
    # 压入用户历史
    chat_history.append({"role": "user", "content": user_input})
    
    print("\n" + "="*50)
    print(f"📡 发送给 Amadeus: {user_input}")
    print("="*50)
    
    # 初始化 OpenAI 客户端（指向 DeepSeek）
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    
    # 发起 Stream 流式请求
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=chat_history,
        temperature=0.8,
        stream=True  # 开启高能流式
    )
    
    raw_buffer = ""
    last_japanese = ""
    last_chinese = ""
    detected_emotion = "normal"
    has_split = False
    
    print("\n🤖 [来自原版 Skill 驱动的流式响应...]\n")
    
    for chunk in response:
        chunk_text = chunk.choices[0].delta.content
        if chunk_text:
            raw_buffer += chunk_text
            
            # 扔进解析器获取三元素
            emotion, jp, cn = clean_and_parse_stream(raw_buffer)
            
            # 捕捉到表情变化时立刻打印提示
            if emotion != detected_emotion:
                detected_emotion = emotion
                print(f"\n🎬 [立绘切换表情 -> {detected_emotion.upper()}]")
            
            # --- 打字机效果流式切分模拟 ---
            if not has_split and '|' in raw_buffer:
                has_split = True
                print("\n🎵 [日语部分吐字完毕，开始吐屏幕中文...]")
            
            if not has_split:
                # 正在吐日语（用于给 VoiceVox 读音）
                new_jp_chars = jp[len(last_japanese):]
                if new_jp_chars:
                    print(f"{new_jp_chars}", end="", flush=True)
                    last_japanese = jp
            else:
                # 已经跨过竖线，正在吐中文（用于在树莓派小屏幕上流式打字机显示）
                new_cn_chars = cn[len(last_chinese):]
                if new_cn_chars:
                    print(f"{new_cn_chars}", end="", flush=True)
                    last_chinese = cn

    print("\n\n" + "-"*30)
    print("🏁 [本轮流式传输结束]")
    print(f"📊 最终解析汇总:")
    print(f"  • 当前立绘表情: [{detected_emotion}]")
    print(f"  • 语音TTS(日语): {last_japanese}")
    print(f"  • 屏幕显示(中文): {last_chinese}")
    print("-"*30 + "\n")
    
    # 将完整的回复存入上下文，维持傲娇记忆
    chat_history.append({"role": "assistant", "content": raw_buffer})
    return detected_emotion, last_japanese, last_chinese
# ==========================================
# 🏁 5. 测试主循环
# ==========================================
'''
if __name__ == "__main__":
    if DEEPSEEK_API_KEY == "你的_DEEPSEEK_API_KEY_填在这里":
        print("❌ 错误：请先在脚本第 30 行填写你的真实 DeepSeek API Key！")
        exit()
        
    print("✨ Amadeus 纯控制台双语流式解析链条初始化成功。")
    
    try:
        ask_amadeus_stream("红莉栖，今晚要不要一起去吃烤肉？")
        time.sleep(1)
        ask_amadeus_stream("别傲娇了，去嘛去嘛。")
        
    except Exception as e:
    
        print(f"💥 发生错误: {e}")
        '''
