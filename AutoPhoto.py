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
            data = receive_socket.recv(1024)
            result = data.decode('utf-8').strip().strip(';')
            logging.info("CAM Получен QR результат: %s", result)
            return result if result else None

    except Exception as e:
        logging.error("CAM Ошибка при получении QR: %s", str(e))
        return None

def photo():
    with _camera_lock:
        attempts = 3
        results = []

        for i in range(attempts):
            logging.info("CAM Попытка №%d получения QR-кода...", i + 1)
            result = get_qr_result()
            if result:
                results.append(result)

        if not results:
            logging.error("CAM QR-код не получен ни в одной из попыток.")
            return 404, None

        unique_results = list(set(results))
        if len(unique_results) == 1:
            logging.info("CAM QR-код стабильно считан: %s", unique_results[0])
            return 200, unique_results[0]
        else:
            logging.warning("CAM QR-коды отличаются между попытками: %s", unique_results)
            return 404, None

# Простой цикл: каждые 3 секунды пробуем получить QR, если есть - сохраняем в файл
print("Начинаем сканирование...")
while True:
    res, data = photo()
    
    if res == 200 and data:
        # Сохраняем в файл в столбик
        with open('scanned_boards.txt', 'a', encoding='utf-8') as f:
            f.write(f"{data}\n")
        print(f"Сохранено: {data}")
    else:
        print("QR не найден, ждем...")
    
    time.sleep(3)