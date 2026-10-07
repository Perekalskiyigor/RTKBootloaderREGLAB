"""Столы с многпоточностью класс, так тетстился"""

import time
import threading

# Глобальные переменные для отслеживания состояния каждой главной операции
operation1_status = 0  # 0 - выполняется, 1 - завершена
operation2_status = 0
operation3_status = 0

class Operation:
    def __init__(self, name, status_var):
        self.name = name  # Название главной операции
        self.flag = False  # Флаг, который будет подниматься по завершению операции
        self.status_var = status_var  # Переменная для отслеживания статуса

    def run_sub_operations(self):
        """Выполняем подоперации в рамках главной операции"""
        print(f"Выполнение подопераций для {self.name}...")
        time.sleep(1)  # Пауза между подоперациями для видимости
        self.sub_operation_1()
        time.sleep(1)
        self.sub_operation_2()
        time.sleep(1)
        self.sub_operation_3()
        time.sleep(1)

        # После выполнения всех подопераций поднимаем флаг
        self.flag = True
        self.update_status(1)
        print(f"{self.name} завершена. Флаг поднят.")

    def sub_operation_1(self):
        """Подоперация 1"""
        print(f"  - Выполняется подоперация 1 для {self.name}")

    def sub_operation_2(self):
        """Подоперация 2"""
        print(f"  - Выполняется подоперация 2 для {self.name}")

    def sub_operation_3(self):
        """Подоперация 3"""
        print(f"  - Выполняется подоперация 3 для {self.name}")

    def update_status(self, status):
        """Обновление глобальной переменной статуса"""
        globals()[self.status_var] = status


class MainProcess:
    def __init__(self):
        # Инициализация трех объектов с главными операциями и указанием глобальных переменных
        self.operation1 = Operation("Операция 1", "operation1_status")
        self.operation2 = Operation("Операция 2", "operation2_status")
        self.operation3 = Operation("Операция 3", "operation3_status")

    def run_operation(self, operation):
        """Запуск выполнения операции в отдельном потоке"""
        operation.run_sub_operations()

    def run(self):
        """Запуск всех главных операций параллельно"""
        print("Запуск главных операций параллельно...\n")

        # Создаем потоки для каждой операции
        thread1 = threading.Thread(target=self.run_operation, args=(self.operation1,))
        thread2 = threading.Thread(target=self.run_operation, args=(self.operation2,))
        thread3 = threading.Thread(target=self.run_operation, args=(self.operation3,))

        # Запускаем потоки
        thread1.start()
        thread2.start()
        thread3.start()

        # Ждем завершения всех потоков
        thread1.join()
        thread2.join()
        thread3.join()


# Создаем объект MainProcess и запускаем все операции
main_process = MainProcess()
main_process.run()

# Выводим финальный статус всех операций
print("\nСтатус операций после завершения:")
print(f"Операция 1: {operation1_status}")
print(f"Операция 2: {operation2_status}")
print(f"Операция 3: {operation3_status}")
