import logging
import time
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading
import socket
from opcua import Client
from opcua import ua
import logging
import yaml
import subprocess
import sys
import os


# Команды боту блок
command_toBOt_lock = threading.Lock()
command_toBOt = [0]
command_toBOt2 = [0]
command_toBOt3 = [0]

# Текущий обрабатываемый список (1, 2 или 3)
current_list = 1

def insertincommand_toBOt(command, listnumber):
    global command_toBOt, command_toBOt2, command_toBOt3
    
    with command_toBOt_lock:
        if listnumber == 1:
            command_toBOt.append(command)
        elif listnumber == 2:
            command_toBOt2.append(command)
        elif listnumber == 3:
            command_toBOt3.append(command)
        else:
            raise ValueError("listnumber должен быть 1, 2 или 3")
        

def getlascommandBot():
    global command_toBOt, command_toBOt2, command_toBOt3, current_list
    
    with command_toBOt_lock:
        # Выбираем список в зависимости от current_list
        if current_list == 1 and command_toBOt:
            return command_toBOt[-1], 1
        elif current_list == 2 and command_toBOt2:
            return command_toBOt2[-1], 2
        elif current_list == 3 and command_toBOt3:
            return command_toBOt3[-1], 3
        else:
            # Если текущий список пуст, переключаемся на следующий
            if current_list == 1:
                current_list = 2
            elif current_list == 2:
                current_list = 3
            else:
                current_list = 1
            return None, current_list  # Нет команд в текущем списке


def eracecommandBot(command, listnumber):
    global command_toBOt, command_toBOt2, command_toBOt3
    
    with command_toBOt_lock:
        if listnumber == 1 and command in command_toBOt:
            command_toBOt.remove(command)
            print(f"Удалена команда {command} из списка 1")
        elif listnumber == 2 and command in command_toBOt2:
            command_toBOt2.remove(command)
            print(f"Удалена команда {command} из списка 2")
        elif listnumber == 3 and command in command_toBOt3:
            command_toBOt3.remove(command)
            print(f"Удалена команда {command} из списка 3")
        else:
            print(f"Команда {command} не найдена в списке {listnumber}") 




# Пользовательский класс камеры
# mport CameraClass as CAM
import CameraSocket
 
 # Пользовательский класс БД
import Provider1C
import SQLite as SQL

# Поьзовательский класс провайдера Иглостола
import ProviderIgleTable as Igable

# Пользовательский калсс прошивальщика
import Botloader as Bot

# Глобальные ящик и ясейка 
Tray1 = 0
Cell1 = 0
Order = "ЗНП-2160.1.1"
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

shared_data = {
    1: {
        'DICT1': 0,
        'Reg_move_Table': 0,
        'sub_Reg_move_Table': 0,
        'Reg_updown_Botloader': 0,
        'sub_Reg_updown_Botloader': 0,
        'Rob_Action': 0,
        'sub_Rob_Action': 0,
        'workplace1': 0, # Какое ложе сейчас раочее. нужно для платы индикации

        'DB_order_number': "",
        'DB_module': "",
        'DB_fw_version': "",
        'DB_last_count': 0,
        'DB_common_count': 0,
        'DB_success_count': 0,
        'DB_nonsuccess_count': 0,

        'OPC_ButtonLoadOrders': False,
        'OPC_ButtonSelectOrder': False,
        'OPC_Order': "",
        'OPC_Orders': ""
        },
    2: {
        'DICT2': 0,
        'Reg_move_Table': 0,
        'sub_Reg_move_Table': 0,
        'Reg_updown_Botloader': 0,
        'sub_Reg_updown_Botloader': 0,
        'Rob_Action': 0,
        'sub_Rob_Action': 0,
        'workplace1': 0, # Какое ложе сейчас раочее. нужно для платы индикации

        'DB_order_number': "",
        'DB_module': "",
        'DB_fw_version': "",
        'DB_last_count': 0,
        'DB_common_count': 0,
        'DB_success_count': 0,
        'DB_nonsuccess_count': 0,

        'OPC_ButtonLoadOrders': False,
        'OPC_ButtonSelectOrder': False,
        'OPC_Order': "",
        'OPC_Orders': ""
        },
    3: {
        'DICT3': 0,
        'Reg_move_Table': 0,
        'sub_Reg_move_Table': 0,
        'Reg_updown_Botloader': 0,
        'sub_Reg_updown_Botloader': 0,
        'Rob_Action': 0,
        'sub_Rob_Action': 0,
        'workplace1': 0, # Какое ложе сейчас раочее. нужно для платы индикации

        'DB_order_number': "",
        'DB_module': "",
        'DB_fw_version': "",
        'DB_last_count': 0,
        'DB_common_count': 0,
        'DB_success_count': 0,
        'DB_nonsuccess_count': 0,

        'OPC_ButtonLoadOrders': False,
        'OPC_ButtonSelectOrder': False,
        'OPC_Order': "",
        'OPC_Orders': ""
        },
    'OPC-DB': {
        'DB_order_number': "пусто",
        'DB_module': "пусто",
        'DB_fw_version': "пусто",
        'DB_last_count': 0,
        'DB_common_count': 0,
        'DB_success_count': 0,
        'DB_nonsuccess_count': 0,

        'OPC_ButtonLoadOrders': False,
        'OPC_ButtonSelectOrder': False,
        'OPC_Order': "ЗНП-2160.1.1",
        'OPC_Orders': ""
        },

}

