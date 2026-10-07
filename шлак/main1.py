import logging
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading
import time
import os

"""
Пользовательские модули
"""
import Provider1C
import logClass

# Глобальные переменные для обмена данными
# Глобальные переменные для хранения значений регистров
input1 = 0
input2 = 0
output1 = 0 # в регистр
output2 = 0


"""
MADBAS
"""

from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading
import time
import logging
import Provider1C

# Глобальные переменные для обмена данными
input1 = 0
input2 = 0
output1 = 0  # в регистр
output2 = 0

# Функция для запуска Modbus TCP сервера
def run_modbus_server(store):
    # Создаем контекст сервера
    context = ModbusServerContext(slaves=store, single=True)
    # Запускаем Modbus TCP сервер
    logging.info("Starting Modbus TCP server on localhost:502")
    print("Starting Modbus TCP server on localhost:502")
    StartTcpServer(context, address=("localhost", 502))

# Функция для обновления значений регистров
def update_registers(store):
    global input1, input2, output1, output2
    while True:
        try:
            # Чтение значений из регистров 0 и 1 (input1 и input2)
            input1 = store.getValues(3, 0, count=1)[0]
            input2 = store.getValues(3, 1, count=1)[0]

            # Запись значений в регистры 2 и 3 (output1 и output2)
            store.setValues(3, 2, [output1])
            store.setValues(3, 3, [output2])

            logging.info(f"Updated registers: input1={input1}, input2={input2}, output1={output1}, output2={output2}")
            time.sleep(1)
        except Exception as e:
            logging.error(f"Error in update_registers: {e}")

# Основной поток
def main_thread(store):
    global input1, input2, output1, output2
    while True:
        try:
            # Чтение значений input1 и input2
            current_input1 = input1
            current_input2 = input2
            logging.info(f"Main Thread: Read input1={current_input1}, input2={current_input2}")

            # Обработка данных (пример)
            output1 = 5
            output2 = 6

            logging.info(f"Main Thread: Written output1={output1}, output2={output2}")
            time.sleep(2)

            # Получение заказов из 1С
            cookies = Provider1C.login('user1', 'password123')
            ordersPLM = Provider1C.get_orders(cookies)
            ordersPLM = ordersPLM.get("orders", [])

            if not ordersPLM:
                message = "Не получены заказы из 1С ПЛМ"
                logging.error(message)
            else:
                logging.info(f"Received ordersPLM: {ordersPLM}")
        except Exception as e:
            logging.error(f"Error in main_thread: {e}")



# # 3. Получение деталей заказа
# get_order_details(558, cookies)

# # 4. Проверка наличия серийного номера в ЕРП
# check_order(558, 'SN1234', cookies)

# # 5. Лог в 1С ЕРП'
# mark_order_to1C(cookies)

# # 6. Ответ от 1С'
# mark_order_from1C(cookies)



"""
2. Получить ор Регул с интерфейса заказ который взят в работу
Вход
Выход
"""


"""
3. Сделать запрос в 1С ПЛМ на заказ. 
Вход
Выход Номер номенклатура колличество, версия прошивки, ссылка на прошивку, перечень серийниых номеров
"""

"""
5. Сделать запрос в 1С ЕРП для валидации платы (если такое необходимо с интерфейса). 
Вход
Выход Номер номенклатура колличество, версия прошивки, ссылка на прошивку, перечень серийниых номеров
"""

"""
6. Подготовка робота и всего остального к прошивке. Диагнстика и тд
Вход
Выход
"""

"""
7. Команда роботу взять чистую плату и поднести к сканеру
Вход
Выход
"""

"""
8. Считать штрих код платы с камеры.
Вход
Выход
"""

"""
9. Запрос в ПЛМ, что такая плата есть
Вход
Выход
"""

"""
10. привзяать Серийный номер к штрих коду платы.
Вход
Выход
"""

"""
11. Посмотреть совободный стол. И назначить стол готовй к прошивке платы. 
Если нет свободных ждем, если есть делаем дальше
Вход
Выход
"""

"""
12. Команда рботу поместить готовую плату на назначенный стол.
Вход
Выход
"""

"""
13. Начать процесс прошгивки на указанном столе
Вход
Выход
"""

"""
14. Следит что процесс прошивки на столе завершен. Если успешно, команда роботу плату прошита. Если проблема команда роботу плата брак.
Передать брак на интерфейс. Коол-во брака
Вход
Выход
"""

"""
15. Команда роботу убрать плату. если брак в брак если норм в прошитые. Освободить стол для следующей платы.
Вход
Выход
"""

"""
16. Сформировать отчет/лог в 1С, что плата успешно прошита, отдать штрих-код привязанный к серийнику
Вход
Выход
"""

if __name__ == "__main__":

    logClass.logingRTK()
    
    # Создание хранилища данных Modbus
    store = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [0] * 100))

    # Запуск Modbus TCP сервера в отдельном потоке
    server_thread = threading.Thread(target=run_modbus_server, args=(store,), daemon=True)
    server_thread.start()

    # Запуск потока для обновления регистров
    update_thread = threading.Thread(target=update_registers, args=(store,), daemon=True)
    update_thread.start()

    # Запуск основного потока
    main_thread(store)