"""Связь с камерой по ТСП"""
import socket

def photo():
    # Адрес и порт камеры
    camera_ip = '192.168.1.50'
    trigger_port = 2001  # Порт для отправки команды "start"
    camera_port = 2002   # Порт для получения результата

    # Создаем TCP-сокет для отправки команды "start"
    trigger_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    trigger_socket.connect((camera_ip, trigger_port))

    # Отправляем команду "start"
    trigger_socket.sendall(b'start')
    print("Команда 'start' отправлена на порт 2001.")

    # Закрываем сокет для отправки команды
    trigger_socket.close()

    # Создаем TCP-сокет для получения результата от камеры
    receive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    receive_socket.connect((camera_ip, camera_port))

    print(f"Ожидание результата от камеры на порту {camera_port}...")

    # Получаем данные от камеры
    data = receive_socket.recv(4096)  # Размер буфера можно увеличить, если ожидается большой объем данных
    print(f"Получены данные: {data}")

    # Закрываем сокет для получения данных
    receive_socket.close()
    return data
