import time
#import sys
import queue
import threading
import subprocess
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from PIL import Image, ImageDraw, ImageFont
from config import MOTHERBOARD, port, address, screen_height, screen_width, font_name, font_size, blocks, icons, letter_width, letter_height, line_height, MAX_LINE_LENGTH, TRUNCATE_AT



class Display:

    """
        Общий класс отображения на экране

        В config.py есть blocks словарь, где прописаны блоки на экране с координатами.
        В отдельном потоке, запускается цикл, который проверяет очередь таск для экрана.
        Есть 3 строки, первые две - в них выводиться текущая полезная информация,
        Третья - системная, все нужные данные.
        На экран выводиться из тасок в указанное место и высвечивается, пока на эту 
        позицию не пришла следущая таска, которая вызывает очистку только своей области
        и выводит на нее новое сообщение не затронув остальное.

    """

    def __init__(self):
        """ Инициализация дисплея и его настроек """
        self.matherboard = MOTHERBOARD
        self.serial = i2c(port=port, address=address)
        self.device = ssd1306(self.serial, width=screen_width, height=screen_height)
        self._create_new_image() # Создаем новое изображение 
        self.display_queue = queue.Queue(maxsize=50)
        self.font = self._get_font(font_name, font_size)
        self.cycle_screen()
        #print("The Display module is loaded")


    def _get_font(self, name, size):
        """ Функция для поиска установленного шрифта, 
            если нет устанавливает его сама """
        font = None
        # Список путей для поиска шрифтов
        font_paths = [
            name,
            f"/usr/share/fonts/truetype/{name}",
            f"/usr/local/share/fonts/{name}",
            f"./fonts/{name}"
        ]

        # Попытка 1: Загрузить указанный шрифт из различных путей
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, size)
                #print(f"Font loaded from: {font_path}")
                return font
            except Exception as e:
                continue

        # Попытка 2: Системный шрифт по умолчанию
        try:
            font = ImageFont.load_default()
            #print("Using system default font")
            return font
        except Exception as e:
            print(f"Error loading system default font: {e}")

        # Попытка 3: Установка шрифта
        try:
            print("Installing fonts-dejavu, please wait...")
            subprocess.check_call(['apt', 'install', '-y', 'fonts-dejavu'],
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
            time.sleep(10)  # Уменьшил время ожидания

            # Пробуем снова после установки
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, size)
                    print(f"Font loaded after installation: {font_path}")
                    return font
                except:
                    continue
        except Exception as e:
            print(f"Font installation failed: {e}")

        # Финальный fallback
        print("Using basic font")
        return ImageFont.load_default()


    def _create_new_image(self):
        """Создает чистое изображение"""
        self.image = Image.new("1", (self.device.width, self.device.height))
        self.draw = ImageDraw.Draw(self.image)


    def __del__(self):
        """ Очистка при удалении объекта
            вызывается автоматом """
        if hasattr(self, 'device'):
            self._clear_display()


    def _clear_display(self):
        """Полная очистка дисплея"""
        self._create_new_image()
        self.device.display(self.image)


    def add_display_task(self, data: dict):
        """Добавление таски в очередь"""
        self.display_queue.put(data)
        #print(f"В очередь добавленно: {data}")
        return True


    def get_display_task(self) -> dict:
        """Забрать таску из очереди"""
        #print(f"Таска забрана")
        return self.display_queue.get()


    def done_display_task(self):
        """Таска выполнена"""
        self.display_queue.task_done()
        #print(f"Таска выполнена, в очереди ({self.display_queue.qsize()})")
        return True


    def _draw_wifi_icon(self, x: int, y: int, name: str = 'sys'):
        """Рисует bitmap-иконку (8x8 пикселей)."""
        bitmap = icons.get(name, icons['0'])
        for row in range(8):
            for col in range(8):
                if bitmap[row] & (1 << col):
                    # Рисуем точку. Используем fill=255 для белого на монохромном дисплее
                    self.draw.point((x + col, y + row), fill=255)


    def _draw_text(self, x, y, text):
        """ Отображение текста"""
        if text is not None:
            safe_text = str(text)
            self.draw.text((x, y), safe_text, font=self.font, fill=255)
        else:
            print("Warning: Attempted to draw None text")


    def clear_area(self, x1, y1, x2, y2):
        """Очистить указанную область (закрасить чёрным)"""
        self.draw.rectangle([x1, y1, x2, y2], fill=0, outline=0)
        self.device.display(self.image)


    def cycle_screen(self):
        """Background thread that processes display tasks from queue."""
        
        def truncate_text(text: str) -> str:
            """Truncate text to fit display line."""
            if len(text) > MAX_LINE_LENGTH:
                return f"{text[:TRUNCATE_AT]}.."
            return text
        
        def render_block(block_name: str, text: str):
            """Clear and draw text in specified block."""
            coords = blocks.get(block_name, {})
            x, y = coords.get("x", 0), coords.get("y", 0)
            width, height = coords.get("w", 128), coords.get("h", 10)
            
            self.clear_area(x, y, x + width, y + height)
            self._draw_text(x, y, text)
        
        def render_icon(name_icon: str):
            """Очистить и нарисовать иконку в указанном блоке."""
            coords = blocks.get(name_icon, {})
            x, y = coords.get("x", 0), coords.get("y", 0)
            width, height = coords.get("w", 8), coords.get("h", 8)
            
            # Очищаем область иконки
            self.clear_area(x, y, x + width, y + height)
            # Рисуем иконку. icon_data - это уровень сигнала, например '3'
            self._draw_wifi_icon(x, y, name_icon)


        def run_loop():
            last_line_text = None
            #last_line2_text = None  # для хранения предпоследней строки
            
            while True:
                try:
                    task = self.get_display_task()
                    if not task:
                        time.sleep(0.1) # <<<--- ВАЖНО: отдыхаем, если задач нет
                        continue
                    
                    block = task.get("block")
                    text = task.get("text", "")
                    


                    # if self.matherboard == "ORANGE":
                    if block == "line":
                        # Move previous line to line2
                        if last_line_text:
                            render_block("line2", truncate_text(last_line_text))
                        
                        # Draw new line to line1
                        render_block("line1", truncate_text(text))
                        last_line_text = text

                    # if self.matherboard == "RASPBERRY":
                    #     # Сдвигаем всё вниз
                    #     if last_line2_text:
                    #         render_block("line3", truncate_text(last_line2_text))
                        
                    #     if last_line_text:
                    #         render_block("line2", truncate_text(last_line_text))
                        
                    #     # Новая строка
                    #     render_block("line1", truncate_text(text))
                        
                    #     # Обновляем историю
                    #     last_line2_text = last_line_text
                    #     last_line_text = text


                    elif block == "icon":
                        # Ожидаем, что в task будет ключ "name"
                        name_icon = task.get("name", "0")
                        render_icon(name_icon)
                    
                    else:
                        render_block(block, text)
                    
                    self.device.display(self.image)
                    self.done_display_task()
                    
                except Exception as e:
                    # Логируй или обрабатывай, но не дай потоку упасть
                    print(f"Display error: {e}")
                    time.sleep(1)  # при ошибке тоже отдыхаем
        
        thread = threading.Thread(target=run_loop, daemon=True) #, name="DisplayThread")
        thread.start()
        return thread