shared_data_lock = threading.Lock()





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
        urlStatusFromIgleTabe=f"http://192.168.1.100:5003/get_test_results/1")

igle_table2 = Igable.IgleTable(
        urlIgleTabeControl=f"http://192.168.1.100:5000/nails_table/start_test_board_with_rtk",
        urlStatusFromIgleTabe=f"http://192.168.1.100:5003/get_test_results/2")

igle_table3 = Igable.IgleTable(
        urlIgleTabeControl=f"http://192.168.1.100:5000/nails_table/start_test_board_with_rtk",
        urlStatusFromIgleTabe=f"http://192.168.1.100:5003/get_test_results/3")

################################################# IgleTable Communication Class ###################################


################################################# START SQL Communication class ###################################
# Класс для синхронизации с базой данных и обновления глобального словаря
class DatabaseSynchronizer:
    def __init__(self, order, number, shared_dict) :
        self.order = order
        self.stop_event = threading.Event()  # Событие для остановки потока
        self.update_thread = threading.Thread(target=self.update_data, daemon=True)
        self.update_thread.start()
        self.lock = threading.Lock()
        self.number = number
        self.my_data = shared_dict.get('OPC-DB', {})  # Только своя часть словаря
        self.lock = threading.Lock()

    def update_data(self):
        """Метод для обновления данных в глобальном словаре с базы данных"""
        global shared_data
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
                        with shared_data_lock:
                            self.my_data["DB_order_number"] = order_number          # номер заказа
                            self.my_data["DB_module"] = module                      # имя платы
                            self.my_data["DB_fw_version"] = fw_version              # версия прошивки
                            self.my_data["DB_last_count"] = last_count              # колво непрошитых
                            self.my_data["DB_common_count"] = common_count          # общее колво плат
                            self.my_data["DB_success_count"] = success_count        # прошито ок
                            self.my_data["DB_nonsuccess_count"] = nonsuccess_count  # не прошито    
                else:
                    print(f"[DBSync {self.client_id}] Данные по заказу не найдены.")

            except Exception as e:
                logging.error(f"Ошибка при синхронизации с базой данных: {e}")
            
            # Пауза 1 секунда перед следующей попыткой
            time.sleep(1)

    def stop(self):
        """Метод для остановки потока"""
        self.stop_event.set()  # Устанавливаем событие, чтобы остановить поток

try:
        # Create an instance of DatabaseConnection
        db_connection = SQL.DatabaseConnection()
except Exception as e:
        logging.error(f"Error Create an instance of DatabaseConnection: {e}")
 ################################################# STOP SQL Communication class ###################################




################################################# START OPC Communication class ###################################

class OPCClient:
    def __init__(self, url, client_id, shared_dict):
        self.url = url
        self.lock = threading.Lock()
        self.shared_dict = shared_dict
        self.my_data = shared_dict.get(client_id, {})
        
        # инициализируем значениями по умолчанию
        self.my_data.setdefault("OPC_ButtonLoadOrders", False)
        self.my_data.setdefault("OPC_ButtonSelectOrder", False)
        self.my_data.setdefault("OPC_Order", "")
        
        self.client = None
        self.connected = False
        self.stop_event = threading.Event()
        
        # Start threads
        self.server_thread = threading.Thread(target=self.connection_manager, daemon=True)
        self.update_thread = threading.Thread(target=self.update_registers, daemon=True)
        self.server_thread.start()
        self.update_thread.start()

    def connection_manager(self):
        """Управление соединением по ОПС"""
        while not self.stop_event.is_set():
            try:
                if not self.connected:
                    self.client = Client(self.url)
                    self.client.connect()
                    self.connected = True
                    print(f"Connected to {self.url}")
                time.sleep(1)
            except Exception as e:
                print(f"Connection error: {e}")
                self.connected = False
                if self.client:
                    try:
                        self.client.disconnect()
                    except:
                        pass
                time.sleep(5)  # Wait before reconnection attempt

    def is_connected(self):
        """Check if client is properly connected"""
        return self.connected and self.client is not None

    def update_registers(self):
        """Method for updating OPC variables and dictionary"""
        global shared_data
        while not self.stop_event.is_set():
            try:
                if not self.is_connected():
                    time.sleep(1)
                    continue

                with self.lock:
                    with shared_data_lock:
                        try:
                            # Read ButtonLoadOrders with protection
                            ButtonLoadOrders = False  # Default value
                            try:
                                node = self.client.get_node('ns=2;s=Application.UserInterface.ButtonLoadOrders')
                                ButtonLoadOrders = node.get_value() or False
                            except Exception as e:
                                print(f"Error reading ButtonLoadOrders: {e}")
                            
                            shared_data['OPC-DB']["OPC_ButtonLoadOrders"] = ButtonLoadOrders
                            logging.debug(f"ButtonLoadOrders state - {ButtonLoadOrders}")

                            # Write values to OPC only if connected
                            if self.connected:
                                # Write interface values with protection
                                try:
                                    node = self.client.get_node('ns=2;s=Application.UserInterface.name_board')
                                    node.set_value(ua.DataValue(ua.Variant(shared_data['OPC-DB']['DB_module'], ua.VariantType.String)))
                                except Exception as e:
                                    print(f"Error setting name_board: {e}")

                                try:
                                    node = self.client.get_node('ns=2;s=Application.UserInterface.fw_version')
                                    node.set_value(ua.DataValue(ua.Variant(shared_data['OPC-DB']['DB_fw_version'], ua.VariantType.String)))
                                except Exception as e:
                                    print(f"Error setting fw_version: {e}")

                                # Other write operations similarly protected...

                                # Handle ButtonLoadOrders logic
                                if ButtonLoadOrders:
                                    try:
                                        orders = Provider1C.getOrders() or ['']  # Default empty list
                                        node = self.client.get_node('ns=2;s=Application.UserInterface.search_result')
                                        node.set_value(ua.DataValue(ua.Variant(orders, ua.VariantType.String)))
                                    except Exception as e:
                                        print(f"Error handling ButtonLoadOrders: {e}")

                                # Handle ButtonSelectOrder logic
                                # ... similar protection for other operations

                        except Exception as e:
                            print(f"Error in update_registers: {e}")

            except Exception as e:
                print(f"Critical error in update loop: {e}")
            
            time.sleep(1)

    def stop(self):
        """Clean shutdown"""
        self.stop_event.set()
        if self.client:
            try:
                self.client.disconnect()
            except:
                pass



