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
#     text_stream = "Ошибка системы!"
#     speechkit.stream_synthesis(text_stream)      # передаём и озвучиваем

#     # MIC:
#     # resut = speechkit.stream_mic_record()
#     # print("resut:", resut)


# main()




# blocks = {
#     # Основные строки текста (сверху)
#     "line1": {"x": 0, "y": 0},
#     "line2": {"x": 0, "y": line_height},
#     "line3": {"x": 0, "y": line_height * 2},

#     # Системная строка (нижняя часть)
#     "sys": {"x": 0, "y": 52},  # почти внизу

#     # Иконки статуса (нижняя строка, слева направо)
#     # Сигнал WiFi
#     "high_signal": {"x": 0, "y": 54, "w": 8, "h": 8},
#     "mid_signal": {"x": 0, "y": 54, "w": 8, "h": 8},
#     "low_signal": {"x": 0, "y": 54, "w": 8, "h": 8},
#     "no_signal": {"x": 0, "y": 54, "w": 8, "h": 8},

#     # RAM иконка
#     "ram": {"x": 12, "y": 54, "w": 8, "h": 8},
#     "size_ram": {"x": 22, "y": 53, "w": 25, "h": 8},  # чуть шире для цифр

#     # Громкость иконка
#     "ico_vol": {"x": 52, "y": 54, "w": 8, "h": 8},
#     "volume": {"x": 62, "y": 53, "w": 20, "h": 8},
# }




