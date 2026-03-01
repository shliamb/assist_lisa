from config import BUTTON_OFF_PIN, BUTTON_PIN, SUDO_PASS, CACHE_SEC_DISP
from network import Network
import time
from buttons import status_button
from deepseek import DeepSeek
from speechkit import YaSpeechKit
from audio import Audio
import subprocess
import psutil
import os
import gc
# from display import image 
from display import Display
import threading
# from memory import memory_percent_get


speechkit = YaSpeechKit()
audio = Audio()
deepseek = DeepSeek()
display = Display()
net = Network()
process = psutil.Process(os.getpid())



class CachingParameters:
    """ Получение актуальных данных для экрана
        и вывод с временным кэшированием """
    def __init__(self):
        """ Обнуление последних показаний """
        self.last_check = 0 # Время последней проверки
        self.last_level = "" # Последний уровень сети WIFI
        self.last_us_ram = 0 # Последний объем занятой памяти
        self.last_volume = 0 # Последний уровень громкости
        self.cache_sec = CACHE_SEC_DISP # Время кэширования


    def _check_time(self):
        """ Проверка времени кэша """
        now = time.time()
        if now - self.last_check >= CACHE_SEC_DISP:
            self.last_check = now
            return True
        return False
    
    def _clear_last(self):
        """ Сброс последних значений в кэше, что бы снова 
        обновить на экране """
        self.last_check = 0 # Время последней проверки
        self.last_level = "" # Последний уровень сети WIFI
        self.last_us_ram = 0 # Последний объем занятой памяти
        self.last_volume = 0 # Последний уровень громкости
    
    def update_sys_display(self):
        """ Вывод на экран системных параметров с кэшированием """
        if self._check_time():

            """ Вывод уровня сигнала WIFI"""
            level = net.get_signal_cached()
            if self.last_level != level:
                display.add_display_task({"block": "icon", "name": level})
                self.last_level = level


            """ Вывод RAM """
            used_ram = f"{process.memory_info().rss // 1024 // 1024}"
            if self.last_us_ram != used_ram:
                display.add_display_task({"block": "icon", "name": "ram"})
                display.add_display_task({"block": "size_ram", "text": used_ram})
                self.last_us_ram = used_ram

            """ Вывод VOLUME """
            volume = 10
            if self.last_volume != volume:
                display.add_display_task({"block": "icon", "name": "ico_vol"})
                display.add_display_task({"block": "volume", "text": volume})
                self.last_volume = volume

            gc.collect()












def main() -> None:
    """ Главная функция"""

    """ Заупуск основной функции и цикла
        вносится или удаляется из списка цикла вывода экрана
        реакция на кнопки """
    
    cache_param = CachingParameters()




    # #image("█▓▒░ ELIZABET ░▒▓█", 5, 10)
    # display.add_display_task({"block": "line", "text": "█▓▒░ ELIZABET ░▒▓█"})
    # SYSTEMS

    flag_ip = 0
    flag_off = 0
    flag_false = 0
    flag_memory_get = 0
    recording_active = False
    record_thread = None
    
    audio.play_audio("./wavs/1.wav")

    while True:
        ''' Условия с айпи и вай фаем'''
        get_ip = net.get_ip()

        # Вывод на экран системных данных с кешированием
        cache_param.update_sys_display()
        

        if not get_ip:
            #image("вай-фай не подключён", 5, 10)
            display.add_display_task({"block": "line", "text": "вай-фай не подключён"})
            audio.play_audio("./wavs/2.wav")

            flag_ip = 0
            
        elif flag_ip == 0 and get_ip:
            # print(f"ip : {get_ip}")
            audio.play_audio("./wavs/4.wav")
            # image(get_ip, 5, 10)
            # time.sleep(5)
            # # print("end 5 sec")
            # image("    ", 5, 20)
            flag_ip = 1

            '''процент занятости памяти'''

        # memory_percent = memory_percent_get()
        # if flag_memory_get > 20:
        #     #image(f"занято озу {memory_percent}%", 0, 5)
        #     display.add_display_task({"block": "line", "text": f"озу:{memory_percent}%"})
        #     flag_memory_get = 0
        # else:
        #     flag_memory_get += 1

        '''кнопка левая'''

        button_off_status = status_button(BUTTON_OFF_PIN) 

        if button_off_status == True and flag_off > 11 :
            # print("выключаюсь")
            audio.play_audio("./wavs/3.wav")
            #image("выключаюсь(", 5, 20)
            display.add_display_task({"block": "line", "text": "выключаюсь("})

            
            time.sleep(2)
            flag_ip = 0
            flag_off = 0
            #image("    ", 5, 20)
            command = ["sudo", "poweroff"]
            command = ["sudo", "poweroff"]

            proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            proc.communicate(input = SUDO_PASS + "\n", timeout=30)
            proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            proc.communicate(input = SUDO_PASS + "\n", timeout=30)            

        elif flag_off < 10 and flag_false > 0 :
            #image(get_ip, 5, 10)
            display.add_display_task({"block": "line", "text": get_ip})
            #time.sleep(5)
            #image("  ", 5, 10)
            flag_off = 0
            flag_false = 0

        elif button_off_status == True:
            flag_off += 1

        elif flag_off > 1 and button_off_status == False:
            flag_false += 1
            



        ''' кнпока правая со звуком'''
        status_hold = status_button(BUTTON_PIN)

        recording_active = speechkit.get_recording_active()

        if status_hold == True and not recording_active:
            #image("записываю вопрос,", 5, 10)
            #image("ГОВОРИ!", 5, 20 )
            display.add_display_task({"block": "line", "text": "ГОВОРИ!"})
            speechkit.change_recording_active(True)

            # Запуск в отдельном потоке
            record_thread = threading.Thread(target=speechkit.stream_mic_record)
            record_thread.start()

        elif status_hold == False and recording_active:
            time.sleep(2)
            print("Останавливаю запись...")
            speechkit.change_recording_active(False)
            
            if record_thread:
                record_thread.join()

                input_question = speechkit.get_last_transcription()
                print("input_question:", input_question)
                if not input_question:
                    # Звуковая заготовка - Задай вопрос снова, я не разобрал
                    print("Нет транс текста.. ")
                    continue
                
                text_stream_ds = deepseek.stream_llm_response(input_question)
                speechkit.stream_synthesis(text_stream_ds)
                gc.collect()
                record_thread = None



        time.sleep(0.1)

main()



