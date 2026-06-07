
set "PROJECT_DIR=D:\GPT-SoVITS-v2pro-20250604"
set "PYTHON_EXE=%PROJECT_DIR%\runtime\python.exe"

set "PATH=%PROJECT_DIR%\runtime;%PATH%"
cd /d "%PROJECT_DIR%"

start "TTS_Engine" "%PYTHON_EXE%" -I api_v2.py -a 127.0.0.1 -p 9880

start "Gateway_Server" "%PYTHON_EXE%" -I server.py

timeout /t 15 /nobreak

curl http://127.0.0.1:9880/set_sovits_weights?weights_path=D:\GPT-SoVITS-v2pro-20250604\SoVITS_weights_v2Pro\makise_kurisu_e8_s1192.pth

curl http://127.0.0.1:9880/set_gpt_weights?weights_path=D:\GPT-SoVITS-v2pro-20250604\GPT_weights_v2Pro\makise_kurisu-e15.ckpt

