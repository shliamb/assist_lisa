import os
import time
import psutil
import json
import queue
import subprocess
import threading
from display import Display
from voice import VoiceSTT
from gpio import Gpio
from silero_tts import SileroTTS
from model_deepseek import DeepSeek
from network import Network
from text_utils import TextProcessing
from config import SAMPLE_RATE, CACHE_SEC_DISP, I_TURN_OFF


display = Display()
display.add_display_task({"block": "line", "text": "Загружаю библиотеки.."})
net = Network()
gpio = Gpio()
process = psutil.Process(os.getpid())

recorder = VoiceSTT()
silero = SileroTTS()
ds = DeepSeek()
tp = TextProcessing()

display.add_display_task({"block": "line", "text": "Готова к работе.."})


# recorder = None
# silero = None
# ds = None
# tp = None


# Очередь очищеных предложений от стрима LLM на синтезирование TTS
answer_llm_queue = queue.Queue(maxsize=20)
# Очередь из WAV голосовых озвученных файлов на воспроизведение
audio_queue = queue.Queue(maxsize=20)
# Очередь событий выставленных ИИ Агентом на исполнение
agent_task_queue = queue.Queue(maxsize=20)
# Флаг
stop_all = threading.Event()







def process_tts_buffer(force_flush=False):
    """ Собирает предложения из слов и Кидает в очередь """
    buffer_list: list = tp.read_buffer()
    buffer_str: str = tp.get_text_buffer()

    if not buffer_str: return

    # Если форсируем (Tool или Usage) — отдаем всё без остатка
    if force_flush:
        #print(f"\n[FORCE SEND TEXT queue]: '{buffer_str}'")
        display.add_display_task({"block": "line", "text": f"{buffer_str}"})
        answer_llm_queue.put(buffer_str)
        tp.clear_buffer() # Очистка буфера
        return

    # Ищет с конца знаки припинания, нашел - с него 
    # забирает все, хвост оставляет в буфере для следующих чанок.
    delimiters = frozenset("!?.\n")
    last_sep_index = -1
    for i in range(len(buffer_list) - 1, -1, -1):
        if buffer_list[i] in delimiters:
            last_sep_index = i
            break
    
    if last_sep_index != -1:
        chunk = "".join(buffer_list[:last_sep_index+1])
        buffer_list = buffer_list[last_sep_index+1:]
        #print(f"\n[SENT TEXT queue]: '{chunk}'")
        display.add_display_task({"block": "line", "text": f"{chunk}"})
        answer_llm_queue.put(chunk)
        tp.clear_buffer()
        tp.add_to_buffer(buffer_list)




# Поток синтеза речи
def tts_worker() -> None:
    """ Отдельный поток синтеза речи из очереди в очередь на воспроизведение """
    #print("Отдельный Поток Синтеза речи запущен")
    while not stop_all.is_set():
        try:
            # Ждем текст из очереди
            text_chunk = answer_llm_queue.get(timeout=0.5)
            if text_chunk is None:
                #print("🗑 Удалил None из очереди answer_llm_queue и вышел")
                answer_llm_queue.task_done()
                break
                
            #print(f"\nСинтезирую: {text_chunk}") # {text_chunk[:30]}
            #display.add_display_task({"block": "line", "text": f"[SINTEZ]: {text_chunk}"})
            
            # Синтез речи
            audio = silero.tts_to_ram(text_chunk)
            if audio is not None:
                # Кладем в очередь аудио
                audio_queue.put(audio)
                #print(f"\nАудио готово, в очереди всего: {audio_queue.qsize()}")
                
            answer_llm_queue.task_done()
            
        except queue.Empty:
            continue
        except Exception as e:
            #print(f"Ошибка синтеза: {e}")
            continue
    
    #print("Поток Синтеза речи остановлен")




# Поток воспроизведения
def playback_worker() -> None:
    """ Отдельный поток на воспроизведение из очереди """
    #print("Отдельный Поток Воспроизведения запущен")
    while not stop_all.is_set():
        try:
            # Ждем аудио из очереди
            #print("Жду аудио из очереди...")
            audio_data = audio_queue.get(timeout=0.5)
            #print(f"Получил аудио, тип: {type(audio_data)}")
            if audio_data is None:
                #print("🗑 Удалил None из очереди audio_queue и вышел")
                audio_queue.task_done()
                break
                
            #print(f"Воспроизвожу (в очереди всего: {audio_queue.qsize()})")
            
            time.sleep(0.02)
            #print("Начинаю play_ram...")
            
            success = recorder.play_ram(audio_data=audio_data, sample_rate=SAMPLE_RATE)
            
            #print("play_ram завершен")
            time.sleep(0.02)
            
            audio_queue.task_done()
            #print(f"Воспроизведено, task_done вызван")
            time.sleep(0.02)

            # if success:
            #     print(f"Воспроизведено успешно")
            # else:
            #     print(f"⚠ Воспроизведение не удалось")

            # print(f"Очередь текста: {answer_llm_queue.qsize()}")
            # print(f"Очередь аудио: {audio_queue.qsize()}")
            
        except queue.Empty:
            continue
        except Exception as e:
            print(f"КРИТИЧЕСКАЯ ОШИБКА воспроизведения: {e}")
            import traceback
            traceback.print_exc() # Для отладки
            try:
                gpio.off_amp()
            except:
                pass
            # ВСЕГДА вызываем task_done даже при ошибке!
            try:
                audio_queue.task_done()
            except:
                pass
            # НЕ выходим из цикла - продолжаем работу
            continue
    
    #print("Поток Воспроизведения остановлен")



