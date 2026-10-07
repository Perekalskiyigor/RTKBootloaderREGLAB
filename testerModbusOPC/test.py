import threading
import time
import random

# === Глобальные данные и блокировка ===
global_data = {}
data_lock = threading.Lock()



# === Класс для Modbus-подключения ===
class ModbusClient(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True  # поток завершится вместе с программой

    def run(self):
        while True:
            value = random.randint(0, 100)
            with data_lock:
                global_data['modbus_value'] = value
            print(f"[Modbus] Wrote value: {value}")
            time.sleep(1)

# === Класс для OPC-подключения ===
class OPCClient(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True

    def run(self):
        while True:
            with data_lock:
                modbus_val = global_data.get('modbus_value')
                global_data['opc_ack'] = f"Got {modbus_val}" if modbus_val is not None else "No data"
            print(f"[OPC] Processed value: {modbus_val}")
            time.sleep(2)

# === Основная программа ===
def main():
    modbus = ModbusClient()
    opc = OPCClient()

    modbus.start()
    opc.start()

    # Управление из основной программы
    while True:
        with data_lock:
            # Пример чтения
            print(f"[Main] Current global data: {global_data}")
            # Пример управления
            global_data['user_command'] = 'RUN'
        time.sleep(3)

if __name__ == "__main__":
    main()

"""
Компонент	Поведение
ModbusClient	Каждую секунду записывает случайное значение в global_data['modbus_value'].
OPCClient	Каждые 2 секунды читает modbus_value, обрабатывает и пишет opc_ack.
Основной поток	Каждые 3 секунды читает словарь и пишет команду user_command.
"""