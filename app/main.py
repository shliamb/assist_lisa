from config import BUTTON_OFF_IP, BUTTON_SPEEK, SUDO_PASS, CACHE_SEC_DISP, I_TURN_OFF
from network import Network
import time
from buttons import Gpio
from deepseek import DeepSeek
from speechkit import YaSpeechKit
from audio import Audio
import subprocess
import psutil
import queue
from display import Display
import threading


button = Gpio()
speechkit = YaSpeechKit()
audio = Audio()
deepseek = DeepSeek()
display = Display()
net = Network()
total = psutil.virtual_memory()
cpu_percent = psutil.cpu_percent(interval=1)

button.on_amp() # Включили усилитель звука, пока так ..

# Очередь событий выставленных ИИ Агентом на исполнение
agent_task_queue = queue.Queue(maxsize=20)


# Приветствие:
display.add_display_task({"block": "line", "text": "█▓▒░ ELIZABET ░▒▓█"})
audio.play_audio("./wavs/1.wav")








def run_tasks_actions():
    """ Обработка задач из очереди агента """
    try:
        task = agent_task_queue.get(timeout=0.1)
        #print(f"[Queue] Получена задача: {task}")
        
        command = task.get("command")
        
        if command == "set_volume":
            volume = task.get('volume')
            #print(f"\nВыполняю: set_volume {volume}")
            if audio.set_gain(volume):
                #print(f"\nВыполнено: set_volume {volume}")
                display.add_display_task({"block": "line", "text": f"set_volume {volume}"})
        
        elif command == "poweroff":
            #print("\nВыполняю: poweroff")
            display.add_display_task({"block": "line", "text": "Выключаюсь.."})
            time.sleep(3)
            display._clear_display()
            subprocess.run(["sudo", "poweroff"])
            return "SHUTDOWN"  # Флаг для выхода из цикла
        
        elif command == "reboot":
            #print("\nВыполняю: reboot")
            display.add_display_task({"block": "line", "text": "reboot"})
            time.sleep(3)
            display._clear_display()
            subprocess.run(["sudo", "reboot"])
            return "REBOOT"
        
        else:
            #print(f"[WARN] Неизвестная команда: {command}")
            display.add_display_task({"block": "line", "text": f"Неизвестная команда {command}"})
        
        agent_task_queue.task_done()
        
    except queue.Empty:
        pass
    
    return "CONTINUE"




class CachingParameters:
    """ Получение актуальных данных для экрана
        и вывод с временным кэшированием """
    def __init__(self):
        """ Обнуление последних показаний """
        self.last_check = 0 # Время последней проверки
        self.last_level = "" # Последний уровень сети WIFI
        self.last_us_ram = 0 # Последний объем занятой памяти
        self.last_volume = 0 # Последний уровень громкости
        self.ip_value = "" # Последнее значение IP адреса
        self.cache_sec = CACHE_SEC_DISP # Время кэширования
        """ Выключение устройства """
        self.i = I_TURN_OFF # Счетчик выключения устройства
        self.turnon_ip_btn = False # Флаг нажата ли кнопка IP

    def get_i(self):
        return self.i
    
    def clear_i(self):
        self.i = I_TURN_OFF

    def counting_i(self):
        self.i -= 1
    
    def get_turnon_ip_btn(self):
        return self.turnon_ip_btn
    
    def change_turnon_ip_btn(self, status):
        self.turnon_ip_btn = status

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
        self.ip_value = "" # Последнее значение IP
    
    def update_sys_display(self):
        """ Вывод на экран системных параметров с кэшированием """
        if self._check_time():

            """ Вывод уровня сигнала WIFI"""
            level = net.get_signal_cached()
            if self.last_level != level:
                display.add_display_task({"block": "icon", "name": level})
                self.last_level = level

            """ Вывод RAM """
            used_ram = total.percent
            if self.last_us_ram != used_ram:
                display.add_display_task({"block": "icon", "name": "ram"})
                display.add_display_task({"block": "size_ram", "text": f"{used_ram}%"})
                self.last_us_ram = used_ram

            """ Вывод VOLUME """
            volume = audio.get_gain()
            if self.last_volume != volume:
                display.add_display_task({"block": "icon", "name": "ico_vol"})
                display.add_display_task({"block": "volume", "text": volume})
                self.last_volume = volume

            """ Проверка IP адреса """
            ip_value = net.get_ip()
            if self.ip_value != ip_value:
                if not ip_value:
                    display.add_display_task({"block": "line", "text": "вай-фай не подключён"})
                    audio.play_audio("./wavs/2.wav")
                elif ip_value:
                    display.add_display_task({"block": "line", "text": "вай-фай подключён"})
                    audio.play_audio("./wavs/4.wav")
                self.ip_value = ip_value

            # print(f"Всего ОЗУ: {total.total // 1024 // 1024} MB")
            # print(f"Свободно ОЗУ: {total.available // 1024 // 1024} MB")
            # print(f"Использовано ОЗУ: {total.percent}%")
            # print(f"Загрузка CPU: {cpu_percent}%")











