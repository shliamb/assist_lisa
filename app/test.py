





# import psutil
# # import os

# # process = psutil.Process(os.getpid())
# # used_mb = process.memory_info().rss // 1024 // 1024

# # total_mb = psutil.virtual_memory().total // 1024 // 1024
# # percent = (used_mb / total_mb) * 100

# # print(f"Занято: {used_mb} MB / {total_mb} MB ({percent:.1f}%)")





# # process = psutil.Process()
# # mem_info = process.memory_info()

# # print(f"RSS: {mem_info.rss / 1024 / 1024:.1f} MB")      # физическая память
# # print(f"VMS: {mem_info.vms / 1024 / 1024:.1f} MB")      # виртуальная память (включая swap, библиотеки)


# total = psutil.virtual_memory()
# print(f"Всего: {total.total // 1024 // 1024} MB")
# print(f"Свободно: {total.available // 1024 // 1024} MB")
# print(f"Использовано: {total.percent}%")









# Да, продуманно. Кэш вынесен наружу — правильно.

# Ошибка именно в том, что вы возвращаете None из _get_signal_raw(), а get_signal_cached() его не проверяет.

# Достаточно добавить в начало get_signal_cached():

# python
# if signal is None:
#     return 'no_signal'
# Или обработать None в _get_signal_raw(), возвращая -100.


# if signal is None:
#     return 'no_signal'  # или 0, или 'unknown'























# from deepseek import DeepSeek
# from speechkit import YaSpeechKit



# deepseek = DeepSeek()
# speechkit = YaSpeechKit()




# def main():
#     # while True:

#     # DEEPSEEK:
#     #     print("Введите вопрос:")
#     #     input_text = input()
#     #     text_stream = deepseek.stream_llm_response(input_text)  # генератор

#     # SINTEZ:
#     text_stream = "Да что ты там бормочишь под нос .. повтори четко!"
#     speechkit.stream_synthesis(text_stream)      # передаём и озвучиваем

#     # MIC:
#     # resut = speechkit.stream_mic_record()
#     # print("resut:", resut)


# main()








# try:
#     for r in it:
#         event_type, alternatives = r.WhichOneof('Event'), None
        
#         if event_type == 'partial':
#             # промежуточные - игнорируем для финала
#             pass
                    
#         elif event_type == 'final':
#             # финал после паузы - пока не используем
#             pass
                    
#         elif event_type == 'final_refinement':
#             # ТОЛЬКО ЭТО БЕРЁМ
#             alternatives = [a.text for a in r.final_refinement.normalized_text.alternatives]
#             current_phrase = alternatives[0]
#             print(f'refined: {current_phrase}')
            
#             # Сразу добавляем в список, т.к. это готовая фраза
#             phrases.append(current_phrase.strip())
#             current_phrase = ""  # сбрасываем
            
#     return phrases  # возвращаем все фразы


# def run():
#     final_text = []  # список для всех фраз
    
#     # ... код ...
    
#     if event_type == 'final':
#         text = alternatives[0]
#         final_text.append(text)  # добавляем фразу
#         print(f'\nfinal: {text}')
    
#     # ... в конце функции ...
#     full_result = ' '.join(final_text)  # склеиваем через пробел
#     print(f"\nИТОГ: {full_result}")
#     return full_result





# def run_stt(self):
#     phrases = []  # список для всех фраз
    
#     for r in it:
#         if event_type == 'final':
#             text = alternatives[0]
#             phrases.append(text)
#             print(f'фраза: {text}')
        
#         if event_type == 'final_refinement':
#             text = alternatives[0]
#             phrases[-1] = text  # заменяем последнюю фразу на уточнённую
    
#     # После отпускания кнопки (когда стрим закончился)
#     full_text = ' '.join(phrases)
#     return full_text




# import subprocess
# import sys
# import grpc
# import yandex.cloud.ai.stt.v3.stt_pb2 as stt_pb2
# import yandex.cloud.ai.stt.v3.stt_service_pb2_grpc as stt_service_pb2_grpc
# from config import YANDEX

# # Настройки распознавания
# RATE = 16000
# CHUNK = 4096  # размер блока в байтах (примерно 0.25 секунды при 16kHz)
# RECORD_SECONDS = 30

# def gen():
#     # Настройки распознавания
#     recognize_options = stt_pb2.StreamingOptions(
#         recognition_model=stt_pb2.RecognitionModelOptions(
#             audio_format=stt_pb2.AudioFormatOptions(
#                 raw_audio=stt_pb2.RawAudio(
#                     audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
#                     sample_rate_hertz=RATE,
#                     audio_channel_count=1
#                 )
#             ),
#             text_normalization=stt_pb2.TextNormalizationOptions(
#                 text_normalization=stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_ENABLED,
#                 profanity_filter=False,
#                 literature_text=False
#             ),
#             language_restriction=stt_pb2.LanguageRestrictionOptions(
#                 restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
#                 language_code=['ru-RU']
#             ),
#             audio_processing_type=stt_pb2.RecognitionModelOptions.REAL_TIME
#         )
#     )

