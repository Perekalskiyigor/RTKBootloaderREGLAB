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
        urlIgleTabeControl=f"http://{ip}:5000/nails_table/start_test_board_with_rtk",
        urlStatusFromIgleTabe=f"http://{ip}:5003/get_test_results",

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
            StartTcpServer(context, address=("localhost", 502)) # "192.168.1.100"
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

    # The first cycle Protect Table in the start work
    def defence_cycle(self):
        print("******ЦИКЛ DEFENCE*******")
        print("1 Регул <- Сдвинь плату освободив ложе1.")
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

        print("2 Робот <- Забери плату с ложе 1.")
        self.change_value('Rob_Action', 231)
        while True:
            result1 = self.read_value("sub_Rob_Action")

            if result1 != 231:
                print(f"Ждем ответ от робота, что плату забрал получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции взять плату с ложа")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)

        print("3 Регул <- Сдвинь плату освободив ложе2.")
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

        print("4 Робот <- Забери плату с ложе 2.")
        self.change_value('Rob_Action', 232)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 232:
                print(f"Ждем ответ от робота, что плату забрал получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции взять плату с ложа")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)

        print("******ЦИКЛ DEFENCE Завершен*******")


    ############# ****ЦИКЛ SETUP ******"
    def setup_cycle(self):
        print("****ЦИКЛ SETUP******")
        global Tray1
        global Cell1
        global Order

        # 5 Робот <- Забери плату из тары
        print("5 Робот <- забрать плату из тары")
        # Передаем ящик из которого нужно забрать и номер ячейки
        Tray1 = 1
        Cell1 = Cell1 + 1
        self.change_value('Rob_Action', 210)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 210:
                print(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции забрать из тары плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)

        # 6 Делаем фото платы
        for i in range(3):
            try:
                a = CameraSocket.photo()
                print(a)
            except Exception as e:
                print(f"Ошибка: камера недоступна (photo camera not available). Детали: {e}")
            time.sleep(1)


        # 7 Робот <- Уложи плату в ложемент тетситрования
        print("7 Робот <- Уложи плату в ложемент тетситрования 2")
        self.change_value('Rob_Action', 222)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 222:
                print(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции забрать из тары плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)



        # 8 Регул - Сдвигаем стол осовобождая ложе1
        print("8 Регул <- Сдвинь плату освободив ложе1.")
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


        # 9 Робот <- Забери плату из тары
        print("9 Робот <- забрать плату из тары")
        # Передаем ящик из которого нужно забрать и номер ячейки
        Tray1 = 1
        Cell1 = Cell1 + 1

        self.change_value('Rob_Action', 210)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 210:
                print(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции забрать из тары плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)

        # 10 Делаем фото платы
        print("10 Камера <- сделай фото")
        for i in range(3):
            try:
                a = CameraSocket.photo()
                print(a)
            except Exception as e:
                print(f"Ошибка: камера недоступна (photo camera not available). Детали: {e}")
            time.sleep(1)
        

        # 11 Робот <- Уложи плату в ложемент тетситрования
        print("11 Робот <- Уложи плату в ложемент тетситрования 1")
        self.change_value('Rob_Action', 221)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 221:
                print(f"Ждем ответ от робота, что плату уложили = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции уложить плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        print("Стол 1ложе занято")
        print("Стол 2ложе занято")
        print("****ЦИКЛ SETUP Завершен******")
    ############# ****ЦИКЛ SETUP END ******"

    ############# ****ЦИКЛ MAIN ******"
    def main(self):
        global Tray1
        global Cell1
        print("****ЦИКЛ MAIN")

        

        ############################# БД Блок нааначения стола #########################
        db_connection.db_connect()
        
        # Берем свободный id в рамках заказа
        record_id = db_connection.setTable(Order)
        ############################# БД Блок нааначения стола #########################
        print(f"Получение id {record_id}")


        ############################# БД Блок ПРОШИВКИ  ####################
        # 
        time.sleep(5)
        # Данные с камеры  
        photodata = "FF494"

        db_connection.db_connect()
        # Ждем пока прошьется

        
        # Команда на прошивку
        loadresult = igle_table.control_igle_table()

        

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
            db_connection.close_connection()
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

    ############################# БД Блок ПРОШИВКИ  ####################




        # 1. Регул <- Сдвинь плату освободив ложе2.
        print("1 Регул <- Сдвинь плату освободив ложе2")
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

        # 2.1. Робот <- Забери плату с ложе 2. # 2.2 Регул <- Опусти прошивальщик (плата на ложе1).
        print("2.1 Робот <- Забери плату с ложе 2.  2.2. Регул <- Опусти прошивальщик (плата на ложе1).")
        self.change_value('Rob_Action', 232)
        self.change_value('Reg_updown_Botloader', 103)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            result2 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 232 and result2 != 103:
                print(f"от робота = {result1}, от регула = {result2}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции взять плату с ложа")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        self.change_value('Reg_updown_Botloader', 0)
        print("Стол 2ложе свободен, прошивальщик опущен")

        result1 = 0
        result2 = 0


        # 3.1 Робот <- Уложи плату в тару # 3.2.1 Сервер <- Начни шить # 3.2.2 Сервер -> Ответ по прошивке (плохо, хорошо)
        print("3.1 Робот <- Уложи плату в тару.")
        print("3.2.1 Сервер <- Начни шить")
        print("3.2.2. Сервер -> Ответ по прошивке (плохо, хорошо)")
        self.change_value('Rob_Action', 241)
        while True:
            result1 = self.read_value("sub_Rob_Action")

            if result1 != 241:
                print(f"от робота = {result1}, от регула = {result2}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции взять плату с ложа")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        print("плата уложена в тару")
        result1 = 0

        ############################# БД Блок нааначения стола #########################
        # если получен ответ об успешной прошивке то производим привязывание платы к штрихкоду иначе в брак
        db_connection.db_connect()
        # Берем свободный id в рамках заказа
        record_id = db_connection.setTable(Order)
        ############################# БД Блок нааначения стола #########################

        # 4.1 Робот <- Забери плату из тары # 4.2 Регул <- Подними прошивальщик.
        print("4.1 Робот <- забрать плату из тары # 4.2 Регул <- Подними прошивальщик")
        # Передаем ящик из которого нужно забрать и номер ячейки
        Tray1 = 1
        Cell1 = Cell1 + 1

        self.change_value('Rob_Action', 210)
        self.change_value('Reg_updown_Botloader', 104)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            result2 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 210 and result2 != 104:
                print(f"от робота = {result1}, от регула = {result2}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции забрать из тары плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        self.change_value('Reg_updown_Botloader', 0)
        result1=0
        result2=0
        
        # 5 Делаем фото платы
        print("5 Камера <- сделай фото")
        try:
            res,photodata = CameraSocket.photo()
            if res == 200 and photodata is not None:
                print(f"Recieve datamatrixcode {photodata}")
                # Сохраняем в бд с привязкой к плате
            else:
                print("Error Recieve datamatrixcode")
        except Exception as e:
                print(f"Ошибка: камера недоступна (photo camera not available). Детали: {e}")
        time.sleep(1)

        
        # 6 Робот <- Уложи плату в ложемент тетситрования 2
        print("6 Робот <- Уложи плату в ложемент тетситрования 2")
        self.change_value('Rob_Action', 222)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 222:
                print(f"Ждем ответ от робота, что плату уложили = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции уложить плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        print("Стол 1ложе занято")
        result1=0

        # 7. Регул <- Сдвинь плату освободив ложе1.
        print("7 Регул <- Сдвинь плату освободив ложе1")
        self.change_value('Reg_move_Table', 101)
        while True:
            result1 = self.read_value("sub_Reg_move_Table")
            if result1 != 101:
                print(f"от робота = {result1}, от регула = {result2}")
            elif result1 == 404:
                print(f"От регула получен код 200 на операции движения стола")
            else:
                break
            time.sleep(1)
        self.change_value('Reg_move_Table', 0)
        result1 = 0
        print("Стол 1ложе свободен")

        # 8.1 Робот <- Забери плату с ложе 1. # 8.2 Регул <- Опусти прошивальщик (плата на ложе2).
        print("# 8.1 Робот <- Забери плату с ложе 1. # 8.2 Регул <- Опусти прошивальщик (плата на ложе2).")
        self.change_value('Reg_updown_Botloader', 103)
        self.change_value('Rob_Action', 231)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            result2 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 231 and result2!= 103:
                print(f"от робота = {result1}, от регула = {result2}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции взять плату с ложа")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        self.change_value('Reg_updown_Botloader', 0)
        result1 = 0
        result2 = 0

        ############################# БД Блок связываания серийника и платы  ####################
        # 
        time.sleep(5)
        photodata = "FF494"
        db_connection.db_connect()
        # Ждем пока прошьется
        loadresult = 200
        if loadresult ==200:
            loadresult = igle_table.control_igle_table()
            # Получаем данные о результате от стола через сверер РТК
            resultTest = igle_table.recentData()
            print("Результат запроса:")
            # Выводим все данные
            for key, value in resultTest.items():
                print(f"{key}: {value}")
            # Проверяем, что ответ успешный
            if resultTest.get("status_code") == 200:
                # Извлекаем переменные
                data_matrix = resultTest.get("data_matrix")
                log_path = resultTest.get("log_path")
                report_path = resultTest.get("report_path")
                serial_number_8 = resultTest.get("serial_number_8")
                stand_id = resultTest.get("stand_id")
                test_result = resultTest.get("test_result")
                # Запись в БД
                db_connection.set_BoardTest_Result(record_id, stand_id, serial_number_8, data_matrix, test_result, log_path, report_path)

                db_connection.ConnectPhotoSerial(record_id, photodata, loadresult)
                db_connection.close_connection()
            else:
                print("Ошибка: не удалось получить данные, запись в БД не выполнена.")
                # выставить результат тестирования и привязать плату
                # 200 - успешно
                # 404 - возгникла ошибка/пишем лог ошибки в базу
                # если 404 говорим роботу убери в брак
               
        else:
            print ("Плата не прошита уводим в брак и проставляем причину")
        
        # Очищаем перменные результата
        photodata = None
        record_id = 0
        loadresult = 0
        resultTest = None
        # если получен ответ об успешной прошивке то производим привязывание платы к штрихкоду иначе в брак
        # Получить данные с сервера
        
        




        
        ############################# БД  Блок связываания серийника и платы #########################

        # 9.1 Робот <- Уложи плату в тару # 9.2.1 Сервер <- Начни шить # 9.2.2 Сервер -> Ответ по прошивке (плохо, хорошо)
        print("9.1 Робот <- Уложи плату в тару.")
        print("9.2.1 Сервер <- Начни шить")
        print("9.2.2. Сервер -> Ответ по прошивке (плохо, хорошо)")
        self.change_value('Rob_Action', 241)
        while True:
            result1 = self.read_value("sub_Rob_Action")

            if result1 != 241:
                print(f"Ждем ответ от робота, что плату забрал получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции взять плату с ложа")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        print("плата уложена в тару")
        result1 = 0

        # 10.1 Робот <- Забери плату из тары # 10.2 Регул <- Подними прошивальщик.
        print("10.1 Робот <- забрать плату из тары # 10.2 Регул <- Подними прошивальщик")
        # Передаем ящик из которого нужно забрать и номер ячейки
        Tray1 = 1
        Cell1 = Cell1 + 1

        self.change_value('Rob_Action', 210)
        self.change_value('Reg_updown_Botloader', 104)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            result2 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 210 and result2 !=104:
                print(f"от робота = {result1}, от регула = {result2}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции забрать из тары плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        self.change_value('Reg_updown_Botloader', 0)
        result1=0
        result2 = 0

        # 11 Делаем фото платы
        print("11 Камера <- сделай фото")
        for i in range(3):
            try:
                a = CameraSocket.photo()
                print(a)
            except Exception as e:
                print(f"Ошибка: камера недоступна (photo camera not available). Детали: {e}")
            time.sleep(1)
        

        # 12 Робот <- Уложи плату в ложемент тетситрования 1
        print("12 Робот <- Уложи плату в ложемент тетситрования 1")
        self.change_value('Rob_Action', 221)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 221:
                print(f"Ждем ответ от робота, что плату уложили = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции уложить плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1=0

        print("****ЦИКЛ MAIN END")

    ############# ****ЦИКЛ MAIN END ******"




    
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

    
    

    table1.main()

