import socket
import logging
import time
import threading

# Set up basic logging configuration
logging.basicConfig(
    filename='RTK.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Локальная блокировка на уровне модуля — общая для всех импортов
_camera_lock = threading.Lock()


def get_qr_result():
    camera_ip = '192.168.1.50'
    trigger_port = 2001
    camera_port = 2002

    try:
        # Отправка команды "start"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as trigger_socket:
            trigger_socket.connect((camera_ip, trigger_port))
            trigger_socket.sendall(b'start')
            logging.info("CAM Команда 'start' отправлена на порт %d.", trigger_port)

        # Получение QR-результата
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as receive_socket:
            receive_socket.connect((camera_ip, camera_port))
            logging.info("CAM Ожидание результата от камеры на порту %d...", camera_port)
            data = receive_socket.recv(1024)  # QR код вряд ли больше
            result = result = data.decode('utf-8').strip().strip(';')  # Удаляет пробелы и ';'
            logging.info("CAM Получен QR результат: %s", result)
            return result if result else None

    except Exception as e:
        logging.error("CAM Ошибка при получении QR: %s", str(e))
        return None

def photo():
    with _camera_lock:  # <--- КРИТИЧЕСКИЙ СЕКЦИЯ
        attempts = 3
        results = []

        for i in range(attempts):
            logging.info("CAM Попытка №%d получения QR-кода...", i + 1)
            result = get_qr_result()
            if result:
                results.append(result)

        if not results:
            logging.error("CAM QR-код не получен ни в одной из попыток.")
            QRresult = 404
            return QRresult, None

        unique_results = list(set(results))
        if len(unique_results) == 1:
            logging.info("CAM QR-код стабильно считан: %s", unique_results[0])
            QRresult = 200
            data = unique_results[0]
            return QRresult, data
        else:
            logging.warning("CAM QR-коды отличаются между попытками: %s", unique_results)
            QRresult = 404
            return QRresult, None
    


res,data = photo()
print (f"Result={res}  Data = {data}")



for i in range(100):
    try:
        logging.debug(f"Попытка {i}: запрос фото с камеры")
        res,photodata = photo()
        print(f"С камеры получен ID {photodata}")
    except Exception as e:
        print(f"Ошибка: камера недоступна (photo camera not available). Детали: {e}")
    time.sleep(1)
while True:
    res,photodata = photo()
    if res != 200 or photodata == "NoRead":
        print(f"Ошибка получения фото с камеры")
        time.sleep(1)
    else:
        print(f"С камеры получено фото {photodata}")
        break 