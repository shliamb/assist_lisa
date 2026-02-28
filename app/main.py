from config import BUTTON_OFF_PIN, BUTTON_PIN, SUDO_PASS
from network import ip
import time
from buttons import status_button
from mod_openai import transcription, get_voice
from deepseek import respons_ds
import subprocess
from display import image 
import threading
from audio import Audio

audio = Audio()




def main() -> None:
    """ Главная функция"""

    flag_ip = 0
    flag_off = 0
    flag_false = 0
    
    audio.play_audio("./wavs/1.wav")

    while True:


        # WORK WHITH IP
        get_ip = ip()
        #print(get_ip)

        if not get_ip:
            #print("wifi is not")
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
            



        # CLICK BUTTON ACTION
        status_hold = status_button(BUTTON_PIN)

        recording_active = audio.get_recording_active()
        record_thread = None

        if status_hold == True and not recording_active:
            image("записываю вопрос,", 5, 10)
            image("говори", 5, 20 )
            audio.change_recording_active(True)
            # name_file = f"record_{int(time.time())}.wav"
            name_file = f"record.wav"
            # Запуск в отдельном потоке
            record_thread = threading.Thread(target=audio.record_audio, args=(name_file,))
            record_thread.start()

        elif status_hold == False and recording_active:
            print("Останавливаю запись...")
            audio.change_recording_active(False)
            if record_thread:
                record_thread.join()
            record_thread = None

            answer_tr = transcription(name_file)
            if not answer_tr:
                print("WTF error")
                return
            
            answer_ds = respons_ds(answer_tr)
            print("answer_ds:", answer_ds)

            name_file = get_voice(answer_ds)

            audio.play_audio(f"./{name_file}", 15)


        time.sleep(0.1)

main()



