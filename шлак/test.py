import time
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading




class ModbusProvider:
    def __init__(self):
        # Инициализация хранилища данных
        self.store = ModbusSlaveContext(
            hr=ModbusSequentialDataBlock(0, [0] * 100)  # 100 регистров, инициализированных значением 0
        )
        # From Regul
        self.Table11free = 0  # Стол один ложе 1 свободно
        self.RobotTake11 = 0  # Взял плату 11
        self.Table12free = 0  # Стол один ложе 2 свободно
        # In Regul
        self.subTable11free = 0  # Стол один ложе 1 освободи
        self.subRobotTake11 = 0  # Возьми плату 11
        self.subTable12free = 0  # Стол один ложе 2 освободи

        # Запуск Modbus TCP сервера в отдельном потоке
        self.server_thread = threading.Thread(target=self.run_modbus_server, daemon=True)
        self.server_thread.start()

        # Запуск потока для обновления регистров
        self.update_thread = threading.Thread(target=self.update_registers, daemon=True)
        self.update_thread.start()

    def run_modbus_server(self):
        """Запуск Modbus TCP сервера."""
        context = ModbusServerContext(slaves=self.store, single=True)
        print("Starting Modbus TCP server on localhost:502")
        StartTcpServer(context, address=("localhost", 502))

    def update_registers(self):
        """Обновление значений регистров."""
        while True:
            # Чтение значений из регистров 0 и 1 (input1 и input2)
            self.subTable11free = self.store.getValues(3, 31, count=1)[0]  # 3 - код функции для holding registers
            self.subRobotTake11 = self.store.getValues(3, 32, count=1)[0]
            self.subTable12free = self.store.getValues(3, 33, count=1)[0]

            # Запись значений в регистры 2 и 3 (output1 и output2)
            self.store.setValues(3, 0, [self.Table11free])
            self.store.setValues(3, 1, [self.RobotTake11])
            self.store.setValues(3, 2, [self.Table12free])

            time.sleep(1)

    def get_value_from_register(self, register):
        """Получение данных из конкретного регистра."""
        try:
            value = self.store.getValues(3, register, count=1)[0]  # Чтение одного значения
            return value
        except Exception as e:
            print(f"Error reading register {register}: {e}")
            return None  # Возвращаем None в случае ошибки

    def set_value_to_register(self, register, value):
        """Запись данных в конкретный регистр."""
        try:
            self.store.setValues(3, register, [value])  # Запись значения в регистр
            print(f"Successfully wrote {value} to register {register}")
            return True  # Успешная запись
        except Exception as e:
            print(f"Error writing to register {register}: {e}")
            return False  # Ошибка записи

    def get_inTable11free(self):
        """Получение данных из регистров."""
        return self.subTable11free

    def set_subTable11free(self, Table11free):
        """Установка данных в регистры."""
        self.Table11free = Table11free
        print(f"Modbus - Сдвинь плату освободив ложе1. {self.subTable11free}")

    def get_inRobotTake11(self):
        """Получение данных из регистров."""
        return self.subRobotTake11

    def set_subRobotTake11(self, RobotTake11):
        """Установка данных в регистры."""
        self.RobotTake11 = RobotTake11
        print(f"Modbus - Робот забери плату 1. {self.RobotTake11}")

    def get_inTable12free(self):
        """Получение данных из регистров."""
        return self.subTable12free

    def set_subTable12free(self, Table12free):
        """Установка данных в регистры."""
        self.Table12free = Table12free
        print(f"Modbus - Сдвинь плату освободив ложе1. {self.subTable12free}")


modbus_provider = ModbusProvider()

# Get value from register 31 (for example)
value = modbus_provider.get_value_from_register(31)
print(f"Value from register 31: {value}")

# Set value to register 1
success = modbus_provider.set_value_to_register(1, 123)
if success:
    print("Successfully updated register 1.")
else:
    print("Failed to update register 1.")
