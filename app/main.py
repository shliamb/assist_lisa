from config import BUTTON_OFF_IP, BUTTON_SPEEK, SUDO_PASS, CACHE_SEC_DISP, I_TURN_OFF
from network import Network
import time
from buttons import Gpio
from deepseek import DeepSeek
from speechkit import YaSpeechKit
from audio import Audio
import subprocess
import psutil
import json
import queue
from display import Display
import threading

display = Display()
button = Gpio()
speechkit = YaSpeechKit(display)
audio = Audio()
deepseek = DeepSeek()
net = Network()
total = psutil.virtual_memory()
cpu_percent = psutil.cpu_percent(interval=1)

button.on_amp() # Включили усилитель звука, пока так ..

# Очередь событий выставленных ИИ Агентом на исполнение
agent_task_queue = queue.Queue(maxsize=20)
record_thread = None


# Приветствие:
display.add_display_task({"block": "line", "text": "█▓▒░ ELIZABET ░▒▓█"})
audio.play_audio("./wavs/1.wav")
#speechkit.stream_synthesis("ООО приветики, пистолетики")








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
        # self.ip_value = "" # Последнее значение IP
    
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
                    display.add_display_task({"block": "line", "text": "ИИ: вай-фай не подключён"})
                    audio.play_audio("./wavs/2.wav")
                elif ip_value:
                    display.add_display_task({"block": "line", "text": "ИИ: вай-фай подключён"})
                    audio.play_audio("./wavs/4.wav")
                self.ip_value = ip_value

            # print(f"Всего ОЗУ: {total.total // 1024 // 1024} MB")
            # print(f"Свободно ОЗУ: {total.available // 1024 // 1024} MB")
            # print(f"Использовано ОЗУ: {total.percent}%")
            # print(f"Загрузка CPU: {cpu_percent}%")




def worker_ds(intent, input_question):

    #
    agent = "general_agent"
    system, tools = deepseek.get_tools(agent)

    # Извлекаем роутинг вне условия для лучшей читаемости
    router_result = deepseek.hybrid_router(input_question)

    intent = router_result.get("intent", "CHAT")  # Значение по умолчанию
    display.add_display_task({"block": "line", "text": f"ИИ: {intent}"})


    try:
        if intent == "ACTION":
            # Обработка ACTION с tools
            stream_events = deepseek.refine_stream_tools(
                question=input_question,
                system=system,
                tools=tools
            )
            
            for event in stream_events:
                event_type = event.get('type')
                
                if event_type == 'text':
                    content = event.get('content', '')
                    if content:
                        # Визуальный вывод (опционально)
                        print(content, end='', flush=True)

                        #speechkit.stream_synthesis(content)
                        yield {'type': 'text', 'content': content}

                        # tp.add_to_buffer(content)
                        # process_tts_buffer(force_flush=False)
                
                elif event_type == 'tool':
                    # # Завершаем текущую озвучку перед выполнением инструмента
                    # process_tts_buffer(force_flush=True)
                    
                    tool_data = event.get('data', {})
                    for tool_id, tool_info in tool_data.items():
                        try:
                            # Безопасный парсинг аргументов
                            args = json.loads(tool_info.get('arguments', '{}'))
                            tool_name = tool_info.get('name', '')
                            
                            if tool_name:
                                answer = ""
                                # Вызываем функцию и добавляем задачу в очередь
                                result_function = deepseek.call_function(tool_name, args)

                                if result_function.get("queue"):
                                    agent_task_queue.put(result_function) # В очередь таск на выполнение
                                    print(f"[ACTION] Добавлена задача в очередь: {tool_name}({args})")
                                    answer = "Просьба выполнена"
                                elif not result_function.get("queue"):
                                    answer = result_function.get("value", "Данных нет")
                                else:
                                    answer = "Ошибка, функция настроена не верно"

                                # В очередь на озвучку
                                # Будет ошибка, ждет генератор..
                                print(answer)

                                #speechkit.stream_synthesis(answer)
                                yield {'type': 'text', 'content': answer}

                                # clear_answer = tp.auto_process(answer)
                                # answer_llm_queue.put(clear_answer)
                                # # Сохраняю диалог tools
                                # ds._add_dialog(question=answer_stt, answer=answer)

                        except json.JSONDecodeError as e:
                            print(f"[ERROR] Ошибка парсинга JSON аргументов: {e}")
                        except Exception as e:
                            print(f"[ERROR] Ошибка обработки tool: {e}")
                
                elif event_type == 'usage':
                    #process_tts_buffer(force_flush=True)
                    usage_data = event.get('data', {})
                    #print(f"[USAGE] Статистика: {usage_data}")
                
                elif event_type == 'error':
                    # Обработка ошибок из стрима
                    error_msg = event.get('content', 'Неизвестная ошибка')
                    print(f"[ERROR]: Ошибка в стриме: {error_msg}")
                    # Можно добавить fallback ответ
                    display.add_display_task({"block": "line", "text": "[ERROR]: Произошла ошибка при обработке запроса."})
                    #tp.add_to_buffer("[ERROR]: Произошла ошибка при обработке запроса.")
                    #process_tts_buffer(force_flush=True)
        
        else:  # CHAT или любой другой intent
            # Обработка обычного чата без tools
            return deepseek.stream_llm_response(input_question)
            #speechkit.stream_synthesis(text_stream_ds)


    except Exception as e:
        print(f"[ERROR] Критическая ошибка в основном цикле: {e}")
        # Fallback ответ при критической ошибке
        display.add_display_task({"block": "line", "text": "Произошла системная ошибка."})