# display = Display()






# display.add_display_task({"block": "icon", "name": "volume"})

# time.sleep(34444)

# display.add_display_task({"block": "line", "text": "hi bro!"})

# time.sleep(1)


# display.add_display_task({"block": "line", "text": "Приветики пистолетики ребята родные мои суки .."})

# time.sleep(1)

# display.add_display_task({"block": "sys", "text": "IP: 192.168.1.11"})

# time.sleep(1)

# # display.clear_area(0, 0, 30, 10)

# display.add_display_task({"block": "line", "text": "i am buse, sory!"})

# time.sleep(1)

# display.add_display_task({"block": "line", "text": "Загружается что то там кажется уже долго очень .."})

# time.sleep(1)

# display.add_display_task({"block": "line", "text": "И еще что то грузит бля так уже прям суки .."})

# # time.sleep(10)

# display.add_display_task({"block": "wifi_icon", "name": "0"})

# time.sleep(3)

# display.add_display_task({"block": "wifi_icon", "name": "1"})

# time.sleep(3)

# display.add_display_task({"block": "wifi_icon", "name": "2"})

# time.sleep(3)

# display.add_display_task({"block": "wifi_icon", "name": "3"})

# time.sleep(3)

# display.add_display_task({"block": "wifi_icon", "name": "full"})

# time.sleep(3)

# time.sleep(3)

# display.add_display_task({"block": "sys", "text": "vol: 35  bat: 91  waiting"})

# time.sleep(20)