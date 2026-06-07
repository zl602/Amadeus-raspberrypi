# Amadeus
Why run on raspberrypi? cos I can make a nice-looking portable device that goes into my pocket and take out and show off whenever I want El Psy Kongroo.
An interactive stt-llm-tts Makise Kurisu that runs on Raspberrypi Zero 2W 

Inspired by https://github.com/Kur1oR3iko/AMDS-RE

Failed to train a Japanese piper tts model (which could potentially run on raspberrypi), so tts still relies on requests sent to local inference model which runs on pc. But it's already faster than requesting online api. Tailscale is used for device connection

TTS model: https://github.com/RVC-Boss/GPT-SoVITS tuning done with https://github.com/zl602/Makise_Kurisu_Voice_Source
