import subprocess
from config import SUDO_PASS




class Network:
    def __init__(self):
        self.sudo_password = SUDO_PASS
        self.interface = self._get_wifi_interface()


    @staticmethod
    def _get_wifi_interface():
        """Получить имя Wi-Fi интерфейса"""
        try:
            # Сначала пробуем через iw
            result = subprocess.check_output(["iw", "dev"], 
                                           stderr=subprocess.STDOUT,
                                           text=True)
            
            for line in result.split('\n'):
                if 'Interface' in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[-1]
            
            # Если iw не нашел WiFi интерфейсов
            return None
            
        except FileNotFoundError:
            #print("Ошибка: iw не установлен")
            return None
        except subprocess.CalledProcessError as e:
            # iw вернул ошибку - возможно нет WiFi адаптера
            #print(f"iw error: {e.output}")
            return None
        except Exception as e:
            print(f"Error get_wifi_interface: {e}")
            return None


    def get_signal_cached(self):
        """ Получения уровня сигнала
            кешь закоментил, так как в run.py 
            уже кешируется в общем потоке"""
        # """Кеширует результат на cache_seconds секунд"""
        # now = time.time()
        # if now - self.last_check < self.cache_seconds:
        #     return self.last_level
        
        signal = self._get_signal_raw()
        # Конвертируем в уровень для иконки (0-3)
        if signal is None: level = 'no_signal'
        elif signal >= -50: level = 'high_signal'
        elif signal >= -70: level = 'mid_signal'
        elif signal >= -80: level = 'low_signal'
        else: level = 'no_signal'
        self.last_level = level
        # self.last_check = now
        return self.last_level
    

    def _get_signal_raw(self):
        """Сырое получение сигнала"""
        try:
            # Только нужные данные, без лишнего парсинга
            result = subprocess.run(
                ['iw', self.interface, 'link'],
                capture_output=True,
                text=True
            )
            
            # Быстрый поиск по строке
            output = result.stdout
            signal_pos = output.find('signal:')
            if signal_pos != -1:
                line = output[signal_pos:].split('\n')[0]
                signal = line.split(':')[1].strip().split()[0]
                return int(signal)
        except:
            pass
        return None


    def get_current_ip(self):
        """Получает текущий IP адрес интерфейса"""
        try:
            result = subprocess.run(
                ['ip', '-4', 'addr', 'show', self.interface],
                capture_output=True,
                text=True
            )
            
            for line in result.stdout.split('\n'):
                if 'inet ' in line:
                    # Пример: "inet 192.168.1.56/24 brd 192.168.1.255 scope global wlan0"
                    return line.split()[1].split('/')[0]
            
            return None
        except Exception as e:
            print(f"Ошибка получения IP: {e}")
            return None


    def is_internet_connection(self) -> bool:
        """ Прверяем наличие подключения и наличия интеренета """
        try:
            # Смотрим текущее подключение
            result = subprocess.run(['iwconfig', self.interface], 
                                capture_output=True, text=True)
            
            # Если нет ESSID или "Not-Associated"
            if 'ESSID:""' in result.stdout or 'Not-Associated' in result.stdout:
                return False
            
            # Проверяем есть ли интернет
            ping_result = subprocess.run(['ping', '-c', '1', '-W', '2', '8.8.8.8'],
                                    capture_output=True)
            if ping_result.returncode != 0:
                return False
                
            return True
            
        except:
            return False


    @staticmethod
    def get_ip() -> str:
        """Странно получает ip """
        try:
            result = subprocess.check_output(["hostname", "-I"]).decode().strip()
            ip = result.split()
            return ip[0] if ip else None
            
        except Exception as e:
            print(f"Error get_ip_address: {e}")
            return False