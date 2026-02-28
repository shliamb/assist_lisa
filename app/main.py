from config import BUTTON_OFF_PIN, BUTTON_PIN, SUDO_PASS
from network import ip
import time
from buttons import status_button
from deepseek import DeepSeek
from speechkit import YaSpeechKit
import subprocess
from display import image 
import threading
from audio import Audio
from memory import memory_percent_get

speechkit = YaSpeechKit()
audio = Audio()
deepseek = DeepSeek()





def main() -> None:
    """ Главная функция"""

    image("█▓▒░ ELIZABET ░▒▓█", 5, 10)
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
        get_ip = ip()
        

        if not get_ip:
            image("вай-фай не подключён", 5, 10)
            audio.play_audio("./wavs/2.wav")

            flag_ip = 0
            
        elif flag_ip == 0 and get_ip:
            print(f"ip : {get_ip}")
            audio.play_audio("./wavs/4.wav")
            image(get_ip, 5, 10)
            time.sleep(5)
            # print("end 5 sec")
            image("    ", 5, 20)
            flag_ip = 1

            '''процент занятости памяти'''

        memory_percent = memory_percent_get()
        if flag_memory_get > 20:
            image(f"занято озу {memory_percent}%", 0, 5)
            flag_memory_get = 0
        else:
            flag_memory_get += 1

        '''кнопка левая'''

        button_off_status = status_button(BUTTON_OFF_PIN) 

        if button_off_status == True and flag_off > 11 :
            # print("выключаюсь")
            audio.play_audio("./wavs/3.wav")
            image("выключаюсь(", 5, 20)
            time.sleep(2)
            flag_ip = 0
            flag_off = 0
            image("    ", 5, 20)
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
            image(get_ip, 5, 10)
            time.sleep(5)
            image("  ", 5, 10)
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
            image("ГОВОРИ!", 5, 20 )
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
                    # Звуковая заготовка
                    print("Нет транс текста.. ")
                    return
                
                text_stream_ds = deepseek.stream_llm_response(input_question)
                speechkit.stream_synthesis(text_stream_ds)
                record_thread = None



        time.sleep(0.1)

main()



