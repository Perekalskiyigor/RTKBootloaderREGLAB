import time
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading




#######################################Class Mudbus##########################################
class ModbusProvider:
    def __init__(self):
        # Инициализация хранилища данных
        self.store = ModbusSlaveContext(
            hr=ModbusSequentialDataBlock(0, [0] * 100)  # 100 регистров, инициализированных значением 0
        )
        # From Regul
        self.MoveTable = 0 # Стол один ложе 1 свободно
        self.robot_place_board = 0 #Робот положи плату на ложе 1 первого стола
        self.robot_take_board = 0 #Робот забери плату на ложе 1 первого стола
        
        # In Regul
        self.subMoveTable = 0 # Стол один ложе 1 свободно
        self.subrobot_place_board = 0 #ответ Робот положил плату на ложе 1 первого стола
        self.subrobot_take_board = 0 #ответ Робот забрал плату на ложе 1 первого стола

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
            self.subMoveTable = self.store.getValues(3, 31, count=1)[0]  # 3 - код функции для holding registers
            self.subrobot_place_board = self.store.getValues(3, 32, count=1)[0]
            self.subrobot_take_board = self.store.getValues(3, 33, count=1)[0]

            # Запись значений в регистры 2 и 3 (output1 и output2)
            self.store.setValues(3, 0, [self.MoveTable])
            self.store.setValues(3, 1, [self.robot_place_board])
            self.store.setValues(3, 2, [self.robot_take_board])

            time.sleep(1)
        
    #######################Стол
    def get_Tablefree(self):
        """Получение данных из регистров."""
        return self.subMoveTable
    

    def set_Tablefree(self, MoveTable):
        """Установка данных в регистры."""
        self.MoveTable = MoveTable
        print(f"Modbus - Сдвинь плату сол")

    

    ################# Робот
    def get_subrobot_place_board(self):
        """Получение данных из регистров."""
        return self.subrobot_place_board
    

    def set_robot_place_board(self, robot_place_board):
        """Установка данных в регистры."""
        self.robot_place_board = robot_place_board
        print(f"Modbus - Робот положи плату. {self.robot_place_board}")

    
    def get_subrobot_take_board(self):
        """Получение данных из регистров."""
        return self.subrobot_take_board
    

    def set_robot_take_board(self, robot_take_board):
        """Установка данных в регистры."""
        self.robot_take_board = robot_take_board
        print(f"Modbus - Робот забери плату с ложа.")


#############################################################################################

