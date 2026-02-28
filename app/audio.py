import subprocess
import time
import os
from config import GAIN




class Audio:
    def __init__(self):
        pass


    @staticmethod
    def play_audio(filename: str, gain_db=GAIN) -> bool:
        """
            Воспроизведение аудиофайла с усилением через play (sox)
            
            Параметры:
            filename - путь к аудиофайлу для воспроизведения
            gain_db - усиление в дБ (по умолчанию 20)
        """
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


