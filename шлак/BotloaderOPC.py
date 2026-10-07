import logging
import time
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading
import socket
from opcua import Client
from opcua import ua
import logging

# Пользовательский класс камеры
# mport CameraClass as CAM
import CameraSocket
 
 # Пользовательский класс БД
import SQLite as SQL

# Поьзовательский класс провайдера Иглостола
import ProviderIgleTable as Igable

# Пользовательский калсс прошивальщика
import Botloader as Bot

# Класс связи с 1С
import Provider1C


# Глобальные ящик и ясейка 
Tray1 = 0
Cell1 = 0
Order = "ЗНП-12986.1.1"
# данные с платы для цикла main и сетапа
photodata = None


dict_Table1 = {
    'Reg_move_Table': 0,
    'sub_Reg_move_Table': 0,
    'Reg_updown_Botloader': 0,
    'sub_Reg_updown_Botloader': 0,
    'Rob_Action': 0,
    'sub_Rob_Action': 0
    
}

# Словарь опс интерфейса глобальный
dict_OPC = {
    "ns=2;s=Application.PLC_PRG.VAL2": 0,
    "ns=2;s=Application.PLC_PRG.VAL1": 0,
    "ns=2;s=Application.PLC_PRG.orderNode":""
}

shared_data = {
    1: {
        'Reg_move_Table': 0,
        'sub_Reg_move_Table': 0,
        'Reg_updown_Botloader': 0,
        'sub_Reg_updown_Botloader': 0,
        'Rob_Action': 0,
        'sub_Rob_Action': 0
        },
    2: {
        'Reg_move_Table': 0,
        'sub_Reg_move_Table': 0,
        'Reg_updown_Botloader': 0,
        'sub_Reg_updown_Botloader': 0,
        'Rob_Action': 0,
        'sub_Rob_Action': 0
        }
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
        urlStatusFromIgleTabe=f"http://192.168.1.100:5003/get_test_results"
    )
################################################# IgleTable Communication Class ###################################


################################################# START SQL Communication class ###################################
 
# Класс для синхронизации с базой данных и обновления глобального словаря
class DatabaseSynchronizer:
    def __init__(self, order):
        self.order = order
        self.stop_event = threading.Event()  # Событие для остановки потока
        self.update_thread = threading.Thread(target=self.update_data, daemon=True)
        self.update_thread.start()
        self.lock = threading.Lock()

    def update_data(self):
        """Метод для обновления данных в глобальном словаре с базы данных"""
        while not self.stop_event.is_set():  # Проверка на остановку потока
            try:
                # Попытка получения данных по заказу из базы данных
                db_connection = SQL.DatabaseConnection()
                result = db_connection.getDatafromOOPC(self.order)
                
                if result:
                    order_number, module, fw_version, last_count, common_count, success_count, nonsuccess_count = result

                    # print(f"Номер заказа: {order_number}")
                    # print(f"Модуль: {module}")
                    # print(f"Версия ПО: {fw_version}")
                    # print(f"Количество оставшихся: {last_count}")
                    # print(f"Общее количество записей: {common_count}")
                    # print(f"С успешным report_path: {success_count}")
                    # print(f"С успешным log_path: {nonsuccess_count}")

                    # Обновление глобального словаря с данными из базы
                    with self.lock:
                        dict_OPC["order_number"] = order_number
                        dict_OPC["module"] = module
                        dict_OPC["fw_version"] = fw_version
                        dict_OPC["last_count"] = last_count
                        dict_OPC["common_count"] = common_count
                        dict_OPC["success_count"] = success_count
                        dict_OPC["nonsuccess_count"] = nonsuccess_count
                else:
                    print("Данные по заказу не найдены или произошла ошибка.")

            except Exception as e:
                logging.error(f"Ошибка при синхронизации с базой данных: {e}")
            
            # Пауза 1 секунда перед следующей попыткой
            time.sleep(1)

    def stop(self):
        """Метод для остановки потока"""
        self.stop_event.set()  # Устанавливаем событие, чтобы остановить поток


# Создаем и запускаем процесс синхронизации с БД
db_sync = DatabaseSynchronizer(Order)
 ################################################# STOP SQL Communication class ###################################




################################################# START OPC Communication class ###################################



