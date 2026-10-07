import logging
import time
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading
import socket


# Пользовательский класс камеры
# mport CameraClass as CAM
import CameraSocket
 
 # Пользовательский класс БД
import SQLite as SQL

# Поьзовательский класс провайдера Иглостола
import ProviderIgleTable as Igable


# Глобальные ящик и ясейка 
Tray1 = 0
Cell1 = 0
Order = "ЗНП-0005747"

dict_Table1 = {
    'Reg_move_Table': 0,
    'sub_Reg_move_Table': 0,
    'Reg_updown_Botloader': 0,
    'sub_Reg_updown_Botloader': 0,
    'Rob_Action': 0,
    'sub_Rob_Action': 0
    
}

# Set up basic logging configuration
logging.basicConfig(
    filename='RTK.log',
    level=logging.INFO,
    format=' %(asctime)s - MAIN - %(levelname)s - %(message)s'
)

################################################# IgleTable Communication Class ###################################
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
try:
    # Берем адрес текущего хоста
    s.connect(("8.8.8.8", 80))
    ip = s.getsockname()[0]
finally:
    s.close()
print(f"Локальный IP-адрес: {ip}")
   
igle_table = Igable.IgleTable(
        urlIgleTabeControl=f"http://192.168.1.100:5000/nails_table/start_test_board_with_rtk",
        urlStatusFromIgleTabe=f"http://192.168.1.100:5003/get_test_results",

        module_type="R050 DI 16 011-000-AAA",
        stand_id="nt_kto_rtk_1",
        serial_number_8="1",
        data_matrix=["11"],
        firmwares = [
            {
            "fw_type": "MCU",
            "fw_path": "C:\\nails_table_bridge\\plc050_di16012-full.hex",
            "fw_version": "1.0.36.0"
            }
        ]
    )
################################################# IgleTable Communication Class ###################################


################################################# START SQL Communication class ###################################
 
try:
        # Create an instance of DatabaseConnection
        db_connection = SQL.DatabaseConnection()
except Exception as e:
        logging.error(f"Error Create an instance of DatabaseConnection: {e}")
 ################################################# STOP SQL Communication class ###################################




################################################# START OPC Communication class ###################################


################################################# START OPC Communication class l ###################################


class ModbusProvider:
    """Class MODBUS Communication with Modbus regul"""
    global Tray1
    global Cell1
    def __init__(self):
        self.store = ModbusSlaveContext(
            hr=ModbusSequentialDataBlock(0, [0] * 100)
        )
        self.lock = threading.Lock()

        self.Reg_move_Table = 0             # Move Table
        self.Reg_updown_Botloader = 0        # Move botloader
        self.Rob_Action = 0                 # Action to Robot


        self.server_thread = threading.Thread(target=self.run_modbus_server, daemon=True)
        self.server_thread.start()

        self.update_thread = threading.Thread(target=self.update_registers, daemon=True)
        self.update_thread.start()

    def run_modbus_server(self):
        context = ModbusServerContext(slaves=self.store, single=True)
        print("Starting Modbus TCP server on localhost:502")
        try:
            StartTcpServer(context, address=("192.168.1.100", 502)) # "192.168.1.100"  localhost
        except Exception as e:
            print(f"Error starting Modbus server: {e}")

    
    # Modbus registers read/write
    def update_registers(self):
        global dict_Table1

        while True:
            try:
                with self.lock:
                    dict_Table1["sub_Reg_move_Table"] = self.store.getValues(3, 1, count=1)[0]
                    dict_Table1["sub_Reg_updown_Botloader"] = self.store.getValues(3, 3, count=1)[0]
                    dict_Table1["sub_Rob_Action"] = self.store.getValues(3, 5, count=1)[0]

                    self.Reg_move_Table = dict_Table1["Reg_move_Table"]
                    self.Reg_updown_Botloader = dict_Table1["Reg_updown_Botloader"]
                    self.Rob_Action = dict_Table1["Rob_Action"]


                    self.store.setValues(3, 0, [self.Reg_move_Table])
                    self.store.setValues(3, 2, [self.Reg_updown_Botloader])
                    self.store.setValues(3, 4, [self.Rob_Action])

                    self.store.setValues(3, 6, [Tray1])
                    self.store.setValues(3, 8, [Cell1])
            except Exception as e:
                print(f"Error updating registers: {e}")
            time.sleep(1)