def main() -> None:

    """ Заупуск основной функции и цикла
        вносится или удаляется из списка цикла вывода экрана
        реакция на кнопки все-все-все.."""
    
    cache_param = CachingParameters()


    # МОИ ЛЮБИМЫЕ ФЛАГИ:
    flag_off = 0
    flag_false = 0
    recording_active = False
    record_thread = None




    while True:

        # Проверка очереди задач агента и выполнение:
        run_tasks_actions()

        # Получаем значения кнопок:
        status_button_ip_off = button.status_button(BUTTON_OFF_IP)
        status_button_speek = button.status_button(BUTTON_SPEEK)

        # Вывод на экран системных данных с кешированием
        cache_param.update_sys_display()



        button_status = cache_param.get_turnon_ip_btn() # Все еще нажата?

        if status_button_ip_off == True and not button_status:
            """ Нажатие кнопки IP и Вывод SSH IP """
            current_ip = f"SSH IP: {net.get_ip()}"
            display.add_display_task({"block": "sys", "text": current_ip})
            cache_param._clear_last()
            time.sleep(3) # Время задержки SSH IP на экране
            display.clear_area(0, 22, 128, 32) # Зачищаю sys
            cache_param.change_turnon_ip_btn(True)

        if status_button_ip_off == True and button_status:
            """ Долго держу кнопку IP """
            i = cache_param.get_i()
            # display.add_display_task({"block": "line", "text": f"Power off after {i}"})
            cache_param.counting_i() # Уменьшение на -1
            if i == 0:
                display.add_display_task({"block": "line", "text": f"выключаюсь("})
                time.sleep(3)
                display._clear_display()
                command = ["sudo", "poweroff"]
                proc = subprocess.Popen(
                    command,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                proc.communicate(input = SUDO_PASS + "\n", timeout=30) 
                break
            time.sleep(0.9)

        if status_button_ip_off == False:
            """ Отжатие кнопки IP """
            cache_param.change_turnon_ip_btn(False)
            cache_param.clear_i()






        # if status_button_ip_off == True and flag_off > 11 :
        #     audio.play_audio("./wavs/3.wav")
        #     display.add_display_task({"block": "line", "text": "выключаюсь("})
        #     time.sleep(2)
        #     command = ["sudo", "poweroff"]

        #     proc = subprocess.Popen(
        #         command,
        #         stdin=subprocess.PIPE,
        #         stdout=subprocess.PIPE,
        #         stderr=subprocess.PIPE,
        #         universal_newlines=True
        #     )
        #     proc.communicate(input = SUDO_PASS + "\n", timeout=30)       

        # elif flag_off < 10 and flag_false > 0 :
        #     ip_value = net.get_ip()
        #     display.add_display_task({"block": "line", "text": f"SSH: {ip_value}"})
        #     flag_off = 0
        #     flag_false = 0

        # elif status_button_ip_off == True:
        #     flag_off += 1

        # elif flag_off > 1 and status_button_ip_off == False:
        #     flag_false += 1
            

        


        ###### ДИАЛОГ ######
        # Забираем состояние флага активной записи
        recording_active = speechkit.get_recording_active()

        # Нажатие кнопки - SPEEK:
        if status_button_speek == True and not recording_active:
            display.add_display_task({"block": "line", "text": "СЛУШАЮ!"})
            speechkit.change_recording_active(True)

            # Запуск в отдельном потоке
            record_thread = threading.Thread(target=speechkit.stream_mic_record)
            record_thread.start()

        # Разжатие кнопки SPEEK:
        elif status_button_speek == False and recording_active:
            time.sleep(2)
            print("Останавливаю запись...")
            speechkit.change_recording_active(False)
            
            if record_thread:
                record_thread.join()

                input_question = speechkit.get_last_transcription()
                print("input_question:", input_question)
                if not input_question:
                    audio.play_audio("./wavs/bormochish.wav")
                    print("Нет транс текста.. ")
                    continue
                
                text_stream_ds = deepseek.stream_llm_response(input_question)
                speechkit.stream_synthesis(text_stream_ds)
                record_thread = None


        time.sleep(0.1)






if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}.")