#     # Отправляем настройки
#     yield stt_pb2.StreamingRequest(session_options=recognize_options)

#     # Запускаем arecord и читаем из stdout
#     cmd = [
#         "arecord",
#         "-f", "S16_LE",      # 16 бит
#         "-c", "1",           # моно
#         "-r", str(RATE),     # частота
#         "-t", "raw",         # raw формат, без заголовков
#         "-D", "default"      # устройство по умолчанию
#     ]
    
#     process = subprocess.Popen(
#         cmd,
#         stdout=subprocess.PIPE,
#         stderr=subprocess.DEVNULL,
#         bufsize=CHUNK
#     )
    
#     print("recording")
    
#     # Читаем данные и отправляем
#     bytes_per_second = RATE * 2  # 16 бит = 2 байта на сэмпл
#     total_bytes = bytes_per_second * RECORD_SECONDS
#     bytes_read = 0
    
#     while bytes_read < total_bytes:
#         data = process.stdout.read(CHUNK)
#         if not data:
#             break
#         yield stt_pb2.StreamingRequest(chunk=stt_pb2.AudioChunk(data=data))
#         bytes_read += len(data)
    
#     print("finished")
    
#     # Завершаем процесс записи
#     process.terminate()

# def run():
#     final_text = ""  # здесь будем собирать финальный текст
    
#     # Установите соединение с сервером
#     cred = grpc.ssl_channel_credentials()
#     channel = grpc.secure_channel('stt.api.cloud.yandex.net:443', cred)
#     stub = stt_service_pb2_grpc.RecognizerStub(channel)

#     # Отправьте данные для распознавания
#     it = stub.RecognizeStreaming(gen(), metadata=(
#         ('authorization', f'Api-Key {YANDEX}'),
#     ))

#     # Обработайте ответы сервера
#     try:
#         for r in it:
#             event_type, alternatives = r.WhichOneof('Event'), None
#             if event_type == 'partial' and len(r.partial.alternatives) > 0:
#                 alternatives = [a.text for a in r.partial.alternatives]
#                 # выводим промежуточные результаты
#                 print(f'partial: {alternatives[0]}', end='\r')
                
#             if event_type == 'final':
#                 alternatives = [a.text for a in r.final.alternatives]
#                 final_text = alternatives[0]
#                 print(f'\nfinal: {final_text}')
                
#             if event_type == 'final_refinement':
#                 alternatives = [a.text for a in r.final_refinement.normalized_text.alternatives]
#                 final_text = alternatives[0]
#                 print(f'refined: {final_text}')
                
#     except grpc._channel._Rendezvous as err:
#         print(f'Error code {err._state.code}, message: {err._state.details}')
#         raise err
    
#     return final_text

# # Использование
# if __name__ == "__main__":
#     result = run()
#     print(f"\nИтоговый текст: {result}")














# import wave

# # Открываем файл для записи ДО цикла
# wav_file = wave.open("synthesized.wav", 'wb')
# wav_file.setnchannels(1)  # моно
# wav_file.setsampwidth(2)  # 16 бит = 2 байта
# wav_file.setframerate(16000)  # частота

# # Получаем и сразу воспроизводим аудио
# for response in stub.StreamSynthesis(request_generator(), metadata=auth_meta):
#     try:
#         if response.audio_chunk.data:
#             # Воспроизводим
#             play_process.stdin.write(response.audio_chunk.data)
#             play_process.stdin.flush()
            
#             # Сохраняем в файл
#             wav_file.writeframes(response.audio_chunk.data)
            
#         if response.text_chunk.text:
#             print("Озвучивается:", response.text_chunk.text)
#     except Exception as e:
#         print(f"Ошибка при обработке ответа: {e}")

# # Закрываем файл после цикла
# wav_file.close()







# import subprocess

# # Запускаем play с чтением из stdin
# play_process = subprocess.Popen(
#     ["play", "-t", "wav", "-", "gain", "20"],
#     stdin=subprocess.PIPE
# )

# # В цикле получения чанков
# for response in stub.StreamSynthesis(request_generator(), metadata=auth_meta):
#     if response.audio_chunk.data:
#         play_process.stdin.write(response.audio_chunk.data)
#         play_process.stdin.flush()  # важно!

# # Закрываем и ждём
# play_process.stdin.close()
# play_process.wait()




# import subprocess
# import tempfile

# # Вместо всего PyAudio делаем так:
# audio_data = b"".join(audio_chunks)  # если собираешь чанки

# with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
#     f.write(audio_data)
#     temp_file = f.name

# # Воспроизводим с усилением 20dB
# subprocess.run(["play", temp_file, "gain", "20"])

# # Удаляем временный файл
# import os
# os.unlink(temp_file)




# if any(p in chunk['content'] for p in ['.', '!', '?']):
#     # конец предложения — отдаём всё
#     self.buffer += chunk['content']
#     print("буфер (конец):", self.buffer)
#     # yield ...
#     self.buffer = ""
# elif chunk['content'] in [',', ' ']:
#     # знак или пробел — пока копим
#     self.buffer += chunk['content']
# else:
#     # слово — копим
#     self.buffer += chunk['content']