def run_voice_assistant():
    """ Запуск основной цепочки при откускании кнопки: 
        голос user -> в текст онлайн (STT) VOSK 44mb
        текст -> в роутер классификатор (эврестический, 
        если не определил на нужном уровне, то отдельно 
        обращается к LLM и получает Json ответ) результатом которого будет 
        определение к LLM TEXT или к LLM TOOLS обратиться
        текст(классифицированный) -> в LLM и -> возвращается stream ответ + tools + used
        по мере получения из стрима текстовых блоков похожих на строку
        чанки текста в отдельном потоке передаются на синтез речи и возвращаются в очередь
        LLM text chank -> TTS chank sinteze SILERO -> queue
        в отдельном потоке воспроизводиться звук WAV из очереди
        тем самым воспроизведение неприрывно, на низком качестве 8khz, ввиду железа"""
    
    answer_stt = recorder.stop_recording() # Vosk local
    #print(f"Я: {answer_stt}")
    display.add_display_task({"block": "line", "text": f"{answer_stt}"})

    if not answer_stt:
        #print("Error: пустая транскрибация")
        display.add_display_task({"block": "line", "text": "Не распознала.."})
        return False

    # Запускаем рабочие потоки
    stop_all.clear()
    tts_thread = threading.Thread(target=tts_worker, daemon=True)
    playback_thread = threading.Thread(target=playback_worker, daemon=True)
    
    tts_thread.start()
    playback_thread.start()
    time.sleep(0.1)  # Даем потокам запуститься

    # Получаем поток чанков от LLM
    agent = "general_agent"
    system, tools = ds.get_tools(agent)

    gpio.on_amp() # Включаю усилитель

    #print(f"Получаю ответ от агента: {agent}")


    # Извлекаем роутинг вне условия для лучшей читаемости
    router_result = ds.hybrid_router(answer_stt)
    #print(f"\nRouter Intent: {router_result}")
    intent = router_result.get("intent", "CHAT")  # Значение по умолчанию
    display.add_display_task({"block": "line", "text": f"{intent}"})


    try:
        if intent == "ACTION":
            # Обработка ACTION с tools
            stream_events = ds.refine_stream_tools(
                question=answer_stt,
                system=system,
                tools=tools
            )
            
            for event in stream_events:
                event_type = event.get('type')
                
                if event_type == 'text':
                    content = event.get('content', '')
                    if content:
                        # Визуальный вывод (опционально)
                        # print(content, end='', flush=True)
                        
                        tp.add_to_buffer(content)
                        process_tts_buffer(force_flush=False)
                
                elif event_type == 'tool':
                    # Завершаем текущую озвучку перед выполнением инструмента
                    process_tts_buffer(force_flush=True)
                    
                    tool_data = event.get('data', {})
                    for tool_id, tool_info in tool_data.items():
                        try:
                            # Безопасный парсинг аргументов
                            args = json.loads(tool_info.get('arguments', '{}'))
                            tool_name = tool_info.get('name', '')
                            
                            if tool_name:
                                answer = ""
                                # Вызываем функцию и добавляем задачу в очередь
                                result_function = ds.call_function(tool_name, args)

                                if result_function.get("queue"):
                                    agent_task_queue.put(result_function) # В очередь таск на выполнение
                                    #print(f"[ACTION] Добавлена задача в очередь: {tool_name}({args})")
                                    answer = "Просьба выполнена"
                                elif not result_function.get("queue"):
                                    answer = result_function.get("value", "Данных нет")
                                else:
                                    answer = "Ошибка, функция настроена не верно"

                                # В очередь на озвучку
                                clear_answer = tp.auto_process(answer)
                                answer_llm_queue.put(clear_answer)
                                # Сохраняю диалог tools
                                ds._add_dialog(question=answer_stt, answer=answer)

                        except json.JSONDecodeError as e:
                            print(f"[ERROR] Ошибка парсинга JSON аргументов: {e}")
                        except Exception as e:
                            print(f"[ERROR] Ошибка обработки tool: {e}")
                
                elif event_type == 'usage':
                    process_tts_buffer(force_flush=True)
                    usage_data = event.get('data', {})
                    #print(f"[USAGE] Статистика: {usage_data}")
                
                elif event_type == 'error':
                    # Обработка ошибок из стрима
                    error_msg = event.get('content', 'Неизвестная ошибка')
                    print(f"[ERROR]: Ошибка в стриме: {error_msg}")
                    # Можно добавить fallback ответ
                    tp.add_to_buffer("[ERROR]: Произошла ошибка при обработке запроса.")
                    process_tts_buffer(force_flush=True)
        
        else:  # CHAT или любой другой intent
            # Обработка обычного чата без tools
            stream_events = ds.refine_stream(
                question=answer_stt,
                system=system
            )
            
            for event in stream_events:
                event_type = event.get('type')
                
                if event_type == 'text':
                    content = event.get('content', '')
                    if content:
                        # Визуальный вывод (опционально)
                        # print(content, end='', flush=True)
                        
                        tp.add_to_buffer(content)
                        process_tts_buffer(force_flush=False)
                
                elif event_type == 'usage':
                    process_tts_buffer(force_flush=True)
                    usage_data = event.get('data', {})
                    #print(f"[USAGE] Статистика: {usage_data}")
                
                elif event_type == 'error':
                    # Обработка ошибок
                    error_msg = event.get('content', 'Неизвестная ошибка')
                    print(f"[ERROR] Ошибка в стриме: {error_msg}")
                    tp.add_to_buffer("Извините, произошла ошибка.")
                    process_tts_buffer(force_flush=True)
        
        # Гарантируем завершение озвучки в конце обработки
        process_tts_buffer(force_flush=True)

    except Exception as e:
        print(f"[ERROR] Критическая ошибка в основном цикле: {e}")
        # Fallback ответ при критической ошибке
        tp.add_to_buffer("Произошла системная ошибка.")
        process_tts_buffer(force_flush=True)



    # print("Весь текст от LLM получен и добавлен в очередь")
    # print(f"Размер очереди: {answer_llm_queue.qsize()}")


    # Ждем пока текстовые чанки обработаются
    answer_llm_queue.join()
    #print("Весь текст синтезирован")
    
    # Ждем пока аудио воспроизведутся
    audio_queue.join()
    #print("Всё аудио воспроизведено")
    
    # Останавливаем потоки
    stop_all.set()

    
    # Даем время на завершение
    tts_thread.join(timeout=2)
    playback_thread.join(timeout=2)
    
    gpio.off_amp()
    #print("Обработка завершена")
    display.add_display_task({"block": "line", "text": "Процесс завершён. Ожидание..."})
    
    

    
    silero.clear_tts()

    return True