################################################# START OPC Communication class l ###################################


class ModbusProvider:
    """Class MODBUS Communication with Modbus regul"""
    global Tray1
    global Cell1
    global command_toBOt
    def __init__(self):
        self.store = ModbusSlaveContext(
            hr=ModbusSequentialDataBlock(0, [0] * 100)
        )
        self.lock = threading.Lock()

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

    def update_registers(self):
        global shared_data, Tray1, Cell1
        while True:
            try:
                with shared_data_lock:

                    # СТОЛ 1
                    # Получаем данные из регистров и записываем в shared_data[1]
                    shared_data[1]['sub_Reg_move_Table'] = self.store.getValues(3, 9, count=1)[0]
                    shared_data[1]['sub_Reg_updown_Botloader'] = self.store.getValues(3, 11, count=1)[0]
                    shared_data[1]['sub_Rob_Action'] = self.store.getValues(3, 13, count=1)[0]
                    shared_data[1]['workplace1'] = self.store.getValues(3, 15, count=1)[0]

                    # Логирование операций чтения регистров
                    logging.info(
                        "[Modbus] Команда получения данных из регистров (Стол 1):\n"
                        f"  sub_Reg_move_Table       = {shared_data[1]['sub_Reg_move_Table']}\n"
                        f"  sub_Reg_updown_Botloader = {shared_data[1]['sub_Reg_updown_Botloader']}\n"
                        f"  sub_Rob_Action           = {shared_data[1]['sub_Rob_Action']}\n"
                        f"  workplace1               = {shared_data[1]['workplace1']}"
                    )

                    # Записываем данные из shared_data[1] в регистры
                    self.store.setValues(3, 10, [shared_data[1]['Reg_move_Table']])
                    self.store.setValues(3, 12, [shared_data[1]['Reg_updown_Botloader']])
                    Rob_Action = getlascommandBot()
                    self.store.setValues(3, 4, [Rob_Action])
                    #print(f"СТОЛ 1 В модбасе получаем команду робота = {Rob_Action}")

                    # Логирование операций записи регистров
                    logging.info(
                        "[Modbus] Команда записи данных в регистры (Стол 1):\n"
                        f"  Reg_move_Table       = {shared_data[1]['Reg_move_Table']}\n"
                        f"  Reg_updown_Botloader = {shared_data[1]['Reg_updown_Botloader']}\n"
                        f"  Rob_Action           = {shared_data[1]['Rob_Action']}"
                    )


                    # СТОЛ 2
                    # Получаем данные из регистров и записываем в shared_data[1]
                    shared_data[2]['sub_Reg_move_Table'] = self.store.getValues(3, 1, count=1)[0]
                    shared_data[2]['sub_Reg_updown_Botloader'] = self.store.getValues(3, 3, count=1)[0]
                    shared_data[2]['sub_Rob_Action'] = self.store.getValues(3, 5, count=1)[0]
                    shared_data[2]['workplace1'] = self.store.getValues(3, 7, count=1)[0]

                    # Логирование операций чтения регистров
                    logging.info(
                        "[Modbus] Команда получения данных из регистров (Стол 2):\n"
                        f"  sub_Reg_move_Table       = {shared_data[2]['sub_Reg_move_Table']}\n"
                        f"  sub_Reg_updown_Botloader = {shared_data[2]['sub_Reg_updown_Botloader']}\n"
                        f"  sub_Rob_Action           = {shared_data[2]['sub_Rob_Action']}\n"
                        f"  workplace1               = {shared_data[2]['workplace1']}"
                    )

                    # Записываем данные из shared_data[2] в регистры
                    self.store.setValues(3, 0, [shared_data[2]['Reg_move_Table']])
                    self.store.setValues(3, 2, [shared_data[2]['Reg_updown_Botloader']])
                    Rob_Action = getlascommandBot()
                    #self.store.setValues(3, 4, [Rob_Action])
                    #print(f"СТОЛ 2 В модбасе получаем команду робота = {Rob_Action}")

                    # Логирование операций записи регистров
                    logging.info(
                        "[Modbus] Команда записи данных в регистры (Стол 2):\n"
                        f"  Reg_move_Table       = {shared_data[2]['Reg_move_Table']}\n"
                        f"  Reg_updown_Botloader = {shared_data[2]['Reg_updown_Botloader']}\n"
                        f"  Rob_Action           = {shared_data[2]['Rob_Action']}"
                    )

                    # СТОЛ 3
                    # Получаем данные из регистров и записываем в shared_data[1]
                    shared_data[3]['sub_Reg_move_Table'] = self.store.getValues(3, 17, count=1)[0]
                    shared_data[3]['sub_Reg_updown_Botloader'] = self.store.getValues(3, 19, count=1)[0]
                    shared_data[3]['sub_Rob_Action'] = self.store.getValues(3, 21, count=1)[0]
                    shared_data[3]['workplace1'] = self.store.getValues(3, 23, count=1)[0]

                    # Логирование операций чтения регистров
                    logging.info(
                        "[Modbus] Команда получения данных из регистров (Стол 3):\n"
                        f"  sub_Reg_move_Table       = {shared_data[3]['sub_Reg_move_Table']}\n"
                        f"  sub_Reg_updown_Botloader = {shared_data[3]['sub_Reg_updown_Botloader']}\n"
                        f"  sub_Rob_Action           = {shared_data[3]['sub_Rob_Action']}\n"
                        f"  workplace1               = {shared_data[3]['workplace1']}"
                    )

                    # Записываем данные из shared_data[1] в регистры
                    self.store.setValues(3, 18, [shared_data[3]['Reg_move_Table']])
                    self.store.setValues(3, 20, [shared_data[3]['Reg_updown_Botloader']])
                    Rob_Action = getlascommandBot()
                    #self.store.setValues(3, 4, [shared_data[3]['Rob_Action']])

                    # Логирование операций записи регистров
                    logging.info(
                        "[Modbus] Команда записи данных в регистры (Стол 3):\n"
                        f"  Reg_move_Table       = {shared_data[3]['Reg_move_Table']}\n"
                        f"  Reg_updown_Botloader = {shared_data[3]['Reg_updown_Botloader']}\n"
                        f"  Rob_Action           = {shared_data[3]['Rob_Action']}"
                    )
                    
                    # Записываем глобальные переменные
                    self.store.setValues(3, 6, [Tray1])
                    self.store.setValues(3, 8, [Cell1])

                    logging.info(
                        "[Modbus] Запись глобальных переменных ящик-ячейка:\n"
                        f"  Tray1 = {Tray1}\n"
                        f"  Cell1 = {Cell1}"
                    )

                    """
                    # Выводим значения для проверки
                    print(f"Registers updated - Table1: {shared_data[1]['Rob_Action']}, "
                          f"SubTable1: {shared_data[1]['sub_Rob_Action']}, ")
                    
                    # Выводим значения для проверки
                    print(f"Registers updated - Table2: {shared_data[2]['Rob_Action']}, "
                          f"SubTable2: {shared_data[2]['sub_Rob_Action']}, ")


                    # Выводим значения для проверки
                    print(f"Registers updated - Table3: {shared_data[3]['Rob_Action']}, "
                          f"SubTable3: {shared_data[3]['sub_Rob_Action']}, ")
                    """
                    


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
    def __init__(self, name, shared_data, shared_data_lock, number):
        self.name = name
        self.data = shared_data.get(number, {})  # подсловарь объекта
        self.lock = shared_data_lock
        self.number = number



    # Method write registers in modbus through modbus_provider
    def change_value(self, key, new_value):
        with self.lock:
            if key in self.data:
                self.data[key] = new_value
                # print(f"Updated {key} to {new_value} in {self.name}.")
            else:
                print(f"Key '{key}' not found in {self.name}.")

    # Method read registers in modbus through modbus_provider
    def read_value(self, key):
        with self.lock:
            if key in self.data:
                result = self.data[key]
                print(f"Read {key}: {result} from {self.name}.")
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
        #input("Меняем в регистре")
        command = 230 + self.number
        insertincommand_toBOt(command)
        print(f'стол {self.number} отдал команду {command}')

        while True:
            result1 = self.read_value("sub_Rob_Action")
            logging.debug(f"Текущее значение sub_Rob_Action: {result1}")

            if result1 == command:
                eracecommandBot(command)
                print(f"ответ от робота = {command}")
                logging.info("От робота получен код 200 (успех операции 'взять плату')")
                break  
            elif result1 == 404:
                print(f"от робота ошибка 404")
                logging.warning("От робота получен код 404 (успех операции 'взять плату')")
            else:
                logging.debug(f"Ожидание ответа от робота... Текущее значение: {result1}")
            time.sleep(1)
        logging.info(f"Сброс команды Rob_Action = 0")
        self.change_value('Rob_Action', 0)
        command = 0
        result1 = 0

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

        print("4 Робот <- Забери плату с ложе 4 5 6")
        command = 233 + self.number
        insertincommand_toBOt(command)
        print(f'стол {self.number} отдал команду {command}')
        while True:
            result1 = self.read_value("sub_Rob_Action")
            logging.debug(f"Текущее значение sub_Rob_Action: {result1}")
            if result1 == command:
                eracecommandBot(command)
                print (f'__________________________{command_toBOt}')
                print(f"ответ от робота = {command}")
                logging.info("От робота получен код 200 (успех операции 'взять плату')")
                break  
            elif result1 == 404:
                print(f"от робота ошибка 404")
                logging.warning("От робота получен код 404 (успех операции 'взять плату')")
            else:
                logging.debug(f"Ожидание ответа от робота... Текущее значение: {result1}")
            time.sleep(1)
        logging.info(f"Сброс команды Rob_Action = 0")
        self.change_value('Rob_Action', 0)
        command = 0
        result1 = 0
        print("******ЦИКЛ DEFENCE Завершен*******")
    

    ############# ****ЦИКЛ SETUP ******"
    def setup_cycle(self):
        global photodata
        global Tray1
        global Cell1
        global Order
        print("****ЦИКЛ SETUP******")
        ######################################################
        #input("нажми ентер")
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
        
        
        #input("нажми ентер")

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
        #input("нажми ентер")



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
        #input("нажми ентер")
        
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

            #if result1 != 210 and result2 != 103:
            if result2 != 103:
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
            #elif result1 == 210 and result2 == 103:
            elif result2 == 103:
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
        #input("нажми ентер")

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


        #input("нажми ентер")
        ###################################################################################
        # 7 Робот <- Уложи плату в ложемент тетситрования 2 # Сервер <- Начни шить 
        print("7.1 Робот <- Уложи плату в ложемент тетситрования 2")
        logging.info(f"[START1] Робот <- Уложи плату в ложемент тетситрования 2")
        self.change_value('Rob_Action', 222)
        logging.debug("Отправлена команда 'Rob_Action', 222")
        
        print("7.2 Сервер <- Начни шить")
        logging.info(f"[START2] Прошивка")
        result1 = 0
        loge = self.read_value("workplace1")
        print(f"Переадем номер ложемента Моржову = {loge}")
        # Данные по прошивке для этого серийника
        firmware_loader = Bot.FirmwareLoader(db_connection,igle_table,1, Order, photodata1, loge)
        result2 = None  # Инициализируем перед циклом
        while True:
            # Обновляем result2 только если он еще не имеет нужного значения (200)
            if result2 != 200:
                result2 = firmware_loader.loader(photodata1, loge)
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
        #input("нажми ентер")

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
        #input("нажми ентер")
        
    ############# ****ЦИКЛ SETUP END ******"

    ############# ****ЦИКЛ MAIN ******"
    def main(self):
        global Tray1
        global Cell1
        global photodata
        print("ЦИКЛ MAIN _ START")
        ################################################################################################
        ######################################################
        #input("нажми ентер")

        ################################################################
        # 2 Делаем фото платы
        print("2 Камера <- сделай фото")
        logging.info(f"[НАЧАЛО] Камера <- сделай фото")
        for i in range(3):
            try:
                logging.debug(f"Попытка {i}: запрос фото с камеры")
                res,photodata = CameraSocket.photo()
                print(f"С камеры получен ID {photodata}")
                logging.info(f"Успех: получен ID фото {photodata}")
            except Exception as e:
                print(f"Ошибка: камера недоступна (photo camera not available). Детали: {e}")
                logging.warning(f"Попытка {i}: неверный ответ (код: {res}, данные: {photodata})")
            time.sleep(1)
        while True:
            res,photodata = CameraSocket.photo()
            logging.debug(f"Ожидание фото.код {res}, данные {photodata}")
            if res != 200 or photodata == "NoRead":
                print(f"Ошибка получения фото с камеры")
                logging.warning(f"Ошибка получения фото с камеры")
                time.sleep(1)
            else:
                print(f"Фото успешно получено: {photodata}")
                logging.info(f"[Завершение] Камера <- сделай фото: {photodata}")
                break
            time.sleep(1)
        input("Нажми ентер")
        ###########################################################################
    
        #input("нажми ентер")


        ######################################################################
        # 4 Регул - Сдвигаем стол осовобождая ложе2
        print("4 Регул <- Сдвинь плату освободив ложе2.")
        logging.info(f"[НАЧАЛО] Регул <- Сдвинь плату освободив ложе2")

        self.change_value('Reg_move_Table', 102)
        logging.debug("Отправлена команда Reg_move_Table', 102")
        while True:
            result1 = self.read_value("sub_Reg_move_Table")
            logging.debug(f"[Статус] sub_Reg_move_Table = {result1}")

            if result1 != 102:
                logging.info(f"Ждем ответ о том что стол сдвинут - сейчас значение = {result1}")
                print(f"Ждем ответ о том что стол сдвинут - сейчас значение = {result1}")
                time.sleep(1)
            elif result1 == 404:
                print(f"От регула получен код 404 на операции движения стола")
                logging.info(f"От регула получен код 404 на операции движения стола")
            else:
                break
            time.sleep(1)
        logging.info(f"[Завершение] Регул <- Сдвинь плату освободив ложе2")
        self.change_value('Reg_move_Table', 0)
        result1 = 0
        ############################################################################
        #input("нажми ентер")


        ########################################################################################
        # 8. Регул <- Опусти прошивальщик ложе 1.
        print("1 Регул <- Опусти прошивальщик ложе 1")
        logging.info(f"[НАЧАЛО] Регул <- Опусти прошивальщик ложе 1")

        self.change_value('Reg_updown_Botloader', 103)
        logging.debug("Отправлена команда 'Reg_updown_Botloader', 103")
        while True:
            result1 = self.read_value("sub_Reg_updown_Botloader")
            logging.debug(f"[Статус] sub_Reg_updown_Botloader = {result1}")
            if result1 != 103:
                print(f"Ждем ответ от регула, что прошивальщик опущен= {result1}")
                logging.info(f"Ждем ответ от регула, что прошивальщик опущен= {result1}")
            elif result1 == 404:
                print(f"От регула получен код 404 на на операции опустить прошивальщик")
                logging.info(f"От регула получен код 404 на на операции опустить прошивальщик")
            else:
                break
            time.sleep(1)
        logging.info(f"[Завершение] Регул <- Опусти прошивальщик ложе 1")
        self.change_value('Reg_updown_Botloader', 0)
        result1 = 0
        #############################################################################################
        #input("нажми ентер")


        ##############################################################################################
        # 9. Сервер <- Начни шить
        # 10. Сервер -> Ответ по прошивке (плохо, хорошо)
        print("9. Сервер <- Начни шить")
        print("10. Сервер -> Ответ по прошивке (плохо, хорошо)")
        logging.info(f"[НАЧАЛО] Прошивка")
        # photodata = "Z45564564645"
        # Данные по прошивке для этого серийника
        loge = self.read_value("workplace1")
        print(f"Переадем номер ложемента Моржову = {loge}")
        firmware_loader = Bot.FirmwareLoader(db_connection,igle_table,1, Order, photodata, loge)
        result1 = 200 #удалить
        while True:
            result1 = firmware_loader.loader(photodata, loge)
            if result1 != 200:
                print(f"Ждем ответ прошивальщка {result1}")
                logging.info(f"Ждем ответ от прошивальщика= {result1}")
            else:
                print(f"Ответ от прошивальщика {result1}")
                break
            time.sleep(1)
        print (f"Ответ от прошивальщика получен {result1}")
        logging.info(f"[Завершение] Прошивка")
        # Очищаем перменные результата
        photodata = None
        result1 = 0
        ###############################################################################################
        #input("нажми ентер")


        ################################################################################################
        # 11. Регул <- Подними прошивальщик.
        print("11. Регул <- Подними прошивальщик.")
        logging.info(f"[НАЧАЛО] Регул <- Подними прошивальщик.")
        self.change_value('Reg_updown_Botloader', 104)
        logging.debug("Отправлена команда 'Reg_updown_Botloader', 104")
        while True:
            result1 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 104:
                print(f"Ждем ответ от регула, что прошивальщик поднят= {result1}")
                logging.info(f"Ждем ответ от регула, что прошивальщик поднят= {result1}")
            elif result1 == 404:
                print(f"От регула получен код 404 на на операции поднять прошивальщик")
                logging.info(f"От регула получен код 404 на на операции поднять прошивальщик")
            else:
                break
            time.sleep(1)
        logging.info(f"[Завершение] Регул <- Подними прошивальщик.")
        self.change_value('Reg_updown_Botloader', 0)
        result1 = 0
        ################################################################################################
        #input("нажми ентер")


        ################################################################################################
        # 12. Регул <- Сдвинь плату освободив ложе1.
        print("12 Регул <- Сдвинь плату освободив ложе1")
        logging.info(f"[НАЧАЛО] Регул <- Сдвинь плату освободив ложе1")
        self.change_value('Reg_move_Table', 101)
        logging.debug("Отправлена команда 'Reg_move_Table', 101")

        while True:
            result1 = self.read_value("sub_Reg_move_Table")
            if result1 != 101:
                print(f"Ждем ответ о том что стол сдвинут - сейчас значение = {result1}")
                logging.info(f"Ждем ответ о том что стол сдвинут - сейчас значение = {result1}")
            elif result1 == 404:
                print(f"От регула получен код 404 на операции движения стола")
                logging.info(f"От регула получен код 404 на операции движения стола")
            else:
                break
            time.sleep(1)
        self.change_value('Reg_move_Table', 0)
        logging.info(f"[Завершение] Регул <- Сдвинь плату освободив ложе1")
        result1 = 0
        ###################################################################################################
        #input("нажми ентер")





        ################################################################
        # 16 Делаем фото платы
        print("16 Камера <- сделай фото")
        logging.info(f"[НАЧАЛО] Камера <- сделай фото")
        for i in range(3):
            try:
                logging.debug(f"Попытка {i}: запрос фото с камеры")
                res,photodata = CameraSocket.photo()
                print(f"С камеры получен ID {photodata}")
                logging.info(f"Успех: получен ID фото {photodata}")
            except Exception as e:
                print(f"Ошибка: камера недоступна (photo camera not available). Детали: {e}")
                logging.warning(f"Попытка {i}: неверный ответ (код: {res}, данные: {photodata})")
            time.sleep(1)
        while True:
            res,photodata = CameraSocket.photo()
            logging.debug(f"Ожидание фото.код {res}, данные {photodata}")
            if res != 200 or photodata == "NoRead":
                print(f"Ошибка получения фото с камеры")
                logging.warning(f"Ошибка получения фото с камеры")
                time.sleep(1)
            else:
                print(f"Фото успешно получено: {photodata}")
                logging.info(f"[Завершение] Камера <- сделай фото: {photodata}")
                break
            time.sleep(1)
        ###########################################################################
        #input("нажми ентер")


        ########################################################################################
        # 18. Регул <- Опусти прошивальщик ложе 2.
        print("1 Регул <- Опусти прошивальщик ложе 2")
        logging.info(f"[НАЧАЛО] Регул <- Опусти прошивальщик ложе 2")

        self.change_value('Reg_updown_Botloader', 103)
        logging.debug("Отправлена команда 'Reg_updown_Botloader', 103")
        while True:
            result1 = self.read_value("sub_Reg_updown_Botloader")
            logging.debug(f"[Статус] sub_Reg_updown_Botloader = {result1}")
            if result1 != 103:
                print(f"Ждем ответ от регула, что прошивальщик опущен= {result1}")
                logging.info(f"Ждем ответ от регула, что прошивальщик опущен= {result1}")
            elif result1 == 404:
                print(f"От регула получен код 404 на на операции опустить прошивальщик")
                logging.info(f"От регула получен код 404 на на операции опустить прошивальщик")
            else:
                break
            time.sleep(1)
        logging.info(f"[Завершение] Регул <- Опусти прошивальщик ложе 2")
        self.change_value('Reg_updown_Botloader', 0)
        result1 = 0
        #############################################################################################
        #input("нажми ентер")


        ##############################################################################################
        # 19. Сервер <- Начни шить
        # 20. Сервер -> Ответ по прошивке (плохо, хорошо)
        print("19. Сервер <- Начни шить")
        print("20. Сервер -> Ответ по прошивке (плохо, хорошо)")
        logging.info(f"[НАЧАЛО] Прошивка")
        loge = self.read_value("workplace1")
        print(f"Переадем номер ложемента Моржову = {loge}")
        # photodata = "Z45564564645"
        firmware_loader = Bot.FirmwareLoader(db_connection,igle_table,1, Order, photodata, loge)
        result1 = 200 #удалить
        while True:
            result1 = firmware_loader.loader(photodata, loge)
            if result1 != 200:
                print(f"Ждем ответ прошивальщка {result1}")
                logging.info(f"Ждем ответ от прошивальщика= {result1}")
            else:
                print(f"Ответ от прошивальщика {result1}")
                break
            time.sleep(1)
        print (f"Ответ от прошивальщика получен {result1}")
        logging.info(f"[Завершение] Прошивка")
        # Очищаем перменные результата
        photodata = None
        result1 = 0
        ###############################################################################################
        #input("нажми ентер")


        ################################################################################################
        # 21. Регул <- Подними прошивальщик.
        print("21. Регул <- Подними прошивальщик.")
        logging.info(f"[НАЧАЛО] Регул <- Подними прошивальщик.")
        self.change_value('Reg_updown_Botloader', 104)
        logging.debug("Отправлена команда 'Reg_updown_Botloader', 104")
        while True:
            result1 = self.read_value("sub_Reg_updown_Botloader")
            if result1 != 104:
                print(f"Ждем ответ от регула, что прошивальщик поднят= {result1}")
                logging.info(f"Ждем ответ от регула, что прошивальщик поднят= {result1}")
            elif result1 == 404:
                print(f"От регула получен код 404 на на операции поднять прошивальщик")
                logging.info(f"От регула получен код 404 на на операции поднять прошивальщик")
            else:
                break
            time.sleep(1)
        logging.info(f"[Завершение] Регул <- Подними прошивальщик.")
        self.change_value('Reg_updown_Botloader', 0)
        result1 = 0
        ################################################################################################
        #input("нажми ентер")



        ######################################################################
        # 22 Регул - Сдвигаем стол осовобождая ложе2
        print("22 Регул <- Сдвинь плату освободив ложе2.")
        logging.info(f"[НАЧАЛО] Регул <- Сдвинь плату освободив ложе2")

        self.change_value('Reg_move_Table', 102)
        logging.debug("Отправлена команда Reg_move_Table', 102")
        while True:
            result1 = self.read_value("sub_Reg_move_Table")
            logging.debug(f"[Статус] sub_Reg_move_Table = {result1}")

            if result1 != 102:
                logging.info(f"Ждем ответ о том что стол сдвинут - сейчас значение = {result1}")
                print(f"Ждем ответ о том что стол сдвинут - сейчас значение = {result1}")
            elif result1 == 404:
                print(f"От регула получен код 404 на операции движения стола")
                logging.info(f"От регула получен код 404 на операции движения стола")
            else:
                break
            time.sleep(1)
        logging.info(f"[Завершение] Регул <- Сдвинь плату освободив ложе2")
        self.change_value('Reg_move_Table', 0)
        result1 = 0
        ############################################################################
        #input("нажми ентер")



        ################################################################
        # 26 Делаем фото платы
        print("26 Камера <- сделай фото")
        logging.info(f"[НАЧАЛО] Камера <- сделай фото")
        for i in range(3):
            try:
                logging.debug(f"Попытка {i}: запрос фото с камеры")
                res,photodata = CameraSocket.photo()
                print(f"С камеры получен ID {photodata}")
                logging.info(f"Успех: получен ID фото {photodata}")
            except Exception as e:
                print(f"Ошибка: камера недоступна (photo camera not available). Детали: {e}")
                logging.warning(f"Попытка {i}: неверный ответ (код: {res}, данные: {photodata})")
            time.sleep(1)
        while True:
            res,photodata = CameraSocket.photo()
            logging.debug(f"Ожидание фото.код {res}, данные {photodata}")
            if res != 200 or photodata == "NoRead":
                print(f"Ошибка получения фото с камеры")
                logging.warning(f"Ошибка получения фото с камеры")
                time.sleep(1)
            else:
                print(f"Фото успешно получено: {photodata}")
                logging.info(f"[Завершение] Камера <- сделай фото: {photodata}")
                break
            time.sleep(1)
        ###########################################################################
        #input("нажми ентер")

        print("****ЦИКЛ MAIN END")

    ############# ****ЦИКЛ MAIN END ******"




    
