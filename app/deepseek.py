from typing import Generator, Iterator, Optional
from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError, APIError
from agents import AGENTS
from functions import FUNCTIONS
from functools import lru_cache
from config import API_DS, MODEL_DS, TIMEOUT, HISTORY_LIMIT, SYS_CON, TOOLS_ANSWER
import json




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
        self.functions = FUNCTIONS
        self.agents = AGENTS
        self.tool_choice = "auto"
        # self.max_tokens = 1000
        # self.temperature = 0.7
        self.last_full_answer = ""


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


    def get_tools_for_agent(self, function_names: list) -> list:
        """ Формирует tools"""
        tools = []
        for func_name in function_names:
            if func_name in self.functions:
                func_info = self.functions[func_name]
                tools.append({
                    "type": "function",
                    "function": {
                        "name": func_name,
                        "description": func_info["description"],
                        "parameters": func_info["schema"]
                    }
                })
        return tools
    

    def call_function(self, func_name, arguments):
        """Вызываем функцию по имени"""
        if func_name in self.functions:
            func = self.functions[func_name]["function"]
            return func(**arguments)
        return {"error": f"Функция {func_name} не найдена"}


    def get_tools(self, agent: str = "general_agent") -> tuple:
        """ Получает системный промпт и tools для указанного агента. """
        try:
            system = self.agents[agent]["system"]
            function_names = self.agents[agent]["tools"]
            tools = self.get_tools_for_agent(function_names)
            #print(json.dumps(tools, indent=2, ensure_ascii=False))
            return system, tools
        
        except KeyError as e:
            raise KeyError(f"Агент '{agent}' не найден. Доступные агенты: {list(self.agents.keys())}") from e


    def get_agent_info(self, agent: str) -> dict:
        """Полная информация об агенте (опционально)"""
        agent_config = self.agents[agent].copy()  # Копируем, чтобы не менять оригинал
        agent_config["tools_for_api"] = self.get_tools_for_agent(agent_config["function"])
        return agent_config


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
                timeout=self.timeout # 5 секунд на подключение, 30 на чтение
                # max_tokens=self.max_tokens,
                # temperature=self.temperature,
                # timeout=self.timeout
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



    @staticmethod
    def _action_router_smart(user_text: str) -> dict:
        """Упрощённый эвристический роутер БЕЗ цифр"""
        user_lower = user_text.lower().strip()
        words = user_lower.split()
        
        # 1. Ключевые слова ACTION (высокая уверенность)
        # Просто проверяем наличие слова
        action_words = ['громкость', 'volume', 'перезагрузить', 'перезагрузка', 'выключись', 'закройся', 'выключи', 'перезагрузку', 'дата', 'время', 'день', 'месяц', 'год']
        
        for word in action_words:
            if word in words:  # Проверяем в списке слов, а не в строке
                return {'intent': 'ACTION', 'confidence': 0.95}
        
        # 2. Ключевые слова CHAT (высокая уверенность)
        # Проверяем начало фразы
        chat_starts = {
            'спасибо': 0.85,
            'привет': 0.95,
            'здравствуй': 0.95,
            'добрый': 0.9,
            'как': 0.9,      # "как" в начале → CHAT с высокой уверенностью
            'что': 0.85,     # "что" в начале
        }
        
        if words:  # Если есть слова
            first_word = words[0]
            if first_word in chat_starts:
                return {'intent': 'CHAT', 'confidence': chat_starts[first_word]}
        
        # 3. Содержит вопросительные слова (средняя уверенность CHAT)
        question_words = ['как', 'почему', 'что', 'зачем', 'сколько', 'когда', 'где', 'какой']
        for word in words:
            if word in question_words:
                return {'intent': 'CHAT', 'confidence': 0.85}
        
        # 4. Содержит глаголы запроса информации (средняя уверенность CHAT)
        info_verbs = ['расскажи', 'объясни', 'покажи', 'найди', 'поищи']
        for word in words:
            if word in info_verbs:
                return {'intent': 'CHAT', 'confidence': 0.8}
        
        # 5. Заканчивается вопросом (средняя уверенность CHAT)
        if user_lower.endswith('?'):
            return {'intent': 'CHAT', 'confidence': 0.75}
        
        # 6. Начинается с повелительного глагола (ВЫСОКАЯ уверенность ACTION!)
        imperative_verbs = ['установи', 'поставь', 'включи', 'выключи', 'сделай', 'поменяй', 'настрой', 'перезагрузить', 'перезагрузка', 'перезагрузку']
        if words and words[0] in imperative_verbs:
            return {'intent': 'ACTION', 'confidence': 0.85}
        
        # 7. Содержит слова управления (средняя уверенность ACTION)
        control_words = ['громче', 'тише', 'ярче', 'темнее']
        for word in words:
            if word in control_words:
                return {'intent': 'ACTION', 'confidence': 0.8}
        
        # 8. Очень короткие сообщения (высокая уверенность CHAT)
        if len(words) <= 2:
            return {'intent': 'CHAT', 'confidence': 0.9}
        
        # 9. Непонятно → низкая уверенность CHAT → LLM
        return {'intent': 'CHAT', 'confidence': 0.4}


    @lru_cache(maxsize=100)
    def _llm_router_cached(self, user_text: str) -> dict:
        """Кэшированный роутер для повторяющихся запросов"""
        
        system = """Ты классификатор запросов. Определи тип:
        - ACTION: если пользователь хочет что-то сделать (изменить настройки, включить/выключить)
        - CHAT: если это разговор, вопрос, обсуждение
        
        ВЕРНИ ТОЛЬКО JSON: {"intent": "ACTION" или "CHAT", "confidence": число от 0 до 1}
        Примеры:
        "установи громкость 50" → {"intent": "ACTION", "confidence": 0.95}
        "привет как дела" → {"intent": "CHAT", "confidence": 0.98}
        "расскажи про погоду" → {"intent": "CHAT", "confidence": 0.9}"""
        
        result = self.refine_json_safe(
            question=user_text,
            system=system
        )

        if result['success']:
            json_data = result['json']
            return {
                'intent': json_data.get('intent', 'CHAT'),
                'confidence': float(json_data.get('confidence', 0.5)),
                'source': 'llm',
                'usage': result['usage']
            }
        else:
            # Fallback на эвристику
            print(f"[WARN] LLM router failed: {result['error']}")
            return self._action_router_smart(user_text)
        

    def hybrid_router(self, user_text: str):
        """Гибридный роутер с разными порогами"""
        quick_result = self._action_router_smart(user_text)
        
        # Разные пороги для ACTION и CHAT
        if quick_result['intent'] == 'ACTION':
            # Для ACTION нужна высокая уверенность (80%+)
            if quick_result['confidence'] >= 0.8:
                print(f"[ROUTER] Эвристика ACTION (conf={quick_result['confidence']})")
                return quick_result
        
        elif quick_result['intent'] == 'CHAT':
            # Для CHAT достаточно средней уверенности (60%+)
            if quick_result['confidence'] >= 0.6:
                print(f"[ROUTER] Эвристика CHAT (conf={quick_result['confidence']})")
                return quick_result
        
        # Не уверены → LLM
        print(f"[ROUTER] Не уверен → LLM (conf={quick_result['confidence']})")
        return self._llm_router_cached(user_text)






    def refine_json_safe(
        self,
        question: str,
        system: str = None,
        response_format: dict = None,
        max_retries: int = 1
    ) -> dict:  # Возвращаем dict вместо list для удобства
        """
        Безопасная версия с повторными попытками.
        
        Returns:
            dict: {'success': bool, 'json': dict, 'usage': dict, 'error': str}
        """
        if response_format is None:
            response_format = {"type": "json_object"}
        
        for attempt in range(max_retries):
            try:
                response = self._call_request(
                    question=question,
                    system=system,
                    tools=None,
                    stream=False,
                    response_format=response_format
                )
                
                if not hasattr(response, 'choices'):
                    raise ValueError("Invalid API response")
                
                content = response.choices[0].message.content
                
                # Парсим JSON
                # import json
                try:
                    if isinstance(content, str):
                        json_data = json.loads(content)
                    else:
                        json_data = content
                except json.JSONDecodeError as e:
                    if attempt < max_retries - 1:
                        continue  # Пробуем ещё раз
                    raise ValueError(f"Invalid JSON: {content[:100]}")
                
                # Собираем usage
                usage = {}
                if hasattr(response, 'usage'):
                    usage = {
                        'completion_tokens': response.usage.completion_tokens,
                        'prompt_tokens': response.usage.prompt_tokens,
                        'total_tokens': response.usage.total_tokens,
                        'cached_tokens': getattr(
                            getattr(response.usage, 'prompt_tokens_details', None),
                            'cached_tokens', 0
                        )
                    }
                
                return {
                    'success': True,
                    'json': json_data,
                    'usage': usage
                }
                
            except Exception as e:
                print(f"[ERROR] refine_json attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    return {
                        'success': False,
                        'error': str(e),
                        'json': {'intent': 'CHAT', 'confidence': 0.5},  # Fallback
                        'usage': {}
                    }
        
        return {
            'success': False,
            'error': 'Max retries exceeded',
            'json': {'intent': 'CHAT', 'confidence': 0.5},
            'usage': {}
        }




    def stream_llm_response(self, text: str) -> Generator[dict, None, None]:
        """Запрос в режиме стрим к DeepSeek короткая версия"""
        full_answer = ""
        for chunk in self._call_request(text):
            delta = chunk.choices[0].delta
            if delta.content:
                yield {'type': 'text', 'content': delta.content}
                full_answer += delta.content
            
        self._add_dialog(text, full_answer)
        self.last_full_answer = full_answer



    def get_last_answer(self):
         return self.last_full_answer



    def refine_stream(
            self,
            question: str,
            system: str,
        ) -> Iterator[dict]:
        """
            Stream ответ от DeepSeek + usage:
            - {'type': 'text', 'content': '...'} - текст для stream вывода
            - {'type': 'usage', 'data': {...}} - статистика (в конце)
        """

        collected_content = ""
        answer = ""

        for chunk in self._call_request(
                question=question,
                system=system,
                stream=True
            ):
            delta = chunk.choices[0].delta
            
            # 1. Текстовый ответ stream
            if delta.content:
                collected_content += delta.content
                yield {'type': 'text', 'content': delta.content}

        # 2. Usage данные (из последнего chunk)
        if hasattr(chunk, 'usage') and chunk.usage:
            yield {
                'type': 'usage',
                'data': {
                    'completion_tokens': chunk.usage.completion_tokens,
                    'prompt_tokens': chunk.usage.prompt_tokens,
                    'total_tokens': chunk.usage.total_tokens,
                    'cached_tokens': getattr(chunk.usage.prompt_tokens_details, 'cached_tokens', 0)
                }
            }

        answer += collected_content
        self._add_dialog(question=question, answer=answer)



    def refine_stream_tools(
            self,
            question: str,
            system: str,
            tools: dict,
        ) -> Iterator[dict]:
        """
            Stream ответ от DeepSeek + tools + usage:
            - {'type': 'text', 'content': '...'} - текст для stream вывода
            - {'type': 'tool', 'data': {...}} - данные о вызове функции (после завершения)
            - {'type': 'usage', 'data': {...}} - статистика (в конце)
        """

        # Тут не сохраняю диалог, так как решил делать по готовности функции вопрос - ответ сохранять + посылать на озвучку.

        collected_content = ""
        tool_calls_buffer = {}
        current_tool_id = None
        answer = ""

        """ Кажется, большая история мешает LLM верно отработать функцию, 
            попробую сократить или удалить для tools """
        
        dialog = []
        if self.dialog:
            dialog.extend(self.dialog[-4:])  # Последние 4 сообщений из общего диалога

        for chunk in self._call_request(
                question=question,
                system=system,
                dialog=dialog,
                tools=tools,
                stream=True
            ):
            delta = chunk.choices[0].delta
            
            # 1. Текстовый ответ stream
            if delta.content:
                collected_content += delta.content
                yield {'type': 'text', 'content': delta.content}

            # 2. Функции - накапливаем, отдаем в конце
            if delta.tool_calls:
                for tool_call in delta.tool_calls:
                    if tool_call.id:
                        # Новый вызов функции
                        current_tool_id = tool_call.id
                        tool_calls_buffer[current_tool_id] = {
                            "name": tool_call.function.name or "",
                            "arguments": tool_call.function.arguments or "",
                            'id': tool_call.id
                        }
                    elif tool_call.function:
                        # Продолжение аргументов
                        if tool_call.function.name:
                            tool_calls_buffer[current_tool_id]["name"] += tool_call.function.name
                        if tool_call.function.arguments:
                            tool_calls_buffer[current_tool_id]["arguments"] += tool_call.function.arguments
        
        # 3. Usage данные (из последнего chunk)
        if hasattr(chunk, 'usage') and chunk.usage:
            yield {
                'type': 'usage',
                'data': {
                    'completion_tokens': chunk.usage.completion_tokens,
                    'prompt_tokens': chunk.usage.prompt_tokens,
                    'total_tokens': chunk.usage.total_tokens,
                    'cached_tokens': getattr(chunk.usage.prompt_tokens_details, 'cached_tokens', 0)
                }
            }

        # 4. Вызовы функций (отдаем разом после стрима)
        if tool_calls_buffer:
            if not collected_content:
                answer = TOOLS_ANSWER
            yield {'type': 'tool', 'data': tool_calls_buffer}




















        
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
