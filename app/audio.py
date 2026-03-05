import subprocess
import time
import os
from common import percent_to_gain
from config import VOLUME




class Audio:
    def __init__(self):
        self.volume = VOLUME


    def play_audio(self, filename: str) -> bool:
        """
            Воспроизведение аудиофайла с усилением через play (sox)
            
            Параметры:
            filename - путь к аудиофайлу для воспроизведения
            gain_db - усиление в дБ (по умолчанию 20)
        """

        gain_db = percent_to_gain(self.volume)

        # Проверяем, существует ли файл
        if not os.path.exists(filename):
            print(f"Ошибка: файл {filename} не найден")
            return False
        
        # Команда play с усилением
        cmd = ["play", filename, "gain", str(gain_db)]
        
        try:
            print(f"Воспроизведение {filename} с усилением {gain_db} дБ...")
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print("Воспроизведение завершено")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"Ошибка воспроизведения: {e}")
            print(f"stderr: {e.stderr}")
            return False
        
        except FileNotFoundError:
            print("Ошибка: play не найден. Установите sox: sudo apt install sox")
            return False
        
    def get_volume(self):
        return int(self.volume)
    
    def set_volume(self, value: int):
        self.volume = value








# В alsamixer обычно два разных регулятора для микрофона:

# Capture (запись) — то, что попадает в файл.

# Playback (мониторинг) — то, что идёт сразу в динамик (прямой мониторинг).

# Тебе нужно:

# Найти канал "Mic" или "Mic Playback".

# Опустить его громкость или выключить (нажать m).

# Capture при этом останется нетронутым — запись продолжится.