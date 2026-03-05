import subprocess
from config import YANDEX, GAIN, SAVE_FILE, RATE, CHUNK, RECORD_SECONDS
import grpc
import gc
from typing import Generator, Iterator, Optional
# TTS
import yandex.cloud.ai.tts.v3.tts_pb2 as tts_pb2
import yandex.cloud.ai.tts.v3.tts_service_pb2_grpc as tts_service_pb2_grpc
# STT
import yandex.cloud.ai.stt.v3.stt_pb2 as stt_pb2
import yandex.cloud.ai.stt.v3.stt_service_pb2_grpc as stt_service_pb2_grpc





class YaSpeechKit:
    def __init__(self, display):
        # PUSH BUTTON ACT:
        self.record_process = None
        self.recording_active = False
        self.display = display

        # META:
        self.auth_meta = (("authorization", f"Api-key {YANDEX}"),)

        # TTS
        self.tts_channel = "tts.api.cloud.yandex.net:443"
        self.gain = GAIN
        self.buffer = ""

        # STT
        self.stt_channel = "stt.api.cloud.yandex.net:443"
        self.rate = RATE
        self.chunk = CHUNK
        self.record_seconds = RECORD_SECONDS

        # 
        self.last_transcription = ""



    def get_recording_active(self):
        return self.recording_active


    def change_recording_active(self, status: bool):
        self.recording_active = status


    def output_to_screen(self, bufer: str):
        if bufer: self.display.add_display_task({"block": "line", "text": f"ИИ: {bufer}"})



    # ЗАПИСЬ С МИКРОЫФОНА В СТРИМЕНГЕ
    def gen_config_mic(self):
        # Настройки распознавания
        recognize_options = stt_pb2.StreamingOptions(
            recognition_model=stt_pb2.RecognitionModelOptions(
                audio_format=stt_pb2.AudioFormatOptions(
                    raw_audio=stt_pb2.RawAudio(
                        audio_encoding=stt_pb2.RawAudio.LINEAR16_PCM,
                        sample_rate_hertz=self.rate,
                        audio_channel_count=1
                    )
                ),
                text_normalization=stt_pb2.TextNormalizationOptions(
                    text_normalization=stt_pb2.TextNormalizationOptions.TEXT_NORMALIZATION_ENABLED,
                    profanity_filter=False,
                    literature_text=False
                ),
                language_restriction=stt_pb2.LanguageRestrictionOptions(
                    restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
                    language_code=['ru-RU']
                ),
                audio_processing_type=stt_pb2.RecognitionModelOptions.REAL_TIME
            )
        )

        # Отправляем настройки
        yield stt_pb2.StreamingRequest(session_options=recognize_options)

        # Запускаем arecord и читаем из stdout
        cmd = [
            "arecord",
            "-f", "S16_LE",      # 16 бит
            "-c", "1",           # моно
            "-r", str(self.rate),     # частота
            "-t", "raw",         # raw формат, без заголовков
            "-D", "default"      # устройство по умолчанию
        ]
        
        self.record_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=self.chunk
        )
        
        print("Start recording\n")
        
        # Читаем данные и отправляем
        while self.recording_active:  # пока кнопка зажата
            data = self.record_process.stdout.read(self.chunk)
            if not data:
                break
            yield stt_pb2.StreamingRequest(chunk=stt_pb2.AudioChunk(data=data))
                
        print("Finished recording\n")
        
        # Завершаем процесс записи
        self.record_process.terminate()


    def stream_mic_record(self):
        phrases = []  # список для всех фраз
        current_phrase = ""  # буфер для текущей фразы
        self._clear_last_transcription()
        
        # Установите соединение с сервером
        cred = grpc.ssl_channel_credentials()
        channel = grpc.secure_channel(self.stt_channel, cred)
        stub = stt_service_pb2_grpc.RecognizerStub(channel)


        # Отправьте данные для распознавания
        it = stub.RecognizeStreaming(self.gen_config_mic(), metadata=self.auth_meta)

        # Обработайте ответы сервера
        try:
            for r in it:
                event_type, alternatives = r.WhichOneof('Event'), None

                if event_type == 'partial' and len(r.partial.alternatives) > 0:
                    alternatives = [a.text for a in r.partial.alternatives]
                    # выводим промежуточные результаты
                    print(f'partial: {alternatives[0]}', end='\r') # промежуточные гипотезы, пока человек говорит. Меняются в реальном времени. Не нужен для финала.
                    
                if event_type == 'final':
                    alternatives = [a.text for a in r.final.alternatives]
                    current_phrase += alternatives[0]
                    print(f'\nfinal: {current_phrase}') # финальный вариант после паузы. Сервер понял, что фраза закончена.
                    
                if event_type == 'final_refinement':

                    alternatives = [a.text for a in r.final_refinement.normalized_text.alternatives]
                    current_phrase = alternatives[0]
                    print(f'\nrefined: {current_phrase}') # final_refinement — уточнение final (исправление регистра, знаков препинания). Бери его.

                    # В конце сессии (когда стрим закончился)
                    if current_phrase:
                        phrases.append(current_phrase.strip())
                        current_phrase = ""

            self.last_transcription = ' '.join(phrases)
            # gc.collect()
            return self.last_transcription 
                    
        except grpc._channel._Rendezvous as err:
            print(f'Error code {err._state.code}, message: {err._state.details}')
            raise err



    # GET last_transcription
    def get_last_transcription(self):
        return self.last_transcription 


    # CLEAR last_transcription
    def _clear_last_transcription(self):
        self.last_transcription = ""


    # СИНТЕЗ ГОЛОСОВОГО ОТВЕТА ОТ LLM
    def stream_synthesis(self, text_stream: Generator[dict, None, None] | str):
        """Потоковый/Стриминговый Синтез Речи из генератора или гтового str"""
        cred = grpc.ssl_channel_credentials()
        auth_meta = self.auth_meta

        # Если строка — оборачиваем в генератор
        if isinstance(text_stream, str):
            # Если строка — превращаем в генератор с одним элементом
            def text_generator():
                yield {'type': 'text', 'content': text_stream}
            text_stream = text_generator()

        print("\ntext_stream:", text_stream, "\ntype:", type(text_stream) )

        # Запускаем play с чтением из stdin
        play_process = subprocess.Popen(
            ["play", "-t", "wav", "-", "gain", f"{self.gain}"],
            stdin=subprocess.PIPE
        )

        with grpc.secure_channel(self.tts_channel, cred) as channel:
            stub = tts_service_pb2_grpc.SynthesizerStub(channel)

            # Настройки синтеза
            synthesis_options = tts_pb2.SynthesisOptions(
                voice="ermil",
                role="neutral",
                output_audio_spec=tts_pb2.AudioFormatOptions(
                    # Настройки выходного аудио. Задайте через объекты RawAudio или ContainerAudio
                    
                    raw_audio=tts_pb2.RawAudio(
                        audio_encoding=tts_pb2.RawAudio.LINEAR16_PCM,
                        sample_rate_hertz=16000
                    ),
                    container_audio=tts_pb2.ContainerAudio(
                        container_audio_type=tts_pb2.ContainerAudio.ContainerAudioType.WAV
                    )
                )
            )

            # Генератор запросов
            def request_generator():
                yield tts_pb2.StreamSynthesisRequest(options=synthesis_options)
                
                if SAVE_FILE:
                    yield tts_pb2.StreamSynthesisRequest(
                        synthesis_input=tts_pb2.SynthesisInput(text=text_stream + " ")
                    )
                    return


                # Отправляем текст частями из DeepSeek
                for chunk in text_stream:
                    if chunk['type'] == 'text':
                        self.buffer += chunk['content']
                        if any(p in self.buffer for p in ['.', '!', '?', ',']):
                            print("bufer1:", self.buffer)
                            self.output_to_screen(self.buffer)
                            yield tts_pb2.StreamSynthesisRequest(
                                synthesis_input=tts_pb2.SynthesisInput(text=self.buffer + " ")
                            )
                            self.buffer = ""
                if self.buffer:
                    print("bufer2:", self.buffer)
                    self.output_to_screen(self.buffer)
                    yield tts_pb2.StreamSynthesisRequest(
                        synthesis_input=tts_pb2.SynthesisInput(text=self.buffer + " ")
                    )
                    self.buffer = ""


            if SAVE_FILE:
                import wave
                # Открываем файл для записи ДО цикла
                wav_file = wave.open("synthesized.wav", 'wb')
                wav_file.setnchannels(1)  # моно
                wav_file.setsampwidth(2)  # 16 бит = 2 байта
                wav_file.setframerate(20000)  # частота

            
            # Получаем и сразу воспроизводим аудио
            for response in stub.StreamSynthesis(request_generator(), metadata=auth_meta):
                try:
                    if response.audio_chunk.data:
                        play_process.stdin.write(response.audio_chunk.data)
                        play_process.stdin.flush()  # важно!
                        if SAVE_FILE: wav_file.writeframes(response.audio_chunk.data)
                    if response.text_chunk.text:
                        print("Озвучивается:", response.text_chunk.text)
                except Exception as e:
                    print(f"Ошибка при обработке ответа: {e}")
        
        # Закрываем и ждём
        play_process.stdin.close()
        play_process.wait()
        if SAVE_FILE: wav_file.close()