class Table:
    def __init__(self):
        self.lodge1 = None
        self.lodge2 = None

    def pause(self):
        time.sleep(2)

    def robot_place_board_on_table1_lodge1_side(self):
        print("Робот <- Положи плату на стол 1 ложе1 сторона.")
        self.pause()
        return "Робот -> Плату положил."

    def robot_place_board_on_table1_lodge2_side(self):
        print("Робот <- Положи плату на стол 1 ложе2 сторона.")
        self.pause()
        return "Робот -> Плату положил."

    def robot_take_board_from_lodge1(self):
        print("Робот <- Забери плату с ложе 1.")
        self.pause()
        return "Робот -> Плату забрал."

    def robot_take_board_from_lodge2(self):
        print("Робот <- Забери плату с ложе 2.")
        self.pause()
        return "Робот -> Плату забрал."

    def robot_place_board_on_lodge1(self):
        print("Робот <- Положи плату ложе 1.")
        self.pause()
        self.lodge1 = "Плата 1"
        return "Робот -> Плату положил."

    def robot_place_board_on_lodge2(self):
        print("Робот <- Положи плату ложе 2.")
        self.pause()
        self.lodge2 = "Плата 2"
        return "Робот -> Плату положил."

    def regul_move_board_right(self):
        print("Регул <- Сдвинь плату вправо.")
        self.pause()
        return "Регул -> Сдвинул."

    def regul_move_board_to_free_lodge1(self):
        print("Регул <- Сдвинь плату освободив ложе1.")
        self.pause()
        self.lodge1 = None
        return "Регул -> Сдвинул."

    def regul_move_board_to_free_lodge2(self):
        print("Регул <- Сдвинь плату освободив ложе2.")
        self.pause()
        self.lodge2 = None
        return "Регул -> Сдвинул."

    def regul_lower_soldering_iron_lodge2(self):
        print("Регул <- Опусти прошивальщик ложе 2.")
        self.pause()
        return "Регул -> Опустил."

    def regul_lower_soldering_iron(self):
        print("Регул <- Опусти прошивальщик на ложе")
        self.pause()
        return "Регул -> Опустил."

    def regul_raise_soldering_iron(self):
        print("Регул <- Подними прошивальщик.")
        self.pause()
        return "Регул -> Поднял."

    def server_start_stitching(self):
        print("Сервер <- Начни шить.")
        self.pause()
        return "Сервер -> Ответ по прошивке (хорошо/плохо)."
    
    def make_photo_from_CAM(self):
        print("Камера <- Сделай фото штрихкода платы")
        self.pause()
        return "Камера -> Фото получено"

    # Метод для первого цикла
    def first_cycle(self):
        print("****ЦИКЛ SETUP******")

        
        # Ложим плату на ложе 1
        result = self.robot_place_board_on_lodge1()
        print(result)
        # 100 - забрать плату из тары
        # 200 - уложить в ложемент тетстирования
        modbus_provider.set_robot_place_board(100)
        sub = modbus_provider.get_subrobot_place_board()
        while True:
            sub = modbus_provider.get_subrobot_place_board()
            if sub!=100:
                print(f"Ждем ответ от робота что плата взята из тары - {sub}")
            else:
                break
            time.sleep(1)    
        modbus_provider.set_robot_place_board(0)

        # Делаем фото платы
        result = self.make_photo_from_CAM()
        print(result)

        modbus_provider.set_robot_place_board(200)
        sub = modbus_provider.get_subrobot_place_board()
        while True:
            sub = modbus_provider.get_subrobot_place_board()
            if sub!=200:
                print(f"Ждем ответ от робота что плата уложена в ложемент1 - {sub}")
            else:
                break
            time.sleep(1)    
        modbus_provider.set_robot_place_board(0)

        # Сдвигаем стол осовобождая ложе2
        result = self.regul_move_board_to_free_lodge2()
        print(result)
        modbus_provider.set_Tablefree(1)
        sub = modbus_provider.get_Tablefree()
        while True:
            sub = modbus_provider.get_Tablefree()
            if sub!=1:
                print(f"Ждем ответ о том что стол сдвинут - {sub}")
            else:
                break
            time.sleep(1)    
        modbus_provider.set_Tablefree(0)

        # Делаем фото платы
        result = self.make_photo_from_CAM()
        print(result)

        # Ложим плату на ложе 2
        result = self.robot_place_board_on_lodge2()
        print(result)
        # 100 - забрать плату из тары
        # 200 - уложить в ложемент тетстирования
        modbus_provider.set_robot_place_board(100)
        sub = modbus_provider.get_subrobot_place_board()
        while True:
            sub = modbus_provider.get_subrobot_place_board()
            if sub!=100:
                print(f"Ждем ответ от робота что плата взята из тары - {sub}")
            else:
                break
            time.sleep(1)    
        modbus_provider.set_robot_place_board(0)

        modbus_provider.set_robot_place_board(200)
        sub = modbus_provider.get_subrobot_place_board()
        while True:
            sub = modbus_provider.get_subrobot_place_board()
            if sub!=200:
                print(f"Ждем ответ от робота что плата уложена в ложемент2 - {sub}")
            else:
                break
            time.sleep(1)    
        modbus_provider.set_robot_place_board(0)

        print("Стол 1ложе занято")
        print("Стол 2ложе занято")
        print("Регул -> Ничего не делай.")
        #"Регул <- Опусти прошивальщик ложе 1."
        result = self.regul_lower_soldering_iron()
        print(result)
        # "РСервер <- Начни шить. ложе 1"
        result = self.server_start_stitching()
        print(result)
        # "Регул <- Подними прошивальщик. ложе 1"
        result = self.regul_raise_soldering_iron()
        print(result)
        self.pause()
        print("****ЦИКЛ SETUP Завершен******")

    # Метод для защиты что нет плат
    def defence_cycle(self):
        print("******ЦИКЛ DEFENCE*******")
        
        # 1 Регул <- Сдвинь плату освободив ложе1.
        result = self.regul_move_board_to_free_lodge1()
        print(result)
        modbus_provider.set_Tablefree(1)
        sub = modbus_provider.get_Tablefree()
        while True:
            sub = modbus_provider.get_Tablefree()
            if sub!=1:
                print(f"Ждем ответ о том что стол сдвинут - {sub}")
            else:
                break
            time.sleep(1)    
        modbus_provider.set_Tablefree(0)

        
        # Связь по мадбас с регулом
        # 2. Робот <- Забери плату с ложе 1.
        result = self.robot_take_board_from_lodge1()
        print(result)
        sub = 0
        modbus_provider.set_robot_take_board(1)
        sub = modbus_provider.get_subrobot_take_board()
        while True:
            sub = modbus_provider.get_subrobot_take_board()
            if sub!=1:
                print(f"Ждем ответ от робота, что плату забрал {sub}")
            else:
                break

            time.sleep(1)
        modbus_provider.set_robot_take_board(0)  


        # Регул <- Сдвинь плату освободив ложе2.
        result = self.regul_move_board_to_free_lodge2()
        print(result)
        modbus_provider.set_Tablefree(1)
        sub = modbus_provider.get_Tablefree()
        while True:
            sub = modbus_provider.get_Tablefree()
            if sub!=1:
                print(f"Ждем ответ о том что стол сдвинут - {sub}")
            else:
                break
            time.sleep(1)    
        modbus_provider.set_Tablefree(0)

        # 4. Робот <- Забери плату с ложе 2.
        result = self.robot_take_board_from_lodge2()
        print(result)
        sub = 0
        modbus_provider.set_robot_take_board(1)
        sub = modbus_provider.get_subrobot_take_board()
        while True:
            sub = modbus_provider.get_subrobot_take_board()
            if sub!=1:
                print(f"Ждем ответ от робота, что плату забрал {sub}")
            else:
                break

            time.sleep(1)
        modbus_provider.set_robot_take_board(0)
        print("******ЦИКЛ DEFENCE Завершен*******")

    
    
    # Метод для основного цикла
    def main_cycle(self):
        while True:
            if self.lodge1 is None and self.lodge2 is None:
                self.lodge1 = "Плата 1"
                self.lodge2 = "Плата 2"
                self.pause()
            ####################### 2 операция на столе
            # Регул <- Сдвинь плату освободив ложе1.
            result = self.regul_move_board_to_free_lodge1()
            print(result)
            # 4. Робот <- Забери плату с ложе 1.
            result = self.robot_take_board_from_lodge1()
            print(result)
            print("Стол 1ложе свободен.")
            # Робот <- Положи плату ложе 1.
            result = self.robot_place_board_on_lodge1()
            print(result)
            # Фоткаем плату перед тем как пместить на ложе
            result = self.make_photo_from_CAM()
            print(result)
            print("Стол 1ложе занято.")
            #  Регул <- Опусти прошивальщик (плата на ложе2).
            result = self.regul_lower_soldering_iron()
            # "РСервер <- Начни шить. ложе 2"
            result = self.server_start_stitching()
            print(result)
            # Регул <- Подними прошивальщик.
            result = self.regul_raise_soldering_iron()
            print(result)

            ####################### 3 операция на столе
            # Регул <- Сдвинь плату освободив ложе2.
            result = self.regul_move_board_to_free_lodge2()
            print(result)
            # 4. Робот <- Забери плату с ложе 2.
            result = self.robot_take_board_from_lodge2()
            print(result)
            print("Стол 2ложе свободен.")
            # Робот <- Положи плату ложе 2.
            result = self.robot_place_board_on_lodge2()
            print(result)
            # Фоткаем плату перед тем как пместить на ложе
            result = self.make_photo_from_CAM()
            print(result)
            print("Стол 2ложе занято.")
            #  Регул <- Опусти прошивальщик (плата на ложе2).
            result = self.regul_lower_soldering_iron()
            # "РСервер <- Начни шить. ложе 1"
            result = self.server_start_stitching()
            print(result)
            # Регул <- Подними прошивальщик.
            result = self.regul_raise_soldering_iron()
            print(result)
            print("********************************************")



if __name__ == "__main__":

    # Создание объекта и выполнение алгоритма
    table = Table()
    modbus_provider = ModbusProvider()

    """
    # Выполнение первого цикла
    flag1 = True
    if flag1 == True:
        table.defence_cycle()
        flag1 = False
    """
    

    # Выполнение первого цикла
    flag = True
    if flag == True:
        table.first_cycle()
        flag = False


    table.main_cycle()
    