class OPCClient:
    def __init__(self, url):
        self.url = url
        self.lock = threading.Lock()

        self.client = Client(url)
        self.running = False
        self.stop_event = threading.Event()  # Event to signal when to stop the threads

        # Start threads after initializing the client
        self.server_thread = threading.Thread(target=self.connect, daemon=True)
        self.update_thread = threading.Thread(target=self.update_registers, daemon=True)

        self.server_thread.start()
        self.update_thread.start()

    def connect(self):
        try:
            self.client.connect()
            print(f"Подключено к {self.url}")
        except Exception as e:
            print(f"Ошибка подключения: {e}")

    def disconnect(self):
        try:
            self.client.disconnect()
            print("Отключено от OPC сервера")
        except Exception as e:
            print(f"Ошибка отключения: {e}")

    def update_registers(self):
        """ Метод обгновления пременных опс и словаря"""
        while not self.stop_event.is_set():  # Check if the stop event is set
            try:
                with self.lock:

                    ############ Кнопка запрос заказов
                    """Получаем сигнал от кнопки, змагружаем список заказов из 1С""" 
                    node3 = self.client.get_node('ns=2;s=Application.UserInterface.ButtonLoadOrders')
                    ButtonLoadOrders = node3.get_value()
                    logging.debug(f"состояние кнопки запроса заказов - {ButtonLoadOrders}")

                    dict_OPC['ns=2;s=Application.UserInterface.ButtonLoadOrders'] = ButtonLoadOrders  
                    print(f"*********: {dict_OPC['ns=2;s=Application.UserInterface.ButtonLoadOrders']}")
                    print(f"Данные из глобального словаря на интерфейс: {dict_OPC['module']}")

                    #Если нажата кнопка пишем заказы в перменную
                    if  ButtonLoadOrders == True:
                        # Получаем заказы из 1С
                        orders = Provider1C.getOrders()
                        data_value1 = ua.DataValue(ua.Variant(orders, ua.VariantType.String))
                        logging.debug(f"индекс заказа - {data_value1}")


                        # Записываем новое значение в узел
                        node2 = self.client.get_node('ns=2;s=Application.UserInterface.search_result')
                        node2.set_value(data_value1)
                        logging.debug(f"передали индекс заказа - {node2} в узел")



                    ############ Кнопка выбора заказа и получения данных
                    # 2. Читаем кнопку загрузки
                    node5 = self.client.get_node('ns=2;s=Application.UserInterface.ButtonSelectOrder')
                    ButtonSelectOrder = node5.get_value()
                    logging.debug(f"состояние кнопки загрузки - {ButtonSelectOrder}")
                    dict_OPC['ns=2;s=Application.UserInterface.ButtonSelectOrder'] = ButtonSelectOrder
                    print(f"UserInterface.ButtonSelectOrder: {dict_OPC['ns=2;s=Application.UserInterface.ButtonSelectOrder']}")
                    
                    # Если нажата кнопка загрузки, пишем заказы в переменную
                    if ButtonSelectOrder:
                        # 1. Берем заказ из Order
                        node4 = self.client.get_node('ns=2;s=Application.UserInterface.Order')
                        opcOrder = node4.get_value()
                        logging.debug(f"номер заказа - {opcOrder}")
                        
                        dict_OPC['ns=2;s=Application.UserInterface.Order'] = opcOrder

                        if opcOrder:  # Проверка, что заказ не пустой
                            order_id, board_name, firmware, batch, count, version, components = Provider1C.fetch_data(opcOrder)
                            db_connection = SQL.DatabaseConnection()
                            db_connection.get_order_insert_orders_frm1C(order_id, board_name, firmware, batch, count, version, components)
                            print(f"Заказ {opcOrder} отправлен на загрузку данных")
                            print(f"Данные по заказу {opcOrder} загружены в базу")

                            # Пример записи состояния в интерфейс
                            state = self.client.get_node('ns=2;s=Application.UserInterface.State')
                            state.set_value(ua.DataValue(ua.Variant("Данные загружены успешно", ua.VariantType.String)))
                        else:
                            print("В переменной Order нет данных")
                            state = self.client.get_node('ns=2;s=Application.UserInterface.State')
                            state.set_value(ua.DataValue(ua.Variant("Ошибка загрузки", ua.VariantType.String)))

                    """
                    ################### Читаем п ишемв словарь ###################
                    node3 = self.client.get_node("ns=2;s=Application.PLC_PRG.VAL1")
                    value2 = node3.get_value()
                    dict_OPC["ns=2;s=Application.PLC_PRG.VAL2"] = value2
                    print(f"*********: {dict_OPC["ns=2;s=Application.PLC_PRG.VAL2"]}")

                    node4 = self.client.get_node("ns=2;s=Application.PLC_PRG.VAL2")
                    value3 = node4.get_value()
                    dict_OPC["ns=2;s=Application.PLC_PRG.VAL2"] = value3
                    print(f"**VAL2**: {dict_OPC["ns=2;s=Application.PLC_PRG.VAL2"]}")

                    node5 = self.client.get_node("ns=2;s=Application.PLC_PRG.orderNode")
                    value4 = node5.get_value()
                    dict_OPC["ns=2;s=Application.PLC_PRG.orderNode"] = value4
                    print(f"******N*: {dict_OPC["ns=2;s=Application.PLC_PRG.orderNode"]}")
                    """
                    

            except Exception as e:
                print(f"Error updating registers OPC: {e}")
            time.sleep(1)
            

    def stop(self):
        self.stop_event.set()  # Set the event to stop threads

