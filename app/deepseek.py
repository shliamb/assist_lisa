from typing import Generator, Iterator, Optional
from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError, APIError
from config import API_DS, MODEL_DS, TIMEOUT, HISTORY_LIMIT, SYS_CON





class DeepSeek:
    def __init__(self):
        '''Инициализация диписика и его настроек'''
        self.client = OpenAI(
            api_key=API_DS,
            base_url="https://api.deepseek.com"
        )
        self.system_content = SYS_CON
        self.dialog = []
        self.model = MODEL_DS
        self.timeout = TIMEOUT
        self.history_limit = HISTORY_LIMIT
        # self.functions = FUNCTIONS
        # self.agents = AGENTS
        # self.tool_choice = "auto"


    @staticmethod
    def _error_net(text_err):
        """Заглушка для ошибок сети. Возвращает объект в формате ответа API, 
        чтобы основной код не сломался. Внутри будет текст ошибки вместо ответа модели."""

        from types import SimpleNamespace
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=text_err
                    )
                )
            ]
        )


    def _call_request(
            self,
            question: str,
            system: str = None,
            stream: bool = True,
            tools: dict = None,
            dialog: list = None,
            response_format: dict = None
        ):
        """ Чистый Вызов API DeepSeek """
        try:
            messages = []
            messages.append({"role": "system", "content": system if system else self.system_content})
            if not dialog: # Проверяю что диалог не передан в функцию
                if self.dialog: # Предыдущий диалог выгружается из класса
                    for one in self.dialog:
                        messages.append(one)
            messages.append({"role": "user", "content": question}) # текущий вопрос user

            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                response_format=response_format,
                stream=stream,
                timeout=TIMEOUT # 5 секунд на подключение, 30 на чтение
                # max_tokens=self.max_tokens,
                # temperature=self.temperature,
                #timeout=self.timeout
            )
        
        except APITimeoutError:
            return self._error_net("Сервер DeepSeek отвечает слишком долго.")
        except APIConnectionError:
            return self._error_net("Проблемы с интернет-соединением.")
        except RateLimitError:
            return self._error_net("Превышен лимит запросов к DeepSeek.")
        except APIError as e:
            # Логируем реальную ошибку для отладки
            print(f"[DEEPSEEK ERROR] {type(e).name}: {str(e)}")
            return self._error_net(f"Ошибка DeepSeek API: {e.status_code}")


    def stream_llm_response(self, text: str) -> Generator[dict, None, None]:
        """Запрос в режиме стрим к DeepSeek"""
        full_answer = ""
        for chunk in self._call_request(text):
            delta = chunk.choices[0].delta
            if delta.content:
                yield {'type': 'text', 'content': delta.content}
                full_answer += delta.content
            
        self._add_dialog(text, full_answer)


    def _add_dialog(self, question: str, answer: str) -> None:
        """ Добавление диалога в память """
        if not question or not answer:
            print("Atention: question or answer in _add_dialog is empty")
            return
        self.dialog.append({"role": "user", "content": question})
        self.dialog.append({"role": "assistant", "content": answer})
        self.dialog = self.dialog[-self.history_limit:] # Последние 20 HISTORY_LIMIT



    def _clear_dialog(self) -> None:
        """ Очистка диалога """
        self.dialog = []






        
# # Проверка:
# deepseek = DeepSeek()
# for chunk in deepseek.stream_llm_response("Сколько в среднем в неделю секса у разведенной женщины и сколько у мужчины по статистике? "):
#     print(chunk['content'], end="")
# dialog = []

# dialog = [
#     {"role": "user", "content": "Привет как дела?"},
#     {"role": "assistant", "content": " В целом норм.."},
#     {"role": "user", "content": "Ясно.."}
# ]
# dialog = dialog[3:]
