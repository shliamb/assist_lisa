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








if intent == "ACTION":
    stream_events = deepseek.refine_stream_tools(
        question=input_question,
        system=system,
        tools=tools
    )
    
    # Создаём генератор для TTS
    def text_generator():
        for event in stream_events:
            event_type = event.get('type')
            
            if event_type == 'text':
                content = event.get('content', '')
                if content:
                    print(content, end='', flush=True)
                    yield {'type': 'text', 'content': content}
            
            elif event_type == 'tool':
                tool_data = event.get('data', {})
                for tool_id, tool_info in tool_data.items():
                    try:
                        args = json.loads(tool_info.get('arguments', '{}'))
                        tool_name = tool_info.get('name', '')
                        
                        if tool_name:
                            answer = ""
                            result_function = deepseek.call_function(tool_name, args)

                            if result_function.get("queue"):
                                agent_task_queue.put(result_function)
                                print(f"[ACTION] Добавлена задача в очередь: {tool_name}({args})")
                                answer = "Просьба выполнена"
                            elif not result_function.get("queue"):
                                answer = result_function.get("value", "Данных нет")
                            else:
                                answer = "Ошибка, функция настроена не верно"

                            print(answer)
                            yield {'type': 'text', 'content': answer}
                            
                    except json.JSONDecodeError as e:
                        print(f"[ERROR] Ошибка парсинга JSON аргументов: {e}")
                    except Exception as e:
                        print(f"[ERROR] Ошибка обработки tool: {e}")
            
            elif event_type == 'error':
                error_msg = event.get('content', 'Неизвестная ошибка')
                print(f"[ERROR]: Ошибка в стриме: {error_msg}")
                display.add_display_task({"block": "line", "text": "[ERROR]: Произошла ошибка при обработке запроса."})
    
    # Передаём генератор в TTS
    speechkit.stream_synthesis(text_generator())