url = "opc.tcp://192.168.1.3:48010"
opc_client = OPCClient(url)





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
            StartTcpServer(context, address=("192.168.1.100", 502))
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
        logging.info(f"Отправка команды Reg_move_Table = 101")
        self.change_value('Reg_move_Table', 101)
        while True:
            result1 = self.read_value("sub_Reg_move_Table")
            logging.debug(f"Текущее значение sub_Reg_move_Table: {result1}")
            if result1 != 101:
                print(f"Ждем ответ о том что стол сдвинут - сейчас значение = {result1}")
                logging.debug(f"Ожидание ответа от стола... Текущее значение: {result1}")
            elif result1 == 404:
                print(f"От регула получен код 404 на операции движения стола")
                logging.warning("От регула получен код 404 (успех операции движения стола)")
            else:
                logging.info("Успешное завершение: стол сдвинут")
                break
            time.sleep(1)
        logging.info(f"Сброс команды Reg_move_Table = 0")
        self.change_value('Reg_move_Table', 0)

        print("2 Робот <- Забери плату с ложе 1.")
        logging.info(f"Отправка команды Rob_Action = 231")
        self.change_value('Rob_Action', 231)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            logging.debug(f"Текущее значение sub_Rob_Action: {result1}")

            if result1 != 231:
                print(f"ответ от робота = {result1}")
                logging.debug(f"Ожидание ответа от робота... Текущее значение: {result1}")
            elif result1 == 404:
                print(f"от робота ошибка 404")
                logging.warning("От робота получен код 404 (успех операции 'взять плату')")
            else:
                logging.info("От робота получен код 200 (успех операции 'взять плату')")
                break
            time.sleep(1)
        logging.info(f"Сброс команды Rob_Action = 0")
        self.change_value('Rob_Action', 0)

        print("3 Регул <- Сдвинь плату освободив ложе2.")
        logging.info("3 Регул <- Сдвинь плату освободив ложе2.")
        logging.info(f"Отправка команды Reg_move_Table = 102")
        self.change_value('Reg_move_Table', 102)
        while True:
            logging.debug(f"Текущее значение sub_Reg_move_Table: {result1}")

            result1 = self.read_value("sub_Reg_move_Table")
            if result1 != 102:
                print(f"Ждем ответ о том что стол сдвинут - сейчас значение = {result1}")
                logging.debug(f"Ждем ответ о том что стол сдвинут - сейчас значение = {result1}")
            elif result1 == 404:
                print(f"От регула получен код 404 на операции движения стола")
                logging.warning(f"От регула получен код 404 на операции движения стола")
            else:
                logging.info("Успешное завершение: стол сдвинут")
                break
            time.sleep(1)

        logging.info(f"Сброс команды Reg_move_Table = 0")
        self.change_value('Reg_move_Table', 0)

        print("4 Робот <- Забери плату с ложе 2.")
        self.change_value('Rob_Action', 232)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 232:
                print(f"ответ от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции взять плату с ложа")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)

        print("******ЦИКЛ DEFENCE Завершен*******")


    ############# ****ЦИКЛ SETUP ******"
    def setup_cycle(self):
        global photodata
        global Tray1
        global Cell1
        global Order
        print("****ЦИКЛ SETUP******")
        ######################################################
        input("нажми ентер")
        # 1 Робот <- Забери плату из тары
        
        Cell1 = Cell1 + 1
        print("1 Робот <- забрать плату из тары")
        logging.info(f"[START] Робот <- забрать плату из тары")
        self.change_value('Rob_Action', 210)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            logging.debug(f"sub_Rob_Action = {result1}")

            if result1 != 210:
                print(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
                logging.debug(f"ответ от робота = {result1}")
            elif result1 == 404:
                print(f"ошибка 404")
                logging.warning(f"ошибка 404")
                
            else:
                print(f"ответ от робота = {result1}")
                logging.debug(f"ответ от робота = {result1}")
                logging.info(f"[END] Робот <- забрать плату из тары")
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1=0
        ##########################################################
        
        
        input("нажми ентер")

        ##########################################################
        # 2 Делаем фото платы
        print("2 Камера <- сделай фото")
        logging.info(f"[START] Камера <- сделай фото")
        for i in range(3):
            try:
                logging.debug(f"Попытка {i}: запрос фото с камеры")
                res,photodata1= CameraSocket.photo()
                print(f"С камеры получен ID {photodata1}")
                logging.debug(f"Успех: получен ID фото {photodata1}")
            except Exception as e:
                print(f"Ошибка: камера недоступна. Детали: {e}")
                logging.warning(f"Попытка {i}: неверный ответ (код: {res}, данные: {photodata1})")
            time.sleep(1)
        while True:
            res,photodata1= CameraSocket.photo()
            logging.debug(f"Ожидание фото.код {res}, данные {photodata1}")
            if res != 200 or photodata1== "NoRead":
                print(f"Ошибка получения фото с камеры")
                logging.warning(f"Ошибка получения фото с камеры")
                time.sleep(1)
            else:
                print(f"Фото успешно получено: {photodata1}")
                logging.debug(f"[END] Камера <- сделай фото: {photodata1}")
                break
            time.sleep(1)

        ############################################################
        # 3 Робот <- Уложи плату в ложемент тетситрования
        print("3 Робот <- Уложи плату в ложемент тетситрования 1")
        logging.info(f"[START] Робот <- Уложи плату в ложемент тетситрования 1")
        self.change_value('Rob_Action', 221)
        logging.debug("Отправлена команда Rob_Action=221")
        while True:
            result1 = self.read_value("sub_Rob_Action")
            logging.debug(f"sub_Rob_Action = {result1}")

            if result1 != 221:
                logging.debug(f"Получено от робота = {result1}")
                print(f"Получено от робота = {result1}")
                time.sleep(1)
            elif result1 == 404:
                print(f"ошибка 404")
                logging.warning(f"ошибка 404")
                time.sleep(1)
            else:
                logging.debug(f"Получено от робота = {result1}")
                print(f"Получено от робота = {result1}")
                break
            logging.info(f"[END] Робот <- Уложи плату в ложемент тетситрования 1")
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1 = 0
        ####################################################################
        input("нажми ентер")



        ######################################################################
        # 4 Регул - Сдвигаем стол осовобождая ложе2
        print("4 Регул <- Сдвинь плату освободив ложе2.")
        logging.info(f"[START] Регул <- Сдвинь плату освободив ложе2")

        self.change_value('Reg_move_Table', 102)
        logging.debug("Отправлена команда Reg_move_Table', 102")
        while True:
            result1 = self.read_value("sub_Reg_move_Table")
            logging.debug(f"sub_Reg_move_Table = {result1}")

            if result1 != 102:
                logging.debug(f"получено от регула = {result1}")
                print(f"получено от регула = {result1}")
                time.sleep(1)
            elif result1 == 404:
                print(f"ошибка 404")
                logging.warning(f"ошибка 404")
            else:
                logging.debug(f"получено от регула = {result1}")
                print(f"получено от регула = {result1}")
                break
            time.sleep(1)
        logging.info(f"[END] Регул <- Сдвинь плату освободив ложе2")
        self.change_value('Reg_move_Table', 0)
        result1 = 0
        ############################################################################
        input("нажми ентер")
        
        #############################################################################
        # 5 Робот <- Забери плату из тары # Регул <- Опусти прошивальщик (плата на ложе1).
        Cell1 = Cell1 + 1
        
        print("5.1 Робот <- Забери плату из тары")
        print("5.2 Регул <- Опусти прошивальщик ложе 1")

        logging.info(f"[START1] Робот <- Забери плату из тары")
        #self.change_value('Rob_Action', 210)
        logging.debug("Отправлена команда Rob_Action', 210")

        logging.info(f"[START2] Регул <- Опусти прошивальщик ложе 1")
        self.change_value('Reg_updown_Botloader', 103)
        logging.debug("Отправлена команда 'Reg_updown_Botloader', 103")

        while True:
            result1 = self.read_value("sub_Rob_Action")
            logging.debug(f"sub_Reg_move_Table = {result1}")

            result2 = self.read_value("sub_Reg_updown_Botloader")
            logging.debug(f"sub_Reg_updown_Botloader = {result1}")

            if result1 != 210 and result2 != 103:
                print(f"получено от робота = {result1}")
                logging.debug(f"получено от робота = {result1}")
            
                print(f"получено от регула = {result2}")
                logging.debug(f"получено от регула = {result2}")
            elif result1 == 404:
                print(f"От робота ошибка 404")
                logging.warning(f"От робота ошибка 404")
            elif result2 == 404:
                print(f"От регула ошибка 404")
                logging.warning(f"От регула ошибка 404")
            elif result1 == 210 and result2 == 103:
                print(f"получено от робота = {result1}")
                logging.debug(f"получено от робота = {result1}")

                print(f"получено от регула = {result2}")
                logging.debug(f"получено от регула = {result2}")
                break
            time.sleep(1)
        logging.info(f"[END1] Робот <- Забери плату из тары")
        self.change_value('Rob_Action', 0)
        result1 = 0
        logging.info(f"[END2] Регул <- Опусти прошивальщик ложе 1")
        self.change_value('Reg_updown_Botloader', 0)
        result2 = 0
        ##################################################################################
        input("нажми ентер")

        ################################################################
        # 6 Делаем фото платы
        print("6 Камера <- сделай фото")
        logging.info(f"[START] Камера <- сделай фото")
        for i in range(3):
            try:
                logging.debug(f"Попытка {i}: запрос фото с камеры")
                res,photodata= CameraSocket.photo()
                print(f"С камеры получен ID {photodata}")
                logging.debug(f"Успех: получен ID фото {photodata}")
            except Exception as e:
                print(f"Ошибка: камера недоступна. Детали: {e}")
                logging.warning(f"Попытка {i}: неверный ответ (код: {res}, данные: {photodata})")
            time.sleep(1)
        while True:
            res,photodata= CameraSocket.photo()
            logging.debug(f"Ожидание фото.код {res}, данные {photodata}")
            if res != 200 or photodata== "NoRead":
                print(f"Ошибка получения фото с камеры")
                logging.warning(f"Ошибка получения фото с камеры")
                time.sleep(1)
            else:
                print(f"Фото успешно получено: {photodata}")
                logging.debug(f"[END] Камера <- сделай фото: {photodata}")
                break
            time.sleep(1)
        ###########################################################################


        input("нажми ентер")
        ###################################################################################
        # 7 Робот <- Уложи плату в ложемент тетситрования 2 # Сервер <- Начни шить 
        print("7.1 Робот <- Уложи плату в ложемент тетситрования 2")
        logging.info(f"[START1] Робот <- Уложи плату в ложемент тетситрования 2")
        self.change_value('Rob_Action', 222)
        logging.debug("Отправлена команда 'Rob_Action', 222")
        
        print("7.2 Сервер <- Начни шить")
        logging.info(f"[START2] Прошивка")
        result1 = 0

        # Данные по прошивке для этого серийника
        firmware_loader = Bot.FirmwareLoader(db_connection,igle_table,1, Order, photodata1)
        result2 = None  # Инициализируем перед циклом
        while True:
            # Обновляем result2 только если он еще не имеет нужного значения (200)
            if result2 != 200:
                result2 = firmware_loader.loader(photodata1)
                print(f" result2 -- {result2}")

            # Обновляем result1 только если он еще не имеет нужного значения (222)
            if result1 != 222:
                result1 = self.read_value("sub_Rob_Action")
                print(f" result1 -- {result1}")
            
            if result1 != 222 and result2 != 200:
                print(f"Ответ от прошивальщика {result2}")
                logging.debug(f"Ответ от прошивальщика= {result2}")
             
                print(f"Ответ от робота {result1}")
                logging.debug(f"Ответ от робота= {result1}")
            elif result1 == 404:
                print(f"От робота ошибка 404")
                logging.warning(f"От робота ошибка 404")
            elif result2 == 404:
                print(f"От регула ошибка 404")
                logging.warning(f"От регула ошибка 404")
            elif result1 == 222 and result2 == 200:
                print(f"Ответ от прошивальщика {result2}")
                logging.debug(f"Ответ от прошивальщика= {result2}")

                print(f"Ответ от робота {result1}")
                logging.debug(f"Ответ от робота= {result1}")
                break
            
            time.sleep(1)

        self.change_value('Rob_Action', 0)
        logging.info(f"[END1] Прошивка")
        logging.info(f"[END2] Робот <- Уложи плату в ложемент тетситрования 2")

        photodata1 = None
        result1 = 0
        result2 = 0

        ###############################################################################################
        input("нажми ентер")

        ################################################################################################
        # 8. Регул <- Подними прошивальщик.
        print("8. Регул <- Подними прошивальщик.")
        logging.info(f"[START] Регул <- Подними прошивальщик.")
        self.change_value('Reg_updown_Botloader', 104)
        logging.debug("Отправлена команда 'Reg_updown_Botloader', 104")
        while True:
            result1 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 104:
                print(f"ответ от регула= {result1}")
                logging.debug(f"ответ от регула= {result1}")
            elif result1 == 404:
                print(f"ошибка 404")
                logging.warning(f"ошибка 404")
            else:
                print(f"ответ от регула= {result1}")
                logging.debug(f"ответ от регула= {result1}")
                break
            time.sleep(1)
        logging.info(f"[END] Регул <- Подними прошивальщик.")
        self.change_value('Reg_updown_Botloader', 0)
        result1 = 0
        ################################################################################################
        input("нажми ентер")
        
    ############# ****ЦИКЛ SETUP END ******"

    ############# ****ЦИКЛ MAIN ******"
    def main(self):
        global Tray1
        global Cell1
        global photodata
        print("ЦИКЛ MAIN _ START")
        ################################################################################################
        # 1. Регул <- Сдвинь плату освободив ложе1.
        print("1 Регул <- Сдвинь плату освободив ложе1")
        logging.info(f"[START] Регул <- Сдвинь плату освободив ложе1")
        self.change_value('Reg_move_Table', 101)
        logging.debug("Отправлена команда 'Reg_move_Table', 101")

        while True:
            result1 = self.read_value("sub_Reg_move_Table")
            if result1 != 101:
                print(f"ответ от регула = {result1}")
                logging.debug(f"ответ от регула = {result1}")
            elif result1 == 404:
                print(f"ошибка 404")
                logging.warning(f"ошибка 404")
            else:
                print(f"ответ от регула = {result1}")
                logging.debug(f"ответ от регула = {result1}")
                break
                
            time.sleep(1)
        self.change_value('Reg_move_Table', 0)
        logging.info(f"[END] Регул <- Сдвинь плату освободив ложе1")
        result1 = 0

        ###################################################################################################
        input("нажми ентер")


        ###################################################################################################
        # 2. Робот <- Забери плату с ложе 1 # Регул <- Опусти прошивальщик ложе 2.
        print("2.1 Робот <- Забери плату с ложе 1.")
        logging.info(f"[START1] Робот <- Забери плату с ложе 1.")
        self.change_value('Rob_Action', 231)
        logging.debug("Отправлена команда 'Rob_Action', 231")

        print("2.2 Регул <- Опусти прошивальщик ложе 2")
        logging.info(f"[START2] Регул <- Опусти прошивальщик ложе 2")
        self.change_value('Reg_updown_Botloader', 103)
        logging.debug("Отправлена команда 'Reg_updown_Botloader', 103")

        while True:
            result1 = self.read_value("sub_Rob_Action")
            result2 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 231 and result2 != 103:
                print(f"ответ от робота = {result1}")
                logging.debug(f" ответ от робота = {result1}")

                print(f"ответ от регула = {result2}")
                logging.debug(f"ответ от регула = {result2}")
            elif result1 == 404:
                print(f"От робота ошибка 404 ")
                logging.warning(f"От робота ошибка 404")
            elif result2 == 404:   
                print(f"От регула ошибка 404")
                logging.warning(f"От регула ошибка 404")
            elif result1 == 231 and result2 == 103:
                print(f"ответ от робота = {result1}")
                logging.debug(f" ответ от робота = {result1}")

                print(f"ответ от регула = {result2}")
                logging.debug(f"ответ от регула = {result2}")
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        logging.info(f"[END1] Робот <- Забери плату с ложе 1.")
        print("Стол 1ложе свободен")
        result1 = 0

        logging.info(f"[END2] Регул <- Опусти прошивальщик ложе 2")
        self.change_value('Reg_updown_Botloader', 0)
        result2 = 0

        #######################################################################################################
        input("нажми ентер")

        #########################################################################################################
        # 3 Робот <- Уложи плату в тару # Сервер <- Начни шить
        print("#3.1 Робот <- Уложи плату в тару.")
        logging.info(f"[START1] Робот <- Уложи плату в тару.")
        self.change_value('Rob_Action', 241)
        logging.debug("Отправлена команда 'Rob_Action', 241")

        print("#3.2 Сервер <- Начни шить")
        logging.info(f"[START2] Прошивка")
        result1 = 0
        firmware_loader = Bot.FirmwareLoader(db_connection,igle_table,1, Order, photodata)
        while True:
            # Обновляем result2 только если он еще не имеет нужного значения (200)
            if result2 != 200:
                result2 = firmware_loader.loader(photodata)
                print(f" result2 -- {result2}")

            # Обновляем result1 только если он еще не имеет нужного значения (241)
            if result1 != 241:
                result1 = self.read_value("sub_Rob_Action")
                print(f" result1 -- {result1}")
            
            if result1 != 241 and result2 != 200:
                print(f"ответ от робота= {result1}")
                logging.debug(f"ответ от робота = {result1}")

                print(f"ответ прошивальщка {result2}")
                logging.debug(f"ответ от прошивальщика= {result2}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции уложить плату")
                logging.warning(f"От робота получен код 404 на на операции уложить плату")
            elif result1 == 241 and result2 == 200:
                print(f"ответ от робота= {result1}")
                logging.debug(f"ответ от робота = {result1}")

                print(f"ответ прошивальщка {result2}")
                logging.debug(f"ответ от прошивальщика= {result2}")
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        logging.info(f"[END1]  Робот <- Уложи плату в тару.")
        result1 = 0

        logging.info(f"[END2] Прошивка")
        photodata = None
        result2 = 0
        ##########################################################################################################
        input("нажми ентер")
      

        ##########################################################################################################
        # 4 Робот <- Забери плату из тары  # Регул <- Подними прошивальщик.
        print("4.1 Робот <- забрать плату из тары")
        logging.info(f"[START1] Робот <- забрать плату из тары")
        #self.change_value('Rob_Action', 210)
        logging.debug("Отправлена команда 'Rob_Action', 210")

        print("4.2 Регул <- Подними прошивальщик.")
        logging.info(f"[START2] Регул <- Подними прошивальщик.")
        self.change_value('Reg_updown_Botloader', 104)
        logging.debug("Отправлена команда 'Reg_updown_Botloader', 104")
        
        Cell1 = Cell1 + 1

        while True:
            result1 = self.read_value("sub_Rob_Action")
            result2 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 210 and result2 != 104:
                print(f"получено от робота = {result1}")
                logging.debug(f"получено от робота = {result1}")

                print(f"ответ от регула= {result2}")
                logging.debug(f"ответ от регула {result2}")
            elif result1 == 404 or result2 == 404 :
                print(f"От робота ошибка 404")
                logging.warning(f"От робота ошибка 404")
            elif result2 == 404 :
                print(f"От регула ошибка 404")
                logging.warning(f"От регула ошибка 404")
            elif result1 == 210 and result2 == 104:
                print(f"получено от робота = {result1}")
                logging.debug(f"получено от робота = {result1}")

                print(f"ответ от регула= {result2}")
                logging.debug(f"ответ от регула {result2}")
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        logging.info(f"[END1]  Робот <- забрать плату из тары")
        result1=0
        logging.info(f"[END2] Регул <- Подними прошивальщик.")
        self.change_value('Reg_updown_Botloader', 0)
        result2 = 0
        ###############################################################################################################
        input("нажми ентер")


        ################################################################
        # 5 Делаем фото платы
        print("5 Камера <- сделай фото")
        logging.info(f"[START] Камера <- сделай фото")
        for i in range(3):
            try:
                logging.debug(f"Попытка {i}: запрос фото с камеры")
                res,photodata= CameraSocket.photo()
                print(f"С камеры получен ID {photodata}")
                logging.debug(f"Успех: получен ID фото {photodata}")
            except Exception as e:
                print(f"Ошибка: камера недоступна. Детали: {e}")
                logging.warning(f"Попытка {i}: неверный ответ (код: {res}, данные: {photodata})")
            time.sleep(1)
        while True:
            res,photodata= CameraSocket.photo()
            logging.debug(f"Ожидание фото.код {res}, данные {photodata}")
            if res != 200 or photodata== "NoRead":
                print(f"Ошибка получения фото с камеры")
                logging.warning(f"Ошибка получения фото с камеры")
                time.sleep(1)
            else:
                print(f"Фото успешно получено: {photodata}")
                logging.debug(f"[END] Камера <- сделай фото: {photodata}")
                break
            time.sleep(1)
        ###########################################################################
        input("нажми ентер")


        ################################################################################################################
        # 6 Робот <- Уложи плату в ложемент тетситрования 1
        print("6 Робот <- Уложи плату в ложемент тетситрования 1")
        logging.info(f"[START] Робот <- Уложи плату в ложемент тетситрования 1")
        self.change_value('Rob_Action', 221)
        logging.debug("Отправлена команда Rob_Action=221")
        while True:
            result1 = self.read_value("sub_Rob_Action")
            logging.debug(f"sub_Rob_Action = {result1}")

            if result1 != 221:
                logging.debug(f"Получено от робота = {result1}")
                print(f"Получено от робота = {result1}")
                time.sleep(1)
            elif result1 == 404:
                print(f"ошибка 404")
                logging.warning(f"ошибка 404")
                time.sleep(1)
            else:
                logging.debug(f"Получено от робота = {result1}")
                print(f"Получено от робота = {result1}")
                break
            logging.info(f"[END] Робот <- Уложи плату в ложемент тетситрования 1")
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1 = 0
        ######################################################################################################################
        input("нажми ентер")

        ######################################################################
        # 7 Регул - Сдвигаем стол осовобождая ложе2
        print("7 Регул <- Сдвинь плату освободив ложе2.")
        logging.info(f"[START] Регул <- Сдвинь плату освободив ложе2")

        self.change_value('Reg_move_Table', 102)
        logging.debug("Отправлена команда Reg_move_Table', 102")
        while True:
            result1 = self.read_value("sub_Reg_move_Table")
            logging.debug(f"sub_Reg_move_Table = {result1}")

            if result1 != 102:
                logging.debug(f"получено от регула = {result1}")
                print(f"получено от регула = {result1}")
                time.sleep(1)
            elif result1 == 404:
                print(f"ошибка 404")
                logging.warning(f"ошибка 404")
            else:
                logging.debug(f"получено от регула = {result1}")
                print(f"получено от регула = {result1}")
                time.sleep(1)
                break
            time.sleep(1)
        logging.info(f"[END] Регул <- Сдвинь плату освободив ложе2")
        self.change_value('Reg_move_Table', 0)
        result1 = 0
        ############################################################################
        input("нажми ентер")


        ###################################################################################################
        # 8. Робот <- Забери плату с ложе # Регул <- Опусти прошивальщик ложе 1
        print("8 Робот <- Забери плату с ложе 2.")
        logging.info(f"[START1] Робот <- Забери плату с ложе 2.")
        self.change_value('Rob_Action', 232)
        logging.debug("Отправлена команда 'Rob_Action', 232")

        print("8 Регул <- Опусти прошивальщик ложе 2")
        logging.info(f"[START2] Регул <- Опусти прошивальщик ложе 1")
        self.change_value('Reg_updown_Botloader', 103)
        logging.debug("Отправлена команда 'Reg_updown_Botloader', 103")
        while True:
            result1 = self.read_value("sub_Rob_Action")
            result2 = self.read_value("sub_Reg_updown_Botloader")
            logging.debug(f"sub_Reg_updown_Botloader = {result2}")
            if result1 != 232 and result2 != 103:
                print(f"ответ от робота = {result1}")
                logging.debug(f"ответ от робота = {result1}")

                print(f"ответ от регула= {result2}")
                logging.debug(f"ответ от регула= {result2}")
            elif result1 == 404:
                print(f"от робота ошибка 404")
                logging.warning(f"от робота ошибка 404")
            elif result2 == 404:
                print(f"от регула ошибка 404")
                logging.warning(f"от регула ошибка 404")
            elif result1 == 232 and result2 == 103:
                print(f"ответ от робота = {result1}")
                logging.debug(f"ответ от робота = {result1}")

                print(f"ответ от регула= {result2}")
                logging.debug(f"ответ от регула= {result2}")
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        logging.info(f"[END1] Робот <- Забери плату с ложе 2.")
        result1 = 0

        logging.info(f"[END2] Регул <- Опусти прошивальщик ложе 2")
        self.change_value('Reg_updown_Botloader', 0)
        result2 = 0

        #########################################################################################################
        # 9 Робот <- Уложи плату в тару # Сервер <- Начни шить
        print("#9.1 Робот <- Уложи плату в тару.")
        logging.info(f"[START1] Робот <- Уложи плату в тару.")
        self.change_value('Rob_Action', 241)
        logging.debug("Отправлена команда 'Rob_Action', 241")

        print("#9.2 Сервер <- Начни шить")
        logging.info(f"[START2] Прошивка")
        result1 = 0
        firmware_loader = Bot.FirmwareLoader(db_connection,igle_table,1, Order, photodata)
        while True:
            # Обновляем result2 только если он еще не имеет нужного значения (200)
            if result2 != 200:
                result2 = firmware_loader.loader(photodata)
                print(f" result2 -- {result2}")

            # Обновляем result1 только если он еще не имеет нужного значения (241)
            if result1 != 241:
                result1 = self.read_value("sub_Rob_Action")
                print(f" result1 -- {result1}")
            
            if result1 != 241 and result2 != 200:
                print(f"ответ от робота= {result1}")
                logging.debug(f"ответ от робота = {result1}")

                print(f"ответ прошивальщка {result2}")
                logging.debug(f"ответ от прошивальщика= {result2}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции уложить плату")
                logging.warning(f"От робота получен код 404 на на операции уложить плату")
            elif result1 == 241 and result2 == 200:
                print(f"ответ от робота= {result1}")
                logging.debug(f"ответ от робота = {result1}")

                print(f"ответ прошивальщка {result2}")
                logging.debug(f"ответ от прошивальщика= {result2}")
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        logging.info(f"[END1]  Робот <- Уложи плату в тару.")
        result1 = 0

        logging.info(f"[END2] Прошивка")
        photodata = None
        result2 = 0
        ##########################################################################################################
        input("нажми ентер")
       


        ##########################################################################################################
        # 10 Робот <- Забери плату из тары   # Регул <- Подними прошивальщик.
        Cell1 = Cell1 + 1

        print("10.1 Робот <- забрать плату из тары")
        logging.info(f"[START1] Робот <- забрать плату из тары")
        # self.change_value('Rob_Action', 210)
        logging.debug("Отправлена команда 'Rob_Action', 210")

        print("10.2 Регул <- Подними прошивальщик.")
        logging.info(f"[START2] Регул <- Подними прошивальщик.")
        self.change_value('Reg_updown_Botloader', 104)
        logging.debug("Отправлена команда 'Reg_updown_Botloader', 104")

        while True:
            result1 = self.read_value("sub_Rob_Action")
            result2 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 210 and result2 != 104:
                print(f"получено от робота = {result1}")
                logging.debug(f"получено от робота = {result1}")

                print(f"ответ от регула= {result2}")
                logging.debug(f"ответ от регула {result2}")
            elif result1 == 404 or result2 == 404 :
                print(f"От робота ошибка 404")
                logging.warning(f"От робота ошибка 404")
            elif result2 == 404 :
                print(f"От регула ошибка 404")
                logging.warning(f"От регула ошибка 404")
            elif result1 == 210 and result2 == 104:
                print(f"получено от робота = {result1}")
                logging.debug(f"получено от робота = {result1}")

                print(f"ответ от регула= {result2}")
                logging.debug(f"ответ от регула {result2}")
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        logging.info(f"[END1]  Робот <- забрать плату из тары")
        result1=0
        logging.info(f"[END2] Регул <- Подними прошивальщик.")
        self.change_value('Reg_updown_Botloader', 0)
        result2 = 0
        ###############################################################################################################
        input("нажми ентер")


        ################################################################
        # 11 Делаем фото платы
        print("11 Камера <- сделай фото")
        logging.info(f"[START] Камера <- сделай фото")
        for i in range(3):
            try:
                logging.debug(f"Попытка {i}: запрос фото с камеры")
                res,photodata= CameraSocket.photo()
                print(f"С камеры получен ID {photodata}")
                logging.debug(f"Успех: получен ID фото {photodata}")
            except Exception as e:
                print(f"Ошибка: камера недоступна. Детали: {e}")
                logging.warning(f"Попытка {i}: неверный ответ (код: {res}, данные: {photodata})")
            time.sleep(1)
        while True:
            res,photodata= CameraSocket.photo()
            logging.debug(f"Ожидание фото.код {res}, данные {photodata}")
            if res != 200 or photodata== "NoRead":
                print(f"Ошибка получения фото с камеры")
                logging.warning(f"Ошибка получения фото с камеры")
                time.sleep(1)
            else:
                print(f"Фото успешно получено: {photodata}")
                logging.debug(f"[END] Камера <- сделай фото: {photodata}")
                break
            time.sleep(1)
        ###########################################################################
        input("нажми ентер")



        ###################################################################################
        # 12 Робот <- Уложи плату в ложемент тетситрования
        print("12 Робот <- Уложи плату в ложемент тетситрования 2")
        logging.info(f"[START] Робот <- Уложи плату в ложемент тетситрования 2")
        self.change_value('Rob_Action', 222)
        logging.debug("Отправлена команда 'Rob_Action', 222")
        while True:
            result1 = self.read_value("sub_Rob_Action")
            logging.debug(f" sub_Rob_Action = {result1}")

            if result1 != 222:
                print(f"ответ от робота = {result1}")
                logging.debug(f"ответ от робота = {result1}")
            elif result1 == 404:
                print(f"От робота ошибка 404")
                logging.warning(f"От робота ошибка 404")
            else:
                print(f"ответ от робота = {result1}")
                logging.debug(f"ответ от робота = {result1}")
                break
            time.sleep(1)
        logging.info(f"[END] Робот <- Уложи плату в ложемент тетситрования 2")
        self.change_value('Rob_Action', 0)
        result1 = 0
        ######################################################################################
        input("нажми ентер")

        print("****ЦИКЛ MAIN END")

    ############# ****ЦИКЛ MAIN END ******"




    
################################################# STOP TABLE CLASS #####################################################################


    def pause(self):
        time.sleep(2)

    


if __name__ == "__main__":
    modbus_provider = ModbusProvider()
    
    
    

    ################################################# START OPC Communication class l ###################################
    
    table1 = Table("Table 1", dict_Table1)
   
    if Cell1 == 30:
        Tray1 +=1
        Cell1 = 0
    if Tray1 == 2:
        Tray1 = 0
        print('смените тару')

    flag = True
    if flag == True:
        table1.setup_cycle()
        flag = False
    if Tray1 < 3 and flag == False:
        table1.main()
