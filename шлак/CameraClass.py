import logging
import socket

class CameraConnection:
    def __init__(self, camera_ip, trigger_port=2001, camera_port=2002):
        self.camera_ip = camera_ip
        self.trigger_port = trigger_port
        self.camera_port = camera_port

        # Set up basic logging configuration
        logging.basicConfig(
            filename='RTK.log',
            level=logging.INFO,
            format='Camera - %(asctime)s - %(levelname)s - %(message)s'
        )
        logging.info("CameraConnection initialized with camera IP: %s", camera_ip)

    def send_start_command(self):
        """Отправляем команду для начала съемки."""
        try:
            # Создаем TCP-сокет для отправки команды "start"
            trigger_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            trigger_socket.connect((self.camera_ip, self.trigger_port))
            trigger_socket.sendall(b'start')
            logging.info("Command 'start' sent to camera at IP: %s, Port: %d", self.camera_ip, self.trigger_port)
            print("CAM - Coamand 'start' sent on port 2001.")
            trigger_socket.close()
        except Exception as e:
            logging.error("Error sending 'start' command to camera: %s", e)
            print(f"CAM - Erorr sent comand: {e}")

    def receive_data(self):
        """Получаем три фотографии и проверяем их на совпадение."""
        try:
            # Создаем TCP-сокет для получения данных от камеры
            receive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            receive_socket.connect((self.camera_ip, self.camera_port))
            logging.info("Waiting for data from camera at IP: %s, Port: %d", self.camera_ip, self.camera_port)
            print(f"CAM - Waiting result on port {self.camera_port}...")

            pictures = []

            # Получаем три фотографии
            for i in range(3):
                picture_data = receive_socket.recv(4096)  # Размер буфера можно увеличить
                if not picture_data:
                    logging.error("Error receiving picture %d from camera.", i + 1)
                    print(f"CAM - Error when waiting photo {i + 1}.")
                    receive_socket.close()
                    return 200, None  # Возвращаем ошибку, если не удалось получить фото
                pictures.append(picture_data)
                logging.info("Picture %d received successfully", i + 1)

            # Закрываем сокет после получения всех данных
            receive_socket.close()

            # Сравниваем фотографии между собой
            if pictures[0] == pictures[1] == pictures[2]:
                logging.info("Pictures are identical.")
                print("CAM - 3 Photo Same.")
                return 0, pictures[0]  # Возвращаем код 0 и первое совпавшее фото
            else:
                logging.error("Error: Pictures are not identical.")
                print("CAM - Error: Pictures are not identical.")
                return 200, None  # Возвращаем ошибку и None

        except Exception as e:
            logging.error("Error receiving data from camera: %s", e)
            print(f"CAM - Error Data Recieved: {e}")
            return 200, None  # Возвращаем ошибку при исключении

    def take_three_pictures(self):
        """Делаем три фото, проверяем их и возвращаем результат."""
        logging.info("Starting process to take three pictures.")
        self.send_start_command()
        return self.receive_data()



# Пример использования
camera_ip = '192.168.1.50'
camera = CameraConnection(camera_ip)

logging.info("Starting the picture-taking process for camera with IP: %s", camera_ip)

code, result = camera.take_three_pictures()

if code == 200:
    logging.error("Error: Pictures are not identical or not received.")
    print("CAM - Ошибка: фотографии не совпадают или не получены.")
else:
    logging.info("Successfully received identical picture.")
    print("CAM - Получено совпадающее фото:", result)



