"""
Раюочий мадбас провайдер, принимает получает 2 переменные
"""

from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading
import time

# Глобальные переменные для хранения значений регистров
input1 = 0
input2 = 0
output1 = 0 # в регистр
output2 = 0

# Функция для запуска Modbus TCP сервера
def run_modbus_server(store):
    # Создаем контекст сервера
    context = ModbusServerContext(slaves=store, single=True)

    # Запускаем Modbus TCP сервер
    print("Starting Modbus TCP server on localhost:502")
    StartTcpServer(context, address=("localhost", 502))

# Функция для обновления значений регистров
def update_registers(store):
    global input1, input2, output1, output2

    while True:
        # Чтение значений из регистров 0 и 1 (input1 и input2)
        input1 = store.getValues(3, 0, count=1)[0]  # 3 - код функции для holding registers
        input2 = store.getValues(3, 1, count=1)[0]

        # Запись значений в регистры 2 и 3 (output1 и output2)
        store.setValues(3, 2, [output1])
        store.setValues(3, 3, [output2])

        # Имитация задержки
        time.sleep(1)

# Основной поток для обновления output1 и output2
def main_thread(store):
    global input1, input2, output1, output2

    while True:
        # Чтение значений input1 и input2
        current_input1 = input1
        current_input2 = input2
        print(current_input1)
        print(current_input2)

        # Обработка данных (пример)
        output1 = 5
        output2 = 6

        print(f"Main Thread: Прочитано input1: {current_input1}, input2: {current_input2}")
        print(f"Main Thread: Записано output1: {output1}, output2: {output2}")

        # Задержка 2 секунды
        time.sleep(2)

if __name__ == "__main__":
    # Создаем блок данных для holding registers
    store = ModbusSlaveContext(
        hr=ModbusSequentialDataBlock(0, [0] * 100)  # 100 регистров, инициализированных значением 0
    )

    # Запускаем Modbus TCP сервер в отдельном потоке
    server_thread = threading.Thread(target=run_modbus_server, args=(store,), daemon=True)
    server_thread.start()

    # Запускаем поток для обновления регистров
    update_thread = threading.Thread(target=update_registers, args=(store,), daemon=True)
    update_thread.start()

    # Запускаем основной поток
    main_thread(store)