# pip install python-dotenv
import os
from dotenv import load_dotenv
load_dotenv()



# SYSTEM LLM:
HISTORY_LIMIT = 20


# AUDIO:
GAIN = 1

# YANDEX SpeechKit:
SAVE_FILE = False # Сохранять аудио файл

# TTS:


# STT:
RATE = 16000
CHUNK = 4096  # размер блока в байтах (примерно 0.25 секунды при 16kHz)
RECORD_SECONDS = 30


# DeepSeek:
MODEL_DS = "deepseek-chat"
TIMEOUT = (5.0, 30.0)


# GPIO:
BUTTON_OFF_PIN = 5   # GPIO5 (физический пин 29)
BUTTON_PIN = 6   # GPIO6 (физический пин 31)


# GET KEYS:
API_DS = str(os.environ.get("key_deepseek"))
YANDEX = str(os.environ.get("yandex"))
SUDO_PASS = str(os.environ.get("sudopass"))









''' 
1. приветстиве
1.1 Привет! Скоро ли уже каникулы?...
1.2 Здрасте, снова села за домашку за 30 минут до отбоя? Серьезно?
1.3 Готов помогать грызть гранит наук, даже если у меня нету зубовююю

2. нет инета
2.1 Подключи меня к интернету, чтобы я работал
2.2 я как и ты, без интеренета ничего не могу
2.3 ты забыла включить раздачу интеренета

3. прощеание
3.1 Удачи на уроках!
3.2 Вырубаюсь. Если что, ты знаешь как меня включить
3.3 Я спать. Надеюсь, ты тоже
4. интернет есть
4.1 Я с интернетом!
4.2 Интеренет подключён! Теперь я умная железка
4.3 Интеренет есть. Начинаем работу!

'''