################################################# STOP TABLE CLASS #####################################################################


    def pause(self):
        time.sleep(2)

    


if __name__ == "__main__":

    modbus_provider = ModbusProvider()
    

    # Создаем и запускаем процесс синхронизации с БД
    db_sync = DatabaseSynchronizer(Order, 1, shared_data)

    url = "opc.tcp://192.168.1.3:48010"
    opc_client = OPCClient(url, 2, shared_data)


    
    """
    # Имитируем изменение данных
    try:
        while True:
            # Меняем значения в shared_data
            shared_data[1]['Reg_move_Table'] = (shared_data[1]['Reg_move_Table'] + 1) % 10
            shared_data[1]['Reg_updown_Botloader'] = (shared_data[1]['Reg_updown_Botloader'] + 1) % 5
            shared_data[1]['Rob_Action'] = (shared_data[1]['Rob_Action'] + 1) % 3
            
            # Меняем глобальные переменные
            Tray1 = (Tray1 + 1) % 2
            Cell1 = (Cell1 + 1) % 4
            
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("Test stopped")
    """

    # Создаем и запускаем процесс синхронизации с БД
    db_sync = DatabaseSynchronizer(Order, 1, shared_data)
    db_sync = DatabaseSynchronizer(Order, 2, shared_data)
    db_sync = DatabaseSynchronizer(Order, 3, shared_data)


    # Создаём столы
    table1 = Table("Table1", shared_data, shared_data_lock, 1)
    table2 = Table("Table2", shared_data, shared_data_lock, 2)
    table3 = Table("Table3", shared_data, shared_data_lock, 3)

    # Создаем потоки для каждого объекта
    thread1 = threading.Thread(target=table1.defence_cycle)
    thread2 = threading.Thread(target=table2.defence_cycle)
    thread3 = threading.Thread(target=table3.defence_cycle)


    # Запускаем потоки
    print('__________________1 стол')
    thread1.start()
    # time.sleep(10)
    print('__________________2 стол')
    thread2.start()
    #time.sleep(10)
    print('__________________3 стол')
    thread3.start()
    # time.sleep(10)

    # Ждем завершения всех потоков
    thread1.join()
    thread2.join()
    thread3.join()

    print("Все потоки завершены.")
    opc_client.stop()
    
    
    

    ################################################# START OPC Communication class l ###################################
    
 

    