# import pyaudio
# import wave
# import io

# def stream_synthesis_and_play(text_stream, api_key):
#     """
#     text_stream - генератор, выдающий текст частями (например, из DeepSeek)
#     api_key - API ключ Yandex SpeechKit
#     """
#     cred = grpc.ssl_channel_credentials()
#     auth_meta = (('authorization', f'Api-key {api_key}'),)
    
#     # Настройки аудио для воспроизведения
#     CHUNK = 1024
#     FORMAT = pyaudio.paInt16
#     CHANNELS = 1
#     RATE = 16000
    
#     p = pyaudio.PyAudio()
#     stream = p.open(format=FORMAT,
#                     channels=CHANNELS,
#                     rate=RATE,
#                     output=True,
#                     frames_per_buffer=CHUNK)
    


    
#     with grpc.secure_channel('tts.api.cloud.yandex.net:443', cred) as channel:
#         stub = tts_service_pb2_grpc.SynthesizerStub(channel)
        
#         # Настройки синтеза
#         synthesis_options = tts_pb2.SynthesisOptions(
#             voice="masha",
#             role="good",
#             output_audio_spec=tts_pb2.AudioFormatOptions(
#                 raw_audio=tts_pb2.RawAudio(
#                     audio_encoding=tts_pb2.RawAudio.LINEAR16_PCM,
#                     sample_rate_hertz=RATE
#                 )
#             )
#         )
        
#         # Генератор запросов
#         def request_generator():
#             yield tts_pb2.StreamSynthesisRequest(options=synthesis_options)
            
#             # Отправляем текст частями из DeepSeek
#             for text_chunk in text_stream:
#                 if text_chunk:
#                     # Важно: добавляем пробел в конце, чтобы не склеивалось
#                     yield tts_pb2.StreamSynthesisRequest(
#                         synthesis_input=tts_pb2.SynthesisInput(
#                             text=text_chunk + " "
#                         )
#                     )
        
#         # Получаем и сразу воспроизводим аудио
#         for response in stub.StreamSynthesis(request_generator(), metadata=auth_meta):
#             if response.audio_chunk.data:
#                 stream.write(response.audio_chunk.data)
#             if response.text_chunk.text:
#                 print("Озвучивается:", response.text_chunk.text)
    
#     # Закрываем поток
#     stream.stop_stream()
#     stream.close()
#     p.terminate()








# def respons_ds(text: str):
#     client = OpenAI(api_key=API_DS, base_url="https://api.deepseek.com")
#     collected_content = ""  # <- добавил
    
#     for chunk in client.chat.completions.create(
#         model="deepseek-chat",
#         messages=[
#             {"role": "system", "content": "Ты ассистент ребенка. Твой ответ всегда состоит из 3 слов!"},
#             {"role": "user", "content": text},
#         ],
#         stream=True):

#         delta = chunk.choices[0].delta
#         if delta.content:
#             collected_content += delta.content
#             # print(delta.content, end="", flush=True)  # <- закомментил
#             yield {'type': 'text', 'content': delta.content}

# # Правильный вызов:
# for chunk in respons_ds("Привет Маша, как дела?"):
#     print(chunk['content'], end="")




















# import subprocess
# import os

# def play_audio(filename):
#     """
#     Воспроизведение аудиофайла через aplay с авто-конвертацией
#     """
    
#     if not os.path.exists(filename):
#         print(f"Ошибка: файл {filename} не найден")
#         return False
    
#     # Конвертируем через sox "на лету"
#     cmd = f"sox {filename} -b 32 -c 2 -t wav - | aplay"
    
#     try:
#         print(f"Воспроизведение {filename}...")
#         result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
#         print("Воспроизведение завершено")
#         return True
        
#     except subprocess.CalledProcessError as e:
#         print(f"Ошибка воспроизведения: {e}")
#         print(f"stderr: {e.stderr}")
#         return False

# # Использование:
# # play_audio("output_audio.wav")


# # 1. 
# dialog = [
#     {"role": "user", "content": "Привет как дела?"},
#     {"role": "assistant", "content": " В целом норм.."},
#     {"role": "user", "content": "Ясно.."}
# ]
# dialog = dialog[-2:]
# print(dialog)

# # 2.






# def record_audio(self, filename="test.wav"):
#     cmd = ["arecord", "-f", "S16_LE", "-c", "1", "-r", "16000", filename]
    
#     # Запускаем и сохраняем
#     self.record_process = subprocess.Popen(
#         cmd, 
#         stdout=subprocess.DEVNULL,
#         stderr=subprocess.DEVNULL
#     )
    
#     # Ждём флага
#     while self.recording_active:
#         time.sleep(0.1)
    
#     # Останавливаем
#     if self.record_process:
#         self.record_process.terminate()
#         try:
#             self.record_process.wait(timeout=1)
#         except subprocess.TimeoutExpired:
#             self.record_process.kill()
#         self.record_process = None





# python3 -m grpc_tools.protoc -I . -I third_party/googleapis \
#   yandex/cloud/ai/tts/v3/tts_service.proto \
#   yandex/cloud/ai/tts/v3/tts.proto