def run_tasks_actions():
    """ Обработка задач из очереди агента """
    try:
        task = agent_task_queue.get(timeout=0.1)
        #print(f"[Queue] Получена задача: {task}")
        
        command = task.get("command")
        
        if command == "set_volume":
            volume = task.get('volume')
            #print(f"\nВыполняю: set_volume {volume}")
            if recorder.set_volume(volume):
                #print(f"\nВыполнено: set_volume {volume}")
                display.add_display_task({"block": "line", "text": f"set_volume {volume}"})
        
        elif command == "poweroff":
            #print("\nВыполняю: poweroff")
            display.add_display_task({"block": "line", "text": "Good by bro.."})
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
            volume = recorder.get_value_volume()
            if self.last_volume != volume:
                display.add_display_task({"block": "icon", "name": "ico_vol"})
                display.add_display_task({"block": "volume", "text": volume})
                self.last_volume = volume
















def main():

    """ Заупуск основной функции и цикла
        вносится или удаляется из списка цикла вывода экрана
        реакция на кнопки """
    
    cache_param = CachingParameters()

    while True:

        # Проверка очереди задач и выполнение
        run_tasks_actions()

        # Получаем значения кнопок в 0.1 сек
        btnip = gpio.button_ip_status()
        btn2 = gpio.button_speek_status()

        # Вывод на экран системных данных с кешированием
        cache_param.update_sys_display()


        button_status = cache_param.get_turnon_ip_btn() # Все еще нажата?

        if btnip == 0 and not button_status:
            """ Нажатие кнопки IP и Вывод SSH IP """
            current_ip = f"SSH IP: {net.get_current_ip()}"
            display.add_display_task({"block": "sys", "text": current_ip})
            cache_param._clear_last()
            time.sleep(3) # Время задержки SSH IP на экране
            display.clear_area(0, 22, 128, 32) # Зачищаю sys
            cache_param.change_turnon_ip_btn(True)

        if btnip == 0 and button_status:
            """ Долго держу кнопку IP """
            i = cache_param.get_i()
            display.add_display_task({"block": "line", "text": f"Power off after {i}"})
            cache_param.counting_i() # Уменьшение на -1
            if i == 0:
                display.add_display_task({"block": "line", "text": f"Good by bro.."})
                time.sleep(3)
                display._clear_display()
                subprocess.run(["sudo", "poweroff"])
                break
            time.sleep(0.9)

        if btnip == 1:
            """ Отжатие кнопки IP """
            cache_param.change_turnon_ip_btn(False)
            cache_param.clear_i()

        if btn2 == 0 and recorder.recording_process is None:
            """ Начало записи голоса"""
            display.add_display_task({"block": "line", "text": "Гавари давай !!!"})
            recorder.start_recording()

        if btn2 == 1 and recorder.recording_process:
            """ Конец записи и запуск ответа """
            display.add_display_task({"block": "line", "text": "Шас отвечу.. пагади.."})
            run_voice_assistant()



        time.sleep(0.1)





if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}.")