################################################# START MODBUS Communication class with Modbus regul ###################################


################################################# START TABLE CLASS #####################################################################
class Table:
    """ TABLE CLASS"""
    global Tray1
    global Cell1
    global Order

    def __init__(self, name, initial_dict):
        self.name = name
        self.data = initial_dict


    # Method write registers in modbus through modbus_provider
    def change_value(self, key, new_value):
        with modbus_provider.lock:
            if key in self.data:
                self.data[key] = new_value
                # print(f"Updated {key} to {new_value} in {self.name}.")
            else:
                print(f"Key '{key}' not found in {self.name}.")

    # Method read registers in modbus through modbus_provider
    def read_value(self, key):
        with modbus_provider.lock:
            if key in self.data:
                result = self.data[key]
                # print(f"Read {key}: {result} from {self.name}.")
            else:
                print(f"Key '{key}' not found in {self.name}.")
            return result

    




    ############# ****ЦИКЛ MAIN ******"
    def main(self):
        global Tray1
        global Cell1
        print("****ЦИКЛ MAIN")

        # input("Нажми инпут")


        ##########################################################
        # Делаем фото платы
        print("1 Камера <- сделай фото")
        for i in range(3):
            try:
                photodata = CameraSocket.photo()
                photodata = photodata[1]
                print(f"С камеры получен ID {photodata}")
            except Exception as e:
                print(f"Ошибка: камера недоступна (photo camera not available). Детали: {e}")
            time.sleep(1)

        
        ##########################################################


        #input("Нажми инпут")

        ##########################################################
        # 2. Регул <- Опусти прошивальщик ложе 2.
        print("2 Регул <- Опусти прошивальщик ложе 2")
        self.change_value('Reg_updown_Botloader', 103)
        while True:
            result1 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 103:
                print(f"Ждем ответ от регула, что прошивальщик опущен= {result1}")
            elif result1 == 404:
                print(f"От регула получен код 200 на на операции опустить прошивальщик")
            else:
                break
            time.sleep(1)
        self.change_value('Reg_updown_Botloader', 0)
        result1 = 0

        
        ##########################################################

        # input("Нажми инпут")
        
        ##########################################################
        # Команда на прошивку
        print("3 Прошивальщик <- Команда на прошивку")
        # БД Блок нааначения стола
        db_connection.db_connect()
        
        # Берем свободный id в рамках заказа
        record_id = db_connection.setTable(Order)
        # БД Блок нааначения стола
        print(f"БД - получили свободный заказ {record_id}")

        # БД Блок ПРОШИВКИ
        time.sleep(2)

        
        igle_table.control_igle_table()

        

        while True:
            # Получаем данные о результате от стола через сверер РТК
            resultTest = igle_table.recentData()
            print("Результат запроса:")

            loadresult = resultTest['status_code']
            print(f"Rresult from IgleTable {loadresult}")
            
            # Выводим все данные
            if loadresult!= "OK":
                print(f"Ждем ответ от прошивальщика")
            else:
                break
            time.sleep(1)
        
        # Выводим все данные
        for key, value in resultTest.items():
            print(f"{key}: {value}")
        # Проверяем, что ответ успешный
        if resultTest.get("status_code") == "OK":
            # Извлекаем переменные
            data_matrix = resultTest.get("data_matrix")
            log_path = resultTest.get("log_path")
            report_path = resultTest.get("report_path")
            serial_number_8 = resultTest.get("serial_number_8")
            stand_id = resultTest.get("stand_id")
            test_result = resultTest.get("status_code")
            error_description = resultTest.get("error_description")
            # Запись в БД результатов прошивки
            db_connection.set_BoardTest_Result(record_id, stand_id, serial_number_8, data_matrix, test_result, log_path, report_path, error_description)
            # Привязываем Data matrix к серийнику
            db_connection.ConnectPhotoSerial(record_id, photodata, loadresult)
            # Рбот убери пллаиту в прошитые все успешно.
        else:
            print("Ошибка: не удалось получить данные, запись в БД не выполнена.")

            # Роботу буери плату в прошитые не успешно

            # выставить результат тестирования и привязать плату
            # 200 - успешно
            # 404 - возгникла ошибка/пишем лог ошибки в базу
            # если 404 говорим роботу убери в брак
               
        
        # Очищаем перменные результата
        photodata = None
        record_id = 0
        loadresult = 0
        resultTest = None
        # если получен ответ об успешной прошивке то производим привязывание платы к штрихкоду иначе в брак
        # Получить данные с сервера
        
        ##########################################################

        #input("Нажми инпут")


        ##########################################################
        # 4 Регул <- Подними прошивальщик.
        print("4. Регул <- Подними прошивальщик.")
        self.change_value('Reg_updown_Botloader', 104)
        while True:
            result1 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 104:
                print(f"Ждем ответ от регула, что прошивальщик поднят= {result1}")
            elif result1 == 404:
                print(f"От регула получен код 200 на на операции поднять прошивальщик")
            else:
                break
            time.sleep(1)
        self.change_value('Reg_updown_Botloader', 0)
        result1 = 0
        ##########################################################


        
        #input("Нажми инпут")




        ##########################################################
        # 5. Регул <- Сдвинь плату освободив ложе2.
        print("5 Регул <- Сдвинь плату освободив ложе2")
        self.change_value('Reg_move_Table', 102)
        while True:
            result1 = self.read_value("sub_Reg_move_Table")
            if result1 != 102:
                print(f"Ждем ответ о том что стол сдвинут - сейчас значение = {result1}")
            elif result1 == 404:
                print(f"От регула получен код 200 на операции движения стола")
            else:
                break
            time.sleep(1)
        self.change_value('Reg_move_Table', 0)
        result1 = 0
        ##########################################################


        
        #input("Нажми инпут")


        
        ##########################################################
        # Делаем фото платы
        print("6 Камера <- сделай фото")
        for i in range(3):
            try:
                photodata = CameraSocket.photo()
                photodata = photodata[1]
                print(f"С камеры получен ID {photodata}")
            except Exception as e:
                print(f"Ошибка: камера недоступна (photo camera not available). Детали: {e}")
            time.sleep(1)
        ##########################################################


        #input("Нажми инпут")

        ##########################################################
        # 7. Регул <- Опусти прошивальщик ложе 2.
        print("7 Регул <- Опусти прошивальщик ложе 2")
        self.change_value('Reg_updown_Botloader', 103)
        while True:
            result1 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 103:
                print(f"Ждем ответ от регула, что прошивальщик опущен= {result1}")
            elif result1 == 404:
                print(f"От регула получен код 200 на на операции опустить прошивальщик")
            else:
                break
            time.sleep(1)
        self.change_value('Reg_updown_Botloader', 0)
        result1 = 0
        time.sleep(2)
        ##########################################################

        #input("Нажми инпут")


        ##########################################################
        # Команда на прошивку
        print("3 Прошивальщик <- Команда на прошивку")
        # БД Блок нааначения стола
        db_connection.db_connect()
        
        # Берем свободный id в рамках заказа
        record_id = db_connection.setTable(Order)
        # БД Блок нааначения стола
        print(f"БД - получили свободный заказ {record_id}")

        # БД Блок ПРОШИВКИ
        time.sleep(2)

        
        igle_table.control_igle_table()

        

        while True:
            # Получаем данные о результате от стола через сверер РТК
            resultTest = igle_table.recentData()
            print("Результат запроса:")

            loadresult = resultTest['status_code']
            print(f"Rresult from IgleTable {loadresult}")
            
            # Выводим все данные
            if loadresult!= "OK":
                print(f"Ждем ответ от прошивальщика")
            else:
                break
            time.sleep(1)
        
        # Выводим все данные
        for key, value in resultTest.items():
            print(f"{key}: {value}")
        # Проверяем, что ответ успешный
        if resultTest.get("status_code") == "OK":
            # Извлекаем переменные
            data_matrix = resultTest.get("data_matrix")
            log_path = resultTest.get("log_path")
            report_path = resultTest.get("report_path")
            serial_number_8 = resultTest.get("serial_number_8")
            stand_id = resultTest.get("stand_id")
            test_result = resultTest.get("status_code")
            error_description = resultTest.get("error_description")
            # Запись в БД результатов прошивки
            db_connection.set_BoardTest_Result(record_id, stand_id, serial_number_8, data_matrix, test_result, log_path, report_path, error_description)
            # Привязываем Data matrix к серийнику
            db_connection.ConnectPhotoSerial(record_id, photodata, loadresult)
            # Рбот убери пллаиту в прошитые все успешно.
        else:
            print("Ошибка: не удалось получить данные, запись в БД не выполнена.")

            # Роботу буери плату в прошитые не успешно

            # выставить результат тестирования и привязать плату
            # 200 - успешно
            # 404 - возгникла ошибка/пишем лог ошибки в базу
            # если 404 говорим роботу убери в брак
               
        
        # Очищаем перменные результата
        photodata = None
        record_id = 0
        loadresult = 0
        resultTest = None
        # если получен ответ об успешной прошивке то производим привязывание платы к штрихкоду иначе в брак
        # Получить данные с сервера

        # БД Блок ПРОШИВКИ  ##

        ##########################################################



        # input("Нажми инпут")



        ##########################################################
        # 8 Регул <- Подними прошивальщик.
        print("8. Регул <- Подними прошивальщик.")
        self.change_value('Reg_updown_Botloader', 104)
        while True:
            result1 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 104:
                print(f"Ждем ответ от регула, что прошивальщик поднят= {result1}")
            elif result1 == 404:
                print(f"От регула получен код 200 на на операции поднять прошивальщик")
            else:
                break
            time.sleep(1)
        self.change_value('Reg_updown_Botloader', 0)
        result1 = 0


        

        
        # input("Нажми инпут")




        ##########################################################
        # 5. Регул <- Сдвинь плату освободив ложе2.
        print("5 Регул <- Сдвинь плату освободив ложе2")
        self.change_value('Reg_move_Table', 101)
        while True:
            result1 = self.read_value("sub_Reg_move_Table")
            if result1 != 101:
                print(f"Ждем ответ о том что стол сдвинут - сейчас значение = {result1}")
            elif result1 == 404:
                print(f"От регула получен код 200 на операции движения стола")
            else:
                break
            time.sleep(1)
        self.change_value('Reg_move_Table', 0)
        result1 = 0
        ##########################################################


    
################################################# STOP TABLE CLASS #####################################################################


    def pause(self):
        time.sleep(2)

    


if __name__ == "__main__":


    modbus_provider = ModbusProvider()
    
    table1 = Table("Table 1", dict_Table1)
    
    

    """
    # Выполнение первого цикла
        flag1 = True
        if flag1 == True:
            table1.defence_cycle()
            flag1 = False
        
    """  
    

    
    """
    # Выполнение первого цикла
    flag = True
    if flag == True:
        table1.setup_cycle()
        flag = False
    """

    
    

    while True:
        table1.main()