def main() -> None:

    """ Заупуск основной функции и цикла
        вносится или удаляется из списка цикла вывода экрана
        реакция на кнопки все-все-все.."""
    
    cache_param = CachingParameters()






    while True:

        # Проверка очереди задач агента и выполнение:
        run_tasks_actions()

        # Получаем значения кнопок:
        status_button_ip_off = button.status_button(BUTTON_OFF_IP)
        status_button_speek = button.status_button(BUTTON_SPEEK)

        # Вывод на экран системных данных с кешированием
        cache_param.update_sys_display()




        if status_button_ip_off == True and not cache_param.get_turnon_ip_btn():
            """ Нажатие кнопки IP и Вывод SSH IP """
            current_ip = f"SSH IP: {net.get_ip()}"
            display.add_display_task({"block": "sys", "text": current_ip})
            cache_param._clear_last()
            time.sleep(3) # Время задержки SSH IP на экране
            display.clear_area(0, 22, 128, 32) # Зачищаю sys
            cache_param.change_turnon_ip_btn(True)

        elif status_button_ip_off == True and cache_param.get_turnon_ip_btn():
            """ Долго держу кнопку IP для выключения """
            i = cache_param.get_i()
            display.add_display_task({"block": "line", "text": f"ИИ: Выключусь через {i}"})
            cache_param.counting_i() # Уменьшение на -1
            if i == 0:
                display.add_display_task({"block": "line", "text": f"ИИ: Выключаюсь("})
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

        elif status_button_ip_off == False:
            """ Отжатие кнопки IP """
            cache_param.change_turnon_ip_btn(False)
            cache_param.clear_i()





        if status_button_speek == True and not speechkit.get_recording_active():
            """ Нажатие кнопки - SPEEK """
            display.add_display_task({"block": "line", "text": "ИИ: СЛУШАЮ!"})
            speechkit.change_recording_active(True)

            # Запуск в отдельном потоке
            record_thread = threading.Thread(target=speechkit.stream_mic_record)
            record_thread.start()


        elif status_button_speek == False and speechkit.get_recording_active():
            """ Разжатие кнопки SPEEK """
            time.sleep(2)
            print("Останавливаю запись...")
            speechkit.change_recording_active(False)
            
            if record_thread:
                record_thread.join()

                # Транскрибация голоса
                input_question = speechkit.get_last_transcription()
                # print("input_question:", input_question)
                if not input_question:
                    audio.play_audio("./wavs/bormochish.wav")
                    display.add_display_task({"block": "line", "text": "ИИ: Не разобрал!"})
                    # print("Нет транскрибированного текста.. ")
                    continue
                

                # Текст вопроса транскрибирован
                display.add_display_task({"block": "line", "text": f"Я: {input_question}"})

                # 
                # agent = "general_agent"
                # system, tools = deepseek.get_tools(agent)

                # # Извлекаем роутинг вне условия для лучшей читаемости
                # router_result = deepseek.hybrid_router(input_question)
                # #print(f"\nRouter Intent: {router_result}")
                # intent = router_result.get("intent", "CHAT")  # Значение по умолчанию
                # display.add_display_task({"block": "line", "text": f"ИИ: {intent}"})














                text_stream_ds = worker_ds(input_question)

                #text_stream_ds = deepseek.stream_llm_response(input_question)


                speechkit.stream_synthesis(text_stream_ds)


                record_thread = None


        time.sleep(0.1)









if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}.")












































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