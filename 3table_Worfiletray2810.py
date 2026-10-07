# python -m PyInstaller --onefile 3table_Worfiletray2810.py
import logging
import time
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading
import socket
from opcua import Client
from opcua import ua
import yaml
import subprocess
import sys
import os
import SQLite

# --- Глобальная аварийная остановка всего комплекса ---
EMERGENCY_STOP = threading.Event()
SETUP_TABLE = 0
SUB_SETUP_TABLE = 0

def trigger_emergency(reason: str):
    """
    Устанавливает глобальную аварийную остановку и логирует причину.
    После срабатывания ВСЕ циклы должны завершаться/ничего не делать.
    """
    if not EMERGENCY_STOP.is_set():
        logging.critical(f"[EMERGENCY STOP] {reason}")
        print(f"[EMERGENCY STOP] {reason}")
        EMERGENCY_STOP.set()

class TableTimeoutException(Exception):
    """Исключение при превышении таймаута работы со столом"""
    pass

class TableOperationFailed(Exception):
    """Исключение при ошибке выполнения команды столом"""
    pass


class RobActionManager:
    def __init__(self):
        self.lock = threading.Lock()  # Для атомарных операций
        self.current_table = None     # Какой стол сейчас владеет ресурсом

    def acquire(self, table_id):
        """Попытаться захватить Rob_Action для указанного стола."""
        with self.lock:
            if self.current_table is None:
                self.current_table = table_id
                return True
            return False

    def release(self, table_id):
        """Освободить Rob_Action."""
        with self.lock:
            if self.current_table == table_id:
                self.current_table = None
                return True
            return False    



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
Tray1 = 0 # результат (2 или 3) прошивки для 1 стола
Tray2 = 0 # результат (2 или 3) прошивки для 2 стола
Tray3 = 0 # результат (2 или 3) прошивки для 3 стола

Tray_robot = 0

Cell = 0   # номер ячейки, отдаваемый в Modbus (универсальный)
Cell1 = 0  # ячейка тары с новыми платами
Cell2 = 0  # ячейка тары УСПЕХА (241)
Cell3 = 0  # ячейка тары БРАКА (242)

Order = "ЗНП-2160.1.1"
# данные с платы для цикла main и сетапа
photodata = None


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
        'OPC_Orders': "",
        'OPC_STATE': 'idle',          # текстовое состояние: idle/move/down/up/sewing/error/...
        'OPC_SEWING': 0,              # 1 - идёт прошивка; 0 - нет
        'OPC_SEW_LOGE': 0,            # какой ложемент сейчас шьём (1/2)
        'OPC_SEW_DM': '',             # серийник/DM текущей платы
        'OPC_SEW_RESULT': 0,          # 0 – нет, 2 – успех, 3 – брак (как у вас Tray*)
        'OPC_SEW_ERROR': '',          # текст последней ошибки, если была
        'OPC_SEW_TS': 0,              # timestamp старта текущей прошивки (time.time())
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
        'OPC_Orders': "",
        'OPC_STATE': 'idle',          # текстовое состояние: idle/move/down/up/sewing/error/...
        'OPC_SEWING': 0,              # 1 - идёт прошивка; 0 - нет
        'OPC_SEW_LOGE': 0,            # какой ложемент сейчас шьём (1/2)
        'OPC_SEW_DM': '',             # серийник/DM текущей платы
        'OPC_SEW_RESULT': 0,          # 0 – нет, 2 – успех, 3 – брак (как у вас Tray*)
        'OPC_SEW_ERROR': '',          # текст последней ошибки, если была
        'OPC_SEW_TS': 0,              # timestamp старта текущей прошивки (time.time())
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
        'OPC_Orders': "",
        'OPC_STATE': 'idle',          # текстовое состояние: idle/move/down/up/sewing/error/...
        'OPC_SEWING': 0,              # 1 - идёт прошивка; 0 - нет
        'OPC_SEW_LOGE': 0,            # какой ложемент сейчас шьём (1/2)
        'OPC_SEW_DM': '',             # серийник/DM текущей платы
        'OPC_SEW_RESULT': 0,          # 0 – нет, 2 – успех, 3 – брак (как у вас Tray*)
        'OPC_SEW_ERROR': '',          # текст последней ошибки, если была
        'OPC_SEW_TS': 0,              # timestamp старта текущей прошивки (time.time())
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
        'OPC_Order': "ЗНП-2160.1.1", # № Заказа (строка)
        'OPC_Orders': "",
        'OPC_search_result':"", # Узел для хранения списка с заказами
        'OPC_dataOrder': [], # Узел для хранения списка плат в заказе
        'OPC_firmware' :"", # версия прошивки
        'OPC_nameboard': "", # имя платы
        'OPC_cnt_newBoard':0, # колво непрошитых плат
        'OPC_load_t1':0, # 1-старт прошивки 0-конец прошивки стол1
        'OPC_load_t2':0, # 1-старт прошивки 0-конец прошивки стол2
        'OPC_load_t3': 0, # 1-старт прошивки 0-конец прошивки стол3
        'OPC_res_load_t1':0, # 2-успех 1-брак стол1
        'OPC_res_load_t2':0, # 2-успех 1-брак стол2
        'OPC_res_load_t3':0, # 2-успех 1-брак стол3
        'OPC_strat_t1': False, # единичный сигнал true - запускаем поток стол1
        'OPC_strat_t2': False, # единичный сигнал true - запускаем поток стол2
        'OPC_strat_t3':False, # единичный сигнал true - запускаем поток стол3
        'OPC_START_RTK':False, # общий старт потоков\
        'OPC_log':'', #хранение текущего лога
        'OPC_res_brak': False, # Сброс брака
        'OPC_pause_RTK':False, # Постановка на паузу
        'OPC_restart_RTK':False # Перезапуск ртк
        },

}

shared_data_lock = threading.Lock()




##################################Логеры##########################################################################
# Set up basic logging configuration
logging.basicConfig(
    filename='RTK.log',
    level=logging.INFO,
    format=' %(asctime)s - MAIN - %(levelname)s - %(message)s'
)

# Логгер 1
logger1 = logging.getLogger('LoggerTable1')
fh1 = logging.FileHandler('LoggerTable1.txt')
formatter1 = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh1.setFormatter(formatter1)
logger1.addHandler(fh1)
logger1.setLevel(logging.INFO)

# Логгер 2
logger2 = logging.getLogger('LoggerTable2')
fh2 = logging.FileHandler('LoggerTable2.txt')
formatter2 = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh2.setFormatter(formatter2)
logger2.addHandler(fh2)
logger2.setLevel(logging.DEBUG)

# Логгер 3
logger3 = logging.getLogger('LoggerTable3')
fh3 = logging.FileHandler('LoggerTable3.txt')
formatter3 = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh3.setFormatter(formatter3)
logger3.addHandler(fh3)
logger3.setLevel(logging.DEBUG)

# Логгер 4
logger4 = logging.getLogger('LoggerMAIN')
fh4 = logging.FileHandler('LoggerMAIN.txt')
formatter4 = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
fh4.setFormatter(formatter4)
logger4.addHandler(fh4)
logger4.setLevel(logging.DEBUG)

# функция разброски логов
loggers = {
    1: logger1,
    2: logger2,
    3: logger3,
    4: logger4,
}

def log_message(logger_num, log_type, message):
    """Логирует сообщение в выбранный логгер по номеру и типу"""
    logger = loggers.get(logger_num)
    if not logger:
        raise ValueError('Неверный номер логгера (доступны 1..4)')
    if log_type == 'info':
        logger.info(message)
    elif log_type == 'warning':
        logger.warning(message)
    else:
        raise ValueError('Неверный тип сообщения (используй "info" или "warning")')

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
                            self.my_data["OPC_Order"] = order_number          # номер заказа
                            self.my_data["OPC_nameboard"] = module                      # имя платы
                            self.my_data["OPC_firmware"] = fw_version              # версия прошивки
                            self.my_data["DB_last_count"] = last_count              # колво непрошитых
                            self.my_data["DB_common_count"] = common_count          # общее колво плат
                            self.my_data["DB_success_count"] = success_count        # прошито ок
                            self.my_data["DB_nonsuccess_count"] = last_count  # не прошито
                else:
                    print(f"[DBSync] Данные по заказу не найдены.")

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

################################################# START OPC Communication class ###################################

class OPCClient:
    def __init__(self, url, client_id, shared_dict):
        self.url = url
        self.lock = threading.Lock()
        self.shared_dict = shared_dict
        self.my_data = shared_dict.get(client_id, {})

        # значения по умолчанию
        self.my_data.setdefault("OPC_ButtonLoadOrders", 0)
        self.my_data.setdefault("OPC_ButtonSelectOrder", 0)
        self.my_data.setdefault("OPC_Order", "")

        # кэш OPC-узлов
        self.nodes = {}  # {nodeid: Node}

        self.client = None
        self.connected = False
        self.stop_event = threading.Event()

        # Start threads
        self.server_thread = threading.Thread(target=self.connection_manager, daemon=True)
        self.update_thread = threading.Thread(target=self.update_registers, daemon=True)
        self.server_thread.start()
        self.update_thread.start()

    # -------------------- внутренние утилиты OPC --------------------
    def _get_node(self, nodeid):
        """Ленивое получение и кэширование OPC-узла."""
        if nodeid is None:
            return None
        node = self.nodes.get(nodeid)
        if node is None and self.client:
            try:
                node = self.client.get_node(nodeid)
                self.nodes[nodeid] = node
            except Exception as e:
                print(f"[OPC] can't resolve node {nodeid}: {e}")
                return None
        return node

    def _write(self, nodeid, value, vtype):
        """Безопасная запись значения в OPC-узел (с кэшем)."""
        node = self._get_node(nodeid)
        if not node:
            return
        try:
            node.set_value(ua.DataValue(ua.Variant(value, vtype)))
        except Exception as e:
            print(f"[OPC] write fail {nodeid}: {e}")

    def _read_bool(self, nodeid, default=0):
        node = self._get_node(nodeid)
        if not node:
            return default
        try:
            v = node.get_value()
            return int(v)
        except Exception as e:
            print(f"[OPC] read bool fail {nodeid}: {e}")
            return default

    def _read_str(self, nodeid, default=""):
        node = self._get_node(nodeid)
        if not node:
            return default
        try:
            v = node.get_value()
            return str(v) if v is not None else default
        except Exception as e:
            print(f"[OPC] read str fail {nodeid}: {e}")
            return default

    # -------------------- соединение --------------------
    def connection_manager(self):
        """Управление соединением по ОПС"""
        while not self.stop_event.is_set():
            try:
                if not self.connected:
                    self.client = Client(self.url)
                    self.client.connect()
                    self.connected = True
                    print(f"Connected to {self.url}")

                    # при коннекте можно заранее прогреть часто используемые узлы
                    warm_ids = [
                        'ns=2;s=Application.UserInterface.OPC_ButtonLoadOrders',
                        #'ns=2;s=Application.UserInterface.OPC_ButtonSelectOrder',
                        # 'ns=2;s=Application.UserInterface.OPC_selected_order', 
                        # 'ns=2;s=Application.UserInterface.OPC_SelectedOrder',
                        'ns=2;s=Application.UserInterface.OPC_nameboard',
                        'ns=2;s=Application.UserInterface.OPC_firmware',
                        'ns=2;s=Application.UserInterface.OPC_search_result',  # Узел для хранения списка с заказами
                        'ns=2;s=Application.UserInterface.OPC_Order', # № Заказа (строка)
                        'ns=2;s=Application.UserInterface.OPC_cnt_newBoard', # колво непрошитых плат
                        'ns=2;s=Application.UserInterface.OPC_dataOrder', # Узел для хранения списка плат в заказе
                        'ns=2;s=Application.UserInterface.OPC_strat_t1', # true - берем стол1 в работу
                        'ns=2;s=Application.UserInterface.OPC_strat_t2', # true - берем стол2 в работу
                        'ns=2;s=Application.UserInterface.OPC_strat_t3', # true - берем стол3 в работу
                        'ns=2;s=Application.UserInterface.OPC_start_RTK', # единичный сигнал true - запуск основного цикла ртк
                        'ns=2;s=Application.UserInterface.OPC_log', # от питона приходит текущего лога
                        'ns=2;s=Application.UserInterface.OPC_pause_RTK', #пауза от ртк
                        'ns=2;s=Application.UserInterface.OPC_restart_RTK',# рестарт
                        # Прошивка
                        'ns=2;s=Application.GVL.OPC_load_t1',
                        'ns=2;s=Application.GVL.OPC_load_t2',
                        'ns=2;s=Application.GVL.OPC_load_t3',
                        'ns=2;s=Application.GVL.OPC_res_load_t1',
                        'ns=2;s=Application.GVL.OPC_res_load_t2',
                        'ns=2;s=Application.GVL.OPC_res_load_t3',

                        # брак
                        'ns=2;s=Application.UserInterface.OPC_res_brak'

                        
                    ]
                    for nid in warm_ids:
                        self._get_node(nid)

                time.sleep(1)
            except Exception as e:
                print(f"Connection error: {e}")
                self.connected = False
                if self.client:
                    try:
                        self.client.disconnect()
                    except:
                        pass
                self.client = None
                time.sleep(5)  # Wait before reconnection attempt

    def is_connected(self):
        """Check if client is properly connected"""
        return self.connected and self.client is not None
    
    

    # -------------------- основной цикл OPC витрины --------------------
    def update_registers(self):
        """Раз в секунду читает кнопки, пишет статусы из shared_data в OPC"""
        global shared_data, Cell2

        # Адреса узлов в перменные
        BUTTON_LOAD = 'ns=2;s=Application.UserInterface.OPC_ButtonLoadOrders'

        NAME_BOARD = 'ns=2;s=Application.UserInterface.OPC_nameboard'
        CNT_NEW_BOARD  = 'ns=2;s=Application.UserInterface.OPC_cnt_newBoard'
        FW_VERSION = 'ns=2;s=Application.UserInterface.OPC_firmware'
        SEARCH_RESULT = 'ns=2;s=Application.UserInterface.OPC_search_result'
        DATA_ORDER     = 'ns=2;s=Application.UserInterface.OPC_dataOrder'
        # OPC_Order — ВЫБОР пользователя, НЕ перезатираем его из БД!
        NODE_OPC_ORDER = 'ns=2;s=Application.UserInterface.OPC_Order'

        # --- дополнительные ноды OPC (заглушки/синхронизация) ---
        LOAD_T1 = 'ns=2;s=Application.GVL.OPC_load_t1'
        LOAD_T2 = 'ns=2;s=Application.GVL.OPC_load_t2'
        LOAD_T3 = 'ns=2;s=Application.GVL.OPC_load_t3'
        RES_T1  = 'ns=2;s=Application.GVL.OPC_res_load_t1'
        RES_T2  = 'ns=2;s=Application.GVL.OPC_res_load_t2'
        RES_T3  = 'ns=2;s=Application.GVL.OPC_res_load_t3'

        START_T1 = 'ns=2;s=Application.UserInterface.OPC_strat_t1'
        START_T2 = 'ns=2;s=Application.UserInterface.OPC_strat_t2'
        START_T3 = 'ns=2;s=Application.UserInterface.OPC_strat_t3'
        START_RTK = 'ns=2;s=Application.UserInterface.OPC_start_RTK'

        OPC_RES_BRAK = 'ns=2;s=Application.UserInterface.OPC_res_brak'

        LOG = 'ns=2;s=Application.UserInterface.OPC_log'
        OPC_PAUSE_RTK = 'ns=2;s=Application.UserInterface.OPC_pause_RTK'
        OPC_RESTART_RTK = 'ns=2;s=Application.UserInterface.OPC_restart_RTK'
        
        # шаблон nodeId для столов
        def T(n, leaf):
            return f'ns=2;s=Application.UserInterface.Table{n}.{leaf}'

        while not self.stop_event.is_set():
            try:
                if not self.is_connected():
                    time.sleep(1)
                    continue

                with self.lock:
                    # ---------- 1) READ: кнопки из OPC ----------
                    try:
                        btn_load = self._read_bool(BUTTON_LOAD, False)
                        #  btn_select = self._read_bool(BUTTON_SELECT, False)

                        # отражаем в словаре (по желанию)
                        with shared_data_lock:
                            shared_data['OPC-DB']["OPC_ButtonLoadOrders"] = btn_load
                            # shared_data['OPC-DB']["OPC_ButtonSelectOrder"] = btn_select
                    except Exception as e:
                        print(f"[OPC] read buttons failed: {e}")
                        btn_load = False
                        # btn_select = False

                    # ---------- 2) WRITE: витрина DB полей (basic + extra) ----------
                    try:
                        with shared_data_lock:
                            opcdb = dict(shared_data.get('OPC-DB', {}))

                        # Базовые поля
                        self._write(NAME_BOARD, opcdb.get('OPC_nameboard', 'пусто'), ua.VariantType.String)
                        self._write(FW_VERSION, opcdb.get('OPC_firmware', 'пусто'), ua.VariantType.String)

                        # Кол-во непрошитых (берём OPC_cnt_newBoard, иначе DB_last_count как запасной источник)
                        cnt_new = opcdb.get('DB_nonsuccess_count', "")
                        cnt_new = cnt_new
                        self._write(CNT_NEW_BOARD, cnt_new, ua.VariantType.Int16)  # при необходимости замените тип

                        # Список заказов (строка/массив строк)
                        sr = opcdb.get('OPC_search_result', "")
                        if isinstance(sr, (list, tuple)):
                            self._write(SEARCH_RESULT, list(sr), ua.VariantType.String)
                        elif isinstance(sr, str) and sr:
                            self._write(SEARCH_RESULT, [sr], ua.VariantType.String)

                        # Список плат в заказе (строка/массив строк)
                        data_order = opcdb.get('OPC_dataOrder', [])
                        if isinstance(data_order, (list, tuple)):
                            self._write(DATA_ORDER, list(data_order), ua.VariantType.String)
                        else:
                            self._write(DATA_ORDER, str(data_order), ua.VariantType.String)

                        # Старт/статусы прошивки столов (числа)
                        self._write(LOAD_T1, opcdb.get('OPC_load_t1', 0), ua.VariantType.Int16)
                        self._write(LOAD_T2, opcdb.get('OPC_load_t2', 0), ua.VariantType.Int16)
                        self._write(LOAD_T3, opcdb.get('OPC_load_t3', 0), ua.VariantType.Int16)

                        self._write(RES_T1,  opcdb.get('OPC_res_load_t1', 0), ua.VariantType.Int16)
                        self._write(RES_T2,  opcdb.get('OPC_res_load_t2', 0), ua.VariantType.Int16)
                        self._write(RES_T3,  opcdb.get('OPC_res_load_t3', 0), ua.VariantType.Int16)
                        # Флаги запуска столов (булевы)
                        # self._write(START_T1, opcdb.get('OPC_strat_t1', False), ua.VariantType.Boolean)
                        # self._write(START_T2, opcdb.get('OPC_strat_t2', False), ua.VariantType.Boolean)
                        # self._write(START_T3, opcdb.get('OPC_strat_t3', False), ua.VariantType.Boolean)

                        # Логи на панель
                        self._write(LOG,  opcdb.get('OPC_log', ""), ua.VariantType.String)


                        # --- читаем флаги запуска из OPC и зеркалим в shared_data ---
                        try:
                            st1 = bool(self._read_bool(START_T1, False))
                            st2 = bool(self._read_bool(START_T2, False))
                            st3 = bool(self._read_bool(START_T3, False))
                            st4 = bool(self._read_bool(START_RTK, False))
                            st5 = bool(self._read_bool(OPC_RES_BRAK, False))
                            st6 = bool(self._read_bool(OPC_PAUSE_RTK, False))
                            st7 = bool(self._read_bool(OPC_RESTART_RTK, False))

                            with shared_data_lock:
                                shared_data['OPC-DB']['OPC_START_RTK'] = st4
                                shared_data['OPC-DB']['OPC_strat_t1'] = st1
                                shared_data['OPC-DB']['OPC_strat_t2'] = st2
                                shared_data['OPC-DB']['OPC_strat_t3'] = st3
                                shared_data['OPC-DB']['OPC_res_brak'] = st5
                                shared_data['OPC-DB']['OPC_pause_RTK'] = st6
                                shared_data['OPC-DB']['OPC_restart_RTK'] = st7


                        except Exception as e:
                            print(f"[OPC] read START_T* failed: {e}")

                            # Обнуляем ячейку брака есл иполучили истину в OPC_res_brak
                            if st5 is True:
                                Cell2 = 0
                            print(f"Cell2 = {Cell2}")
                        # ВАЖНО: OPC_Order обратно НЕ пишем, только читаем в отдельном блоке-детекторе выбора
                    except Exception as e:
                        print(f"[OPC] write vitrina (basic+extra) failed: {e}")

                    # ---------- 3) ButtonLoadOrders: получить список заказов и показать ----------
                    if btn_load:
                        try:
                            orders = Provider1C.getOrders() or []
                            # в словарь (если хотите хранить локально)
                            with shared_data_lock:
                                shared_data['OPC-DB']['OPC_Orders'] = orders
                            # в OPC как массив строк
                            node = self._get_node(SEARCH_RESULT)
                            if node:
                                node.set_value(ua.DataValue(ua.Variant(orders, ua.VariantType.String)))
                        except Exception as e:
                            print(f"[OPC] handle ButtonLoadOrders failed: {e}")

                    # ---------- Выбор заказа по факту текста в OPC_Order ----------
                    try:
                        selected_from_opc = self._read_str(NODE_OPC_ORDER, "").strip()
                        if selected_from_opc:
                            with shared_data_lock:
                                prev = shared_data['OPC-DB'].get('OPC_Order', "").strip()
                            if selected_from_opc != prev:
                                # фиксируем выбор пользователя в словаре (а НЕ в OPC)
                                with shared_data_lock:
                                    shared_data['OPC-DB']['OPC_Order'] = selected_from_opc
                                logging.info(f"[OPC] Selected order detected: {selected_from_opc}")

                                # (опционально) почистить предыдущие витрины/данные
                                # with shared_data_lock:
                                #     shared_data['OPC-DB']['OPC_dataOrder'] = ""
                                #     shared_data['OPC-DB']['OPC_search_result'] = ""

                    except Exception as e:
                        print(f"[OPC] read OPC_Order failed: {e}")

                    # ---------- 5) Пушим статусы столов (1..3) ----------
                    # try:
                    #     with shared_data_lock:
                    #         t1 = dict(self.shared_dict.get(1, {}))
                    #         t2 = dict(self.shared_dict.get(2, {}))
                    #         t3 = dict(self.shared_dict.get(3, {}))

                    #     for n, td in ((1, t1), (2, t2), (3, t3)):
                    #         self._write(T(n, 'State'),    str(td.get('STATE', 'idle')),         ua.VariantType.String)
                    #         self._write(T(n, 'Sewing'),   int(td.get('SEWING', 0)),             ua.VariantType.Int16)
                    #         self._write(T(n, 'Loge'),     int(td.get('SEW_LOGE', 0)),           ua.VariantType.Int16)
                    #         self._write(T(n, 'DM'),       str(td.get('SEW_DM', '')),            ua.VariantType.String)
                    #         self._write(T(n, 'Progress'), int(td.get('SEW_PROGRESS', 0)),       ua.VariantType.Int16)
                    #         self._write(T(n, 'Result'),   int(td.get('SEW_RESULT', 0)),         ua.VariantType.Int16)
                    #         self._write(T(n, 'Error'),    str(td.get('SEW_ERROR', '')),         ua.VariantType.String)
                    # except Exception as e:
                    #     print(f"[OPC] push table states failed: {e}")

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



################################################# START Modbus Communication class l ###################################


class ModbusProvider:
    """Class MODBUS Communication with Modbus regul"""
    global Tray_robot
    global Cell, Cell2, Cell3, Cell1
    global command_toBOt

    def __init__(self):
        self.store = ModbusSlaveContext(
            hr=ModbusSequentialDataBlock(0, [0] * 100)
        )
        self.lock = threading.Lock()

        self.last_out = {
            # адрес : последнее записанное значение
            # холдинговые регистры (func=3) и адреса вы используете постоянные:
            25: None,   # SETUP_TABLE
            10: None, 12: None,  4: None,   # стол 1
            0: None,  2: None,  4: None,   # стол 2 (4 общий confirm/out)
            18: None, 20: None,  4: None,   # стол 3
            6: None,  8: None, 24: None,   # глобальные
        }

        self.server_thread = threading.Thread(target=self.run_modbus_server, daemon=True)
        self.server_thread.start()

        self.update_thread = threading.Thread(target=self.update_registers, daemon=True)
        self.update_thread.start()

        

    def _set_if_changed(self, addr, value):
        """Пишем в Modbus только если значение поменялось (минимум трафика и задержек)."""
        try:
            if self.last_out.get(addr) != value:
                self.store.setValues(3, addr, [value])
                self.last_out[addr] = value

        except Exception as e:
            print(f"[Modbus] write fail addr {addr}: {e}")

    def run_modbus_server(self):
        context = ModbusServerContext(slaves=self.store, single=True)
        print("Starting Modbus TCP server on 192.168.1.100:502")
        try:
            StartTcpServer(context, address=("192.168.1.100", 502))
        except Exception as e:
            print(f"Error starting Modbus server: {e}")

    def update_registers(self):
        global shared_data, Tray1, Tray2, Tray_robot, Cell, SETUP_TABLE, SUB_SETUP_TABLE
        while True:
            try:
                # --- READ Modbus -> локальные переменные (без shared_data лока) ---
                sub_setup_table = self.store.getValues(3, 26, count=1)[0]

                t1_sub_move = self.store.getValues(3, 9, count=1)[0]
                t1_sub_up   = self.store.getValues(3, 11, count=1)[0]
                t1_sub_rob  = self.store.getValues(3, 5, count=1)[0]
                t1_wp       = self.store.getValues(3, 15, count=1)[0]

                t2_sub_move = self.store.getValues(3, 1, count=1)[0]
                t2_sub_up   = self.store.getValues(3, 3, count=1)[0]
                t2_sub_rob  = self.store.getValues(3, 5, count=1)[0]
                t2_wp       = self.store.getValues(3, 7, count=1)[0]

                t3_sub_move = self.store.getValues(3, 17, count=1)[0]
                t3_sub_up   = self.store.getValues(3, 19, count=1)[0]
                t3_sub_rob  = self.store.getValues(3, 5, count=1)[0]
                t3_wp       = self.store.getValues(3, 23, count=1)[0]

                # --- КОРОТКИЙ ЛОК: обновить shared_data и собрать выход ---
                with shared_data_lock:
                    # апдейты входных sub_*
                    sd1 = shared_data[1]; sd2 = shared_data[2]; sd3 = shared_data[3]
                    sd1['sub_Reg_move_Table'] = t1_sub_move
                    sd1['sub_Reg_updown_Botloader'] = t1_sub_up
                    sd1['sub_Rob_Action'] = t1_sub_rob
                    sd1['workplace1'] = t1_wp

                    sd2['sub_Reg_move_Table'] = t2_sub_move
                    sd2['sub_Reg_updown_Botloader'] = t2_sub_up
                    sd2['sub_Rob_Action'] = t2_sub_rob
                    sd2['workplace1'] = t2_wp

                    sd3['sub_Reg_move_Table'] = t3_sub_move
                    sd3['sub_Reg_updown_Botloader'] = t3_sub_up
                    sd3['sub_Rob_Action'] = t3_sub_rob
                    sd3['workplace1'] = t3_wp

                    SUB_SETUP_TABLE = sub_setup_table

                    # забираем, что писать
                    t1_move = sd1['Reg_move_Table']; t1_updn = sd1['Reg_updown_Botloader']; t1_rob = sd1['Rob_Action']
                    t2_move = sd2['Reg_move_Table']; t2_updn = sd2['Reg_updown_Botloader']; t2_rob = sd2['Rob_Action']
                    t3_move = sd3['Reg_move_Table']; t3_updn = sd3['Reg_updown_Botloader']; t3_rob = sd3['Rob_Action']
                    print('--------------------------------------------------------------------------')
                    print(f'Rob action ={t1_rob}')
                    setup_table_local = SETUP_TABLE
                    tray_robot_local  = Tray_robot
                    cell_local        = Cell
                    tray2_local       = Tray2

                # --- WRITE Modbus, без shared_data лока, только если изменилось ---
                self._set_if_changed(25, setup_table_local)

                self._set_if_changed(10, t1_move)
                self._set_if_changed(12, t1_updn)
                if t1_rob != 0:
                    self._set_if_changed(4, t1_rob)

                self._set_if_changed(0, t2_move)
                self._set_if_changed(2, t2_updn)
                if t2_rob != 0:
                    self._set_if_changed(4, t2_rob)

                self._set_if_changed(18, t3_move)
                self._set_if_changed(20, t3_updn)
                if t3_rob != 0:
                    self._set_if_changed(4, t3_rob)

                self._set_if_changed(6,  tray_robot_local)
                self._set_if_changed(8,  cell_local)
                self._set_if_changed(24, tray2_local)

                # Отладочные принты можно пореже:
                # print(f"t1: Rob={t1_rob}/{t1_sub_rob} t2: Rob={t2_rob}/{t2_sub_rob} t3: Rob={t3_rob}/{t3_sub_rob}")

            except Exception as e:
                print(f"Error updating registers: {e}")

            time.sleep(1)  # быстрее цикл Modbus, чтобы управление было шустрее (20 Гц)


################################################# START MODBUS Communication class with Modbus regul ###################################


################################################# START TABLE CLASS #####################################################################
class Table:
    """ TABLE CLASS"""
    global Tray1, Tray2, Tray3, Tray_robot
    global Cell1, Cell2, Cell3, Cell
    global Order
    def __init__(self, name, shared_data, shared_data_lock, number, rob_manager):
        self.name = name
        self.data = shared_data.get(number, {})  # подсловарь объекта
        self.lock = shared_data_lock
        self.number = number
        self.rob_manager = rob_manager
        self._loge_state_lock = threading.Lock()   # ← вот этого не хватало
        # Переменные хранения состояний прошивки на ложе
        self._loge_outcome = {1: None, 2: None}  # 2=успех(норм), 3=брак
        self._loge_dm      = {1: None, 2: None}  # опционально: DM последней прошивки на ложе

    # Утилиты для записи/чтения результатов прошивки на ложе
    def _set_loge_outcome(self, loge: int, tray_code: int, dm: str | None = None):
        # tray_code: 2 = норм, 3 = брак (как у вас)
        with self._loge_state_lock:
            self._loge_outcome[loge] = tray_code
            if dm is not None:
                self._loge_dm[loge] = dm

    def _consume_loge_outcome(self, loge: int) -> int | None:
        # атомарно прочитать И ОБНУЛИТЬ
        with self._loge_state_lock:
            tr = self._loge_outcome.get(loge)
            self._loge_outcome[loge] = None
            return tr

    def _get_loge_dm(self, loge: int) -> str | None:
        with self._loge_state_lock:
            return self._loge_dm.get(loge)
        
    # Методы работы с глобальным словарем

    # Method write registers in modbus through modbus_provider
    def change_value(self, key, new_value):
        with self.lock:
            if key in self.data and self.data[key] != new_value:
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

    def _send_robot_command(self, base_command, cell_num=None, timeout_s: int = 600):
        """
        Отправляет команду роботу с разделением 220 (укладка) / 230 (забор).
        Если в течение timeout_s (по умолчанию 300 сек = 5 минут) нет подтверждения — 
        глобальная авария: останавливаем всё.
        """
        if EMERGENCY_STOP.is_set():
            logging.error(f"СТОЛ {self.number} Команда роботу игнорируется: EMERGENCY_STOP активен")
            SQLite.insert_log(f"Для стола {self.number} получен аварийный стоп, останавливаем все процессы", 0)
            return False

        # Проверки аргументов 
        if base_command in (220, 230):
            if cell_num not in (1, 2):
                raise ValueError("Для команд 220/230 укажите cell_num: 1 или 2")
        if not (1 <= self.number <= 3):
            raise ValueError(f"Некорректный номер стола: {self.number}. Допустимо: 1-3")

        # Построение команды 
        if base_command == 210:
            command = 210
        elif base_command == 241:
            command = 241
        elif base_command == 242:
            command = 242
        elif base_command == 220:  # Укладка
            command = 220 + (self.number - 1) * 2 + cell_num  # 221-226
        elif base_command == 230:  # Забор
            command = 230 + (self.number - 1) * 2 + cell_num  # 231-236
        else:
            command = base_command + self.number  # Прочие

        action_desc = "Укладка" if base_command == 220 else "Забор" if base_command == 230 else "Команда"
        logging.info(f"СТОЛ {self.number}, ЯЧЕЙКА {cell_num} → {action_desc}: {command}")
        self.change_value('Rob_Action', command)
        SQLite.insert_log(f"Роботу отправлена команда {command}", 0)

        start_time = time.time()
        try:
            while time.time() - start_time < timeout_s:
                if EMERGENCY_STOP.is_set():
                    logging.error(f"СТОЛ {self.number} Ожидание робота прервано: EMERGENCY_STOP активен")
                    return False

                result = self.read_value("sub_Rob_Action")
                if result == command:
                    self.change_value('Rob_Action', 0)
                    logging.info(f"Успешно: {command}")
                    return True
                elif result == 404:
                    self.change_value('Rob_Action', 0)
                    logging.error(f"Ошибка выполнения роботом: {command} (404)")
                    return False
                time.sleep(1)

            # 5 минут вышли — глобальная авария
            self.change_value('Rob_Action', 0)
            trigger_emergency(
                f"Робот не ответил на команду {command} (стол {self.number}) в течение {timeout_s} сек"
            )
            return False
        except Exception as e:
            # Любая неожиданная ошибка при общении с роботом — тоже авария
            self.change_value('Rob_Action', 0)
            trigger_emergency(
                f"Исключение при ожидании ответа робота на команду {command} (стол {self.number}): {e}"
            )
            return False

            

    def _send_table_command(self, command, timeout=6000000):
        print(f"[MAIN] СТОЛ {self.number} вызов функции отправки команды столу _send_table_command")
        logging.info(f"[MAIN] СТОЛ {self.number} вызов функции отправки команды столу _send_table_command")
        """
        Универсальный метод для отправки команд столу
        command: код команды 
            (101 - сдвинуть ложе1, 102 - сдвинуть ложе2, 
            103 - поднять ложе, 104 - опустить ложе)
        timeout: максимальное время ожидания ответа в секундах
        """
        start_time = time.time()
        command_name = {
            101: "Сдвинь плату освободив ложе1",
            102: "Сдвинь плату освободив ложе2",
            103: "Опустить ложе",
            104: "Поднять ложе"
        }.get(command, f"Команда {command}")

        print(f"[MAIN] СТОЛ {self.number} функция _send_table_command СТОЛ {self.number} Регул <- {command_name}")
        logging.info(f"[MAIN] СТОЛ {self.number} функция _send_table_command СТОЛ {self.number} Отправка команды {'Reg_updown_Botloader' if command in (103, 104) else 'Reg_move_Table'} = {command}")
        
        response_reg = None
        command_sent = False
        try: 
            # Отправляем команду
            if command in (103, 104):
                self.change_value('Reg_updown_Botloader', command)
                response_reg = 'sub_Reg_updown_Botloader'
                logging.info(f"СТОЛ {self.number} [COMMAND] отправка команды столу {command}")
            else:
                self.change_value('Reg_move_Table', command)
                response_reg = 'sub_Reg_move_Table'
            
            command_sent = True
            
            # Ожидаем подтверждения
            last_log_time = start_time
            while time.time() - start_time < timeout:
                result = self.read_value(response_reg)
                
                if result == command:
                    logging.info(f"СТОЛ {self.number} [COMMAND] получено подтверждение команды {command_name} значение {result}")
                    # ТОЛЬКО при успешном подтверждении сбрасываем команду
                    if command in (103, 104):
                        self.change_value('Reg_updown_Botloader', 0)
                    else:
                        self.change_value('Reg_move_Table', 0)
                    logging.info(f"СТОЛ {self.number} [COMMAND] Команда сброшена после подтверждения")
                    return True
                elif result == 404:
                    logging.error(f"СТОЛ {self.number} [COMMAND] ошибка выполнения команды: 404")
                    raise TableOperationFailed("Ошибка выполнения команды стола")
                elif result != 0:  # Добавляем проверку на другие ошибки
                    logging.warning(f"СТОЛ {self.number} [COMMAND] неожиданный ответ: {result}")
                
                # Логируем статус не чаще чем раз в 5 секунд
                current_time = time.time()
                if current_time - last_log_time >= 5:
                    logging.debug(f"СТОЛ {self.number} [COMMAND] функция _send_table_command Ожидание ответа на команду {command_name}. Текущее значение: {result}")
                    last_log_time = current_time
                
                time.sleep(0.5)
            
            # Если дошли сюда - таймаут, НИЧЕГО НЕ СБРАСЫВАЕМ
            logging.error(f"СТОЛ {self.number} [COMMAND] ТАЙМАУТ: Стол не ответил на команду {command}")
            raise TableTimeoutException(f"СТОЛ {self.number} [COMMAND] не ответил за {timeout} сек")
        
        except Exception as e:
            logging.error(f"СТОЛ {self.number} [COMMAND] Ошибка при отправке команды {command}: {e}")
            # При любой ошибке НИЧЕГО НЕ СБРАСЫВАЕМ
            raise

    def _try_take_photo_limited(self, max_attempts: int = 3, retry_delay: float = 1.0):
        """
        Сделать до max_attempts попыток снять фото. Без бесконечного ожидания.
        Возвращает (True, dm) при успехе, либо (False, None) при неудаче.
        """
        for _ in range(max_attempts):
            try:
                res, dm = CameraSocket.photo()
                if res == 200 and dm != "NoRead":
                    SQLite.insert_log(f"Стол {self.number}: камера дала DM = {dm}", 0)
                    return True, dm
            except Exception as e:
                logging.warning(f"Стол {self.number}: ошибка камеры: {e}")
            time.sleep(retry_delay)
        return False, None

    def _place_new_board_with_photo(self, target_loge: int, max_photo_attempts: int = 3,
                                    max_new_board_tries: int = 5) -> str:
        """
        При захваченном роботе:
        - взять плату из тары (210);
        - попытаться прочитать DM до max_photo_attempts раз;
        - если DM прочитан — уложить в target_loge (220) и вернуть DM;
        - иначе — увести в брак (242), +Cell3, и повторить с новой платой.
        Если подряд не удалось max_new_board_tries раз — авария.

        Возвращает DM уложенной платы.
        """
        global Tray_robot, Cell, Cell1, Cell3

        for _ in range(max_new_board_tries):
            # 1) взять новую плату из тары
            Tray_robot = 2
            with shared_data_lock:
                if shared_data['OPC-DB']['OPC_res_brak'] == False:
                    Cell1 += 1
                    Cell = Cell1
                else:
                    Cell1 = 0
                    Cell = Cell1
            time.sleep(1)  # дать Modbus прочитать

            if not self._send_robot_command(210):
                raise TableOperationFailed("Ошибка забора платы из тары (210)")

            # 2) пробуем получить DM ограниченно
            ok, dm = self._try_take_photo_limited(max_attempts=max_photo_attempts, retry_delay=1.0)

            if ok:
                # 3a) кладём на целевой ложемент
                if not self._send_robot_command(220, cell_num=target_loge):
                    raise TableOperationFailed(f"Ошибка укладки в ложемент {target_loge} (22X)")
                logging.info(f"Стол {self.number}: уложили плату с DM={dm} на ложе {target_loge}")
                Tray_robot = 0
                Cell = 0
                return dm
            else:
                # 3b) отправляем в брак и пробуем ещё одну плату
                logging.warning(f"Стол {self.number}: DM не прочитан за {max_photo_attempts} попыток — уводим в брак")
                Tray_robot = 3
                Cell3 += 1
                Cell = Cell3
                time.sleep(1)  # дать Modbus прочитать

                if not self._send_robot_command(242):
                    raise TableOperationFailed("Ошибка укладки в тару брака (242)")

                Tray_robot = 0
                Cell = 0

        # если сюда дошли — слишком много подряд «слепых» плат
        trigger_emergency(
            f"Стол {self.number}: не удалось получить читаемый DM после {max_new_board_tries} попыток подряд"
        )
        raise TableOperationFailed("Лимит попыток «новых плат» исчерпан")

    def _take_photo(self, max_attempts=3, retry_delay=1):
        """
        Метод для выполнения фотосъемки с обработкой ошибок и повторных попыток
        :param max_attempts: максимальное количество попыток получения фото
        :param retry_delay: задержка между попытками в секундах
        :return: кортеж (result_code, photo_data)
        """
        print(f"2 Стол {self.number} Камера <- сделай фото")
        logging.info(f"Стол {self.number} Камера <- сделай фото")
        
        # Первоначальные попытки получить фото
        for attempt in range(max_attempts):
            try:
                logging.debug(f"Стол {self.number} Попытка {attempt + 1}: запрос фото с камеры")
                res, photodata = CameraSocket.photo()
                print(f"Стол {self.number} С камеры получен ID {photodata}")
                logging.debug(f"Стол {self.number} Успех: получен ID фото {photodata}")
                SQLite.insert_log(f"Для стола {self.number} получено фото datamatrix платы значение = {photodata}", 0)
                
                # Если фото получено успешно, возвращаем результат
                if res == 200 and photodata != "NoRead":
                    return res, photodata
                    
            except Exception as e:
                print(f"Ошибка: камера недоступна. Детали: {e}")
                logging.warning(f"Попытка {attempt + 1}: ошибка подключения к камере: {str(e)}")
            
            time.sleep(retry_delay)
        
        # Если фото не получено после попыток, продолжаем ожидание
        while True:
            try:
                res, photodata = CameraSocket.photo()
                logging.debug(f"Стол {self.number} Ожидание фото. Код {res}, данные {photodata}")
                
                if res == 200 and photodata != "NoRead":
                    print(f"Стол {self.number} Фото успешно получено: {photodata}")
                    logging.debug(f"[END] Камера <- сделай фото: {photodata}")
                    return res, photodata
                else:
                    print(f"Стол {self.number} Ошибка получения фото с камеры (код: {res}, данные: {photodata})")
                    logging.warning(f"Стол {self.number} Ошибка получения фото с камеры (код: {res}, данные: {photodata})")
                    
            except Exception as e:
                print(f"Стол {self.number} Ошибка при запросе фото: {e}")
                logging.error(f"Стол {self.number} Ошибка при запросе фото: {str(e)}")
                
            time.sleep(retry_delay)
        # метод прошивки
    def start_sewing(self, photodata, loge, max_attempts=120, retry_delay=1):
        global Tray1, Tray2, Tray3
        """
        Метод для инициализации процесса прошивки с обработкой ошибок
        
        Args:
            photodata: Данные фото (серийный номер)
            loge: Номер ложемента для прошивки
            max_attempts: Максимальное количество попыток (по умолчанию 3)
            retry_delay: Задержка между попытками в секундах (по умолчанию 1)
        
        Returns:
            bool: True если прошивка успешно начата, False в случае ошибки
        
        Raises:
            TableOperationFailed: Если прошивка не удалась после всех попыток
        """
        #######OPC#######
        self.opc_set(shared_data, f'OPC_load_t{self.number}', 1) # 1-старт прошивки 0-конец прошивки
        self.opc_set(shared_data, f'OPC_res_load_t{self.number}', 0) # сброс состояния прошивки

        print(f"СТОЛ {self.number} Сервер <- Начни шить (ложемент {loge})")
        logging.info(f"[START2] Прошивка для стола {self.number}, ложемент {loge}")

        # Выбор параметра "stand_id"  в прошивку в зависимости от номера стола

        if self.number == 1:
            stand_id = "table_1"
            igle_table_choose = igle_table
        elif self.number == 2:
            stand_id = "table_2"
            igle_table_choose = igle_table2
        elif self.number == 3:
            stand_id = "table_3"
            igle_table_choose = igle_table3
        else: 
            print(f"Не могу получить номер стола для прошивальщика {self.number}")
            logging.critical(f"Не могу получить номер стола для прошивальщика {self.number}")

        
        # Инициализируем загрузчик прошивки
        db_connection_loader = SQL.DatabaseConnection()
        firmware_loader = Bot.FirmwareLoader(
            db_connection_loader, 
            igle_table_choose,
            stand_id, 
            Order, 
            photodata, 
            loge
        )
        
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            try:
                result, error_description = firmware_loader.loader(photodata, loge)
                SQLite.insert_log(f"Завершена прошивка платы {photodata} на {loge} с результатом {error_description}", 0)
                
                # Если прошивка не успешная - в отбраковку, иначе в нормальный лоток
                print(f"**************** error_description  {error_description}")
                if error_description is True:
                    tray_code = 2  # норм
                else:
                    tray_code = 3  # брак

                self._set_loge_outcome(loge, tray_code, photodata)

                # (опционально оставьте обратную совместимость с OPC/UI,
                if self.number == 1:
                    Tray1 = tray_code
                elif self.number == 2:
                    Tray2 = tray_code
                elif self.number == 3:
                    Tray3 = tray_code

                ####OPC####
                if error_description is True:
                    self.opc_set(shared_data, f'OPC_res_load_t{self.number}', 1) # # 2-успех 1-брак
                    self.opc_set(shared_data, f'OPC_log', f"Стол {self.number} ложе {loge} плата не прошла прошивку или тестирование") # # 2-успех 1-брак
                     
                else:
                    self.opc_set(shared_data, f'OPC_res_load_t{self.number}', 2) # # 2-успех 1-брак
                    self.opc_set(shared_data, f'OPC_log', f"Стол {self.number} ложе {loge} плата прошла прошивку и тестирование успешно") # # 2-успех 1-брак
                self.opc_set(shared_data, f'OPC_load_t{self.number}', 0) # 1-старт прошивки 0-конец прошивки
                
                
                if result == 200:
                    print(f"Прошивка успешно начата для ложемента {loge}")
                    logging.info(f"Прошивка успешно начата для стола {self.number}, ложемент {loge}")
                    return True
                elif result == 404:
                    logging.warning(f"Ошибка 404 от регула (попытка {attempt})")
                    if attempt == max_attempts:
                        raise TableOperationFailed(f"Ошибка прошивки: получен код 404 для ложемента {loge}")
            except Exception as e:
                print(f"Ошибка при запуске прошивки для ложемента {loge}: {e}")
                logging.error(f"Ошибка при запуске прошивки (попытка {attempt}): {str(e)}")
                if attempt == max_attempts:
                    raise TableOperationFailed(f"Не удалось начать прошивку для ложемента {loge} после {max_attempts} попыток")
            
            if attempt < max_attempts:
                time.sleep(retry_delay)

            ####OPC
            with self.lock:
                self.data['SEWING'] = 0
                # если была ошибка:
                # self.data['SEW_ERROR'] = str(e)  # или error_description
                self.data['STATE'] = 'idle'
        
        return False
    
    def opc_set(self, shared, key, value):
        # безопасно пишем в OPC-DB под одним локом
        with shared_data_lock:
            shared['OPC-DB'][key] = value

    
    #  # 1. Сдвигаем плату (ложе1)
    #     self._send_table_command(101)
        
    #     # 2. Забираем плату роботом
    #     self._send_robot_command(230)
        
    #     # 3. Сдвигаем плату (ложе2)
    #     self._send_table_command(102)
        
    #     # 4. Забираем плату с ложемента
    #     self._send_robot_command(233)


    ####################### TESTER BOTLOADER START ############################################################
    
    def test_botloader(self):
        global photodata
        global photodata1
        print(f"[НАЧАЛО] ЦИКЛ MAIN для {self.number} стола старт")
        logging.info(f"[НАЧАЛО] ЦИКЛ MAIN для {self.number} стола старт")

        current_loge = 2  # Начинаем с ложемента 2
        _, next_photodata = self._take_photo()
        while True:
            try:
                print(f"\n=== Обработка ложемента {current_loge} ===")
            
                # 1. Сдвигаем стол под прошивальщик
                self._send_table_command(101 if current_loge == 1 else 102)
                
                # 2. Опускаем прошивальщик
                self._send_table_command(103)

                time.sleep(3)
                
                # 3. Запускаем прошивку (используем фото, сделанное заранее)
                self.start_sewing(next_photodata, loge=current_loge)
                if self.number == 1:
                    Tray_robot = Tray1  # Отбраковка
                elif self.number == 2:
                    Tray_robot = Tray2  # Отбраковка
                elif self.number == 3:
                    Tray_robot = Tray3  # Отбраковка
                logging.info(f"[MAIN] Палата будет переложена в коробку {Tray_robot}")
                print(f"[MAIN] *********************Палата будет переложена в коробку {Tray_robot}")
                
                
                print("Получена команда поднятия ручки")
                logging.warning(f"Получена команда поднятия ручки")

                time.sleep(3)
                print(f"для {self.number}*******************************ШЬЕМ")
                
                
                # 4. Пока шьется на текущем ложементе, готовим следующий
                
                # 4.1 Определяем свободный ложемент
                free_loge = 2 if current_loge == 1 else 1
                

                # 4.3 Фотографируем новую плату
                _, next_photodata = self._take_photo()


                # 6. Поднимаем прошивальщик
                self._send_table_command(104)
                
                # 7. Сдвигаем стол для доступа к обработанной плате
                self._send_table_command(102 if current_loge == 1 else 101)
                
                
                # 9. Подготавливаем данные для следующей итерации
                current_loge = free_loge  # Переключаемся на следующий ложемент
                # next_photodata = new_photodata  # Используем фото новой платы
                
                print(f"Готово! Следующая итерация: ложемент {current_loge}")
                
            except Exception as e:
                logging.error(f"Ошибка в цикле обработки: {str(e)}")
                # Здесь может быть логика восстановления
                time.sleep(5)
    ####################### TESTER BOTLOADER STOP ############################################################
    


    ####################### DEFENCE START ############################################################
    def defence_robo_cycle(self):
        global photodata
        global Tray1
        Tray1 = 1
        global Cell1
        global Order
        print(f"[НАЧАЛО] ЦИКЛ DEFENCE для {self.number} стола старт")
        logging.info(f"[НАЧАЛО] ЦИКЛ DEFENCE для {self.number} стола старт")
        ######################################################

        print(f"СТОЛ {self.number} 1 Регул <- Сдвинь плату освободив ложе1.")
        logging.info(f"СТОЛ {self.number} Отправка команды Reg_move_Table = 101")
        self._send_table_command(101)
        time.sleep(1)

        # Робот забери плату
        while not self.rob_manager.acquire(self.number):
            logging.info(f"СТОЛ {self.number} ждет освобождения робота")
            time.sleep(1)  # Подождать 1 секунду
            

        try:
            print(f"[Начало] Стол {self.number} Захват робота столом")
            logging.info(f"[Начало] Стол {self.number} Захват робота столом")
            print(f"СТОЛ {self.number} 2 Робот <- Забери плату с ложе 1.")
            self._send_robot_command(230, cell_num=1)
            time.sleep(1)
        finally:
            print(f"[Конец] Стол {self.number} Робот освобожден столом")
            logging.info(f"[Конец] Стол {self.number} Робот освобожден столом")
            self.rob_manager.release(self.number)

        print(f"[Начало] Стол {self.number} Регул <- Сдвинь плату освободив ложе2.")
        logging.info(f"[Начало] Стол {self.number} Регул <- Сдвинь плату освободив ложе2.")
        self._send_table_command(102)
        time.sleep(1)
        
        # Робот забери плату
        while not self.rob_manager.acquire(self.number):
            logging.info(f"СТОЛ {self.number} ждет освобождения робота")
            time.sleep(1)  # Подождать 1 секунду

        try:
            print(f"[Начало] Стол {self.number} Захват робота столом")
            logging.info(f"[Начало] Стол {self.number} Захват робота столом")
            print(f"СТОЛ {self.number} 2 Робот <- Забери плату с ложе 1.")
            self._send_robot_command(230, cell_num=2)  # self.number=3
            time.sleep(1)
        finally:
            print(f"[Конец] Стол {self.number} Робот освобожден столом")
            logging.info(f"[Конец] Стол {self.number} Робот освобожден столом")
            self.rob_manager.release(self.number)
    ####################### DEFENCE STOP ############################################################

    ####################### SETUP START ############################################################

    def setup_robo_cycle(self):
        global photodata
        global photodata1
        global Tray1, Tray_robot
        global Cell1,Cell2, Cell3,Cell
        global Order
        print(f"[НАЧАЛО] ЦИКЛ SETUP для {self.number} стола старт")
        logging.info(f"[НАЧАЛО] ЦИКЛ SETUP для {self.number} стола старт")
        ######################################################
        #input("нажми ентер")
        
        # Робот <- Забери плату из тары
        # Сделать фото
        # Робот <- Уложи плату в ложемент тетситрования

        while not self.rob_manager.acquire(self.number):
            logging.info(f"СТОЛ {self.number} ждет освобождения робота")
            time.sleep(1)  # Подождать 1 секунду

        try:
            print(f"[Начало] Стол {self.number} Захват робота столом")
            logging.info(f"[Начало] Стол {self.number} Захват робота столом")

            # 1. Забираем первую плату из тары
            print(f"1 Стол {self.number} Робот <- Забери плату из тары")
            logging.info(f"Стол {self.number} Робот <- Забери плату из тары")
            Tray_robot = 2          # Ящик с новыми платами
            Cell1 += 1              # <-- счётчик тары новых
            Cell = Cell1            # <-- отдаём ячейку в Modbus
            time.sleep(1)           # чтобы Modbus успел прочитать
            if not self._send_robot_command(210):
                raise TableOperationFailed("Ошибка забора первой платы из тары")
            time.sleep(1)
            
            # 2. Фотографируем первую плату
            _, photodata1 = self._take_photo()
            
            # 3. Укладываем первую плату на ложемент 2
            print(f"3 Стол {self.number} Робот <- Уложи плату в ложемент тетситрования 2")
            logging.info(f"3 Стол {self.number} Робот <- Уложи плату в ложемент тетситрования 2")
            if not self._send_robot_command(220, cell_num=2):
                raise TableOperationFailed("Ошибка укладки в ложемент 2")
    
        finally:
            print(f"[Конец] Стол {self.number} Робот освобожден столом")
            logging.info(f"[Конец] Стол {self.number} Робот освобожден столом")
            self.rob_manager.release(self.number)
        print(f"[СТОП] ЦИКЛ SETUP для {self.number} стола старт")
        logging.info(f"[СТОП] ЦИКЛ SETUP для {self.number} стола старт")
    
    ####################### SETUP END ##############################################################
    
    
    ####################### MAIN START ############################################################
    def robo_main_cycle(self):
        import threading, time, logging
        from dataclasses import dataclass
        global Tray1, Cell1,Cell2, Cell3, Cell, photodata, photodata1, Tray_robot

        SEW_WAIT_TIMEOUT = 900000  # сек
        ROBOT_WAIT_TIMEOUT = 900000 # сек

        print(f"[MAIN] ЦИКЛ MAIN для {self.number} стола старт")
        log_message(self.number, "info", f"[MAIN] ЦИКЛ MAIN для {self.number} стола старт")

        # Стартуем: на ложе 2 уже есть плата — начнём шить с него
        current_loge = 2
        photodata1 = '111'                     # DM для первой прошивки (если требуется)
        next_photodata = photodata1            # DM, который будет прошиваться на current_loge

        # Поток «идущей» прошивки 1-й итерации (как было)
        in_flight_sewing_thread = None

        def _move_table_to_loge(loge: int):
            self._send_table_command(101 if loge == 1 else 102)


        def _robot_remove(loge: int) -> bool:
            # было: 231/232 -> fallback 230
            # стало: всегда используем базовую 230 + cell_num, пусть класс сам посчитает 231..236
            return self._send_robot_command(230, cell_num=loge)

        def _robot_place(loge: int) -> bool:
            # было: 221/222 -> fallback 220
            # стало: всегда используем базовую 220 + cell_num, пусть класс сам посчитает 221..226
            return self._send_robot_command(220, cell_num=loge)

        # Флаг: после первой итерации переходим в новый «двухпоточный» режим
        parallel_join_mode = False

        while True:
            SQLite.insert_log(f"Начало работы с РТК", "user", 0)
            try:
                print(f"\n=== Обработка ложемента {current_loge} ===")
                if EMERGENCY_STOP.is_set():
                    log_message(self.number, "critical", f"[MAIN] СТОЛ {self.number} аварийно остановлен (EMERGENCY_STOP)")
                    return

                if in_flight_sewing_thread is None and not parallel_join_mode:
                    # ---------------- ПЕРВЫЙ ЦИКЛ (БЕЗ ИЗМЕНЕНИЙ) ----------------
                    free_loge = 2 if current_loge == 1 else 1
                    log_message(self.number, "info", f"[MAIN] Старт первого цикла free_loge = {free_loge} current_loge = {current_loge}")

                    # 1) Поднять голову (страховка), подвести current_loge
                    self._send_table_command(104)
                    log_message(self.number, "info", f"[MAIN] Подняли прошивальщик (перед подводом текущего ложемента)")
                    

                    _move_table_to_loge(current_loge)
                    log_message(self.number, "info", f"[MAIN] Сдвигаем стол {self.number} под прошивальщик (под головкой ложе {current_loge})")

                    # 2) ОДНОВРЕМЕННО: опускаем прошивальщик И работаем с роботом на free_loge
                    self._send_table_command(103)
                    log_message(self.number, "info", f"[MAIN] Опускаем прошивальщик стол {self.number} (параллельно с операциями робота)")


                    while not self.rob_manager.acquire(self.number):
                        logging.info(f"[MAIN] СТОЛ {self.number} ждет освобождения робота (загрузка новой на ложе {free_loge})")
                        log_message(self.number, "info", f"[MAIN] Робот захвачен столом идет загрузка платы на )")
                        time.sleep(1)
                    try:
                        dm_for_free = self._place_new_board_with_photo(free_loge, max_photo_attempts=3, max_new_board_tries=5)
                    finally:
                        logging.info(f"[MAIN] Стол {self.number} Робот освобожден столом (после загрузки новой на free_loge)")
                        self.rob_manager.release(self.number)
                    # 3) Запускаем прошивку current_loge
                    print(f"-------------------------------------------{current_loge}")
                    sewing_thread = threading.Thread(
                        target=self.start_sewing, args=(next_photodata, current_loge), daemon=True
                    )
                    sewing_thread.start()
                    logging.info(f"[MAIN] СТОЛ {self.number} Прошивка запущена на ложе {current_loge} (DM={next_photodata})")

                    # 4) Дождаться завершения прошивки current_loge
                    sewing_thread.join(timeout=SEW_WAIT_TIMEOUT)
                    if sewing_thread.is_alive():
                        logging.error(f"[MAIN] СТОЛ {self.number} Таймаут прошивки на ложе {current_loge}")
                        raise RuntimeError("Sewing timeout (initial cycle)")
                    logging.info(f"[MAIN] СТОЛ {self.number} Прошивка на ложе {current_loge} завершена")
                    
                    # 5) Поднять голову, перейти на free_loge
                    self._send_table_command(104)
                    logging.info(f"[MAIN] СТОЛ {self.number} Подняли прошивальщик с ложе {current_loge}")

                    _move_table_to_loge(free_loge)
                    logging.info(f"[MAIN] СТОЛ {self.number} сдвинут по оси X (под головкой теперь ложе {free_loge})")

                    # 6) ОДНОВРЕМЕННО: опускаем прошивальщик И работаем с роботом на старом ложе
                    self._send_table_command(103)
                    logging.info(f"[MAIN] Опускаем прошивальщик на ложе {free_loge} (параллельно с операциями робота)")

                    while not self.rob_manager.acquire(self.number):
                        logging.info(f"[MAIN] СТОЛ {self.number} ждет освобождения робота (выгрузка+загрузка на ложе {current_loge})")
                        time.sleep(1)
                    try:
                        print(f" В стол {self.number}")
                        # стало: взять и обнулить исход ровно для того ложемента, с которого снимаем
                        tr = self._consume_loge_outcome(current_loge)

                        if tr is None:
                            # страховка: исход не найден — можно:
                            # 1) считать брак/оставить как есть, 2) кинуть исключение, 3) повторить опрос.
                            # Я бы явно зафейлил, чтобы не перепутать партии:
                            tr = 3
                            logging.warning(
                                f"[MAIN] СТОЛ {self.number} Нет исхода прошивки для ложемента {current_loge}; "
                                f"помечаем как БРАК и уносим в 242."
                            )
                            raise RuntimeError(f"Не найден исход прошивки для ложемента {current_loge}")

                        Tray_robot = tr  # 2 или 3

                        if tr == 2:
                            Cell2 += 1
                            Cell = Cell2
                        elif tr == 3:
                            Cell3 += 1
                            Cell = Cell3
                        else:
                            # на всякий случай
                            raise RuntimeError(f"Неожиданный номер трея для укладки: {tr}")

                        time.sleep(1)  # дать Modbus прочитать
                        # снять обработанную
                        if not self._send_robot_command(230, cell_num=current_loge):
                            raise TableOperationFailed(f"Ошибка забора с ложемента {current_loge}")
                        logging.info(f"[MAIN] СТОЛ {self.number} Забираем обработанную плату с ложемента {current_loge}")
                        if tr == 2:
                            if not self._send_robot_command(241): 
                                raise TableOperationFailed("Ошибка укладки в тару")
                            logging.info(f"[MAIN] СТОЛ {self.number} Укладываем плату в тару с упешно прошитыми платами (с ложе {current_loge})")
                            Cell=0 # чистим CEll модбаса
                        else:
                            if not self._send_robot_command(242):
                                raise TableOperationFailed("Ошибка укладки в тару")
                            logging.info(f"[MAIN] СТОЛ {self.number} Укладываем плату в тару брака (с ложе {current_loge})")
                            Cell=0 # чистим CEll модбаса
                        tr = 0
                        
                        dm_for_old = self._place_new_board_with_photo(current_loge, max_photo_attempts=3, max_new_board_tries=5)

                    finally:
                        print(f"[MAIN] Стол {self.number} Робот освобожден столом (после выгрузки+загрузки старого ложемента)")
                        logging.info(f"[MAIN] Стол {self.number} Робот освобожден столом (после выгрузки+загрузки старого ложемента)")
                        self.rob_manager.release(self.number)

                    # 7) Запускаем прошивку на free_loge как in-flight к началу 2-й итерации
                    next_sewing_thread = threading.Thread(
                        target=self.start_sewing, args=(dm_for_free, free_loge), daemon=True
                    )
                    next_sewing_thread.start()
                    logging.info(f"[MAIN] СТОЛ {self.number} Прошивка запущена на ложе {free_loge} (DM={dm_for_free})")

                    in_flight_sewing_thread = next_sewing_thread
                    current_loge = free_loge           # на нём сейчас идёт in-flight
                    next_photodata = dm_for_old        # DM на противоположном (перезаряженном) ложе
                    parallel_join_mode = True          # со 2-й итерации — новый режим
                    logging.info(f"[MAIN] Подготовка к 2-й итерации: current_loge={current_loge}, next_DM={next_photodata}")

                else:
                    # ---------------- СО 2-Й ИТЕРАЦИИ: ДВА ПАРАЛЛЕЛЬНЫХ ПОТОКА ----------------
                    # 0) Дождаться завершения in-flight на current_loge (с конца 1-й итерации)
                    if in_flight_sewing_thread is not None:
                        logging.info(f"[MAIN] Ожидаем завершения прошивки (in-flight) на ложе {current_loge}")
                        in_flight_sewing_thread.join(timeout=SEW_WAIT_TIMEOUT)
                        if in_flight_sewing_thread.is_alive():
                            logging.error(f"[MAIN] Таймаут ожидания прошивки на ложе {current_loge}")
                            raise RuntimeError("Sewing join timeout (parallel mode)")
                        in_flight_sewing_thread = None
                        logging.info(f"[MAIN] Прошивка на ложе {current_loge} завершена (in-flight)")

                    # 1) Поднять голову 104 — ОТДЕЛЬНО
                    self._send_table_command(104)
                    logging.info(f"[MAIN] СТОЛ {self.number} 104 — подняли прошивальщик")

                    # 2) Подвести противоположное ложе 10X — ОТДЕЛЬНО
                    next_loge = 2 if current_loge == 1 else 1
                    _move_table_to_loge(next_loge)
                    logging.info(f"[MAIN] СТОЛ {self.number} 10{'1' if next_loge==1 else '2'} — подвели ложе {next_loge}")

                    # --- Запускаем 2 параллельных потока ---
                    dm_holder = {"dm": None}
                    thread_errors = {"table": None, "robot": None}

                    def table_thread():
                        global Tray1, Tray2, Tray3, Tray_robot, Cell,Cell1, Cell2, Cell3
                        try:
                            # 3) Стол: 103 + прошивка на next_loge
                            self._send_table_command(103)
                            logging.info(f"[MAIN] СТОЛ {self.number} 103 — опустили прошивальщик на ложе {next_loge}")
                            # прошивка синхронно внутри потока
                            self.start_sewing(next_photodata, next_loge)
                            logging.info(f"[MAIN] СТОЛ {self.number} Прошивка на ложе {next_loge} завершена")
                        except Exception as e:
                            thread_errors["table"] = e


                        # снять обработанную

                    def robot_thread():
                        global Cell, Cell2, Cell3, Tray_robot

                        try:
                            # Захватываем робота на весь блок операций current_loge
                            while not self.rob_manager.acquire(self.number):
                                logging.info(f"[MAIN] СТОЛ {self.number} ждёт робота (операции на ложе {current_loge})")
                                time.sleep(1)
                            try:
                                # 1) Снять обработанную плату с current_loge
                                if not self._send_robot_command(230, cell_num=current_loge):
                                    raise TableOperationFailed(f"Ошибка забора с ложемента {current_loge} (23X/230)")

                                logging.info(f"[MAIN] СТОЛ {self.number} сняли плату с ложемента {current_loge}")

                                # 2) Получить итог прошивки АТОМАРНО для этого ложемента
                                tr = self._consume_loge_outcome(current_loge)
                                if tr is None:
                                    # страховка: если по какой-то причине исхода нет — считаем брак
                                    tr = 3
                                    logging.warning(
                                        f"[MAIN] СТОЛ {self.number}: нет исхода прошивки для ложемента {current_loge}; "
                                        f"помечаем как БРАК (242)."
                                    )

                                # 3) Разложить по лоткам (успех -> 241, брак -> 242) и корректно проставить Cell
                                Tray_robot = tr  # 2 или 3
                                if tr == 2:
                                    Cell2 += 1
                                    Cell = Cell2
                                    time.sleep(1)  # дать Modbus прочитать
                                    if not self._send_robot_command(241):
                                        raise TableOperationFailed("Ошибка укладки в тару успеха (241)")
                                    logging.info(f"[MAIN] СТОЛ {self.number} уложили плату в тару успеха (с ложе {current_loge})")
                                elif tr == 3:
                                    Cell3 += 1
                                    Cell = Cell3
                                    time.sleep(1)  # дать Modbus прочитать
                                    if not self._send_robot_command(242):
                                        raise TableOperationFailed("Ошибка укладки в тару брака (242)")
                                    logging.info(f"[MAIN] СТОЛ {self.number} уложили плату в тару брака (с ложе {current_loge})")
                                else:
                                    raise RuntimeError(f"Неожиданный номер трея для укладки: {tr}")

                                # очистка отображаемых ячеек после укладки
                                Tray_robot = 0
                                Cell = 0
                                tr = 0

                                # 4) ВЗЯТЬ НОВУЮ ПЛАТУ и УЛОЖИТЬ НА current_loge
                                #    — с ограниченными попытками фото; если DM не читается, плата уходит в брак и берём следующую
                                dm_loaded = self._place_new_board_with_photo(
                                    target_loge=current_loge,
                                    max_photo_attempts=3,   # <= как просили
                                    max_new_board_tries=5   # предохранитель от бесконечного цикла брака
                                )
                                logging.info(f"[MAIN] СТОЛ {self.number} новая плата уложена на ложе {current_loge}, DM={dm_loaded}")

                                # 5) Передаём DM в общий держатель для следующей итерации
                                dm_holder["dm"] = dm_loaded

                            finally:
                                self.rob_manager.release(self.number)
                                logging.info(f"[MAIN] Стол {self.number} Робот освобождён (после 23X → сортировка → новая плата)")
                        except Exception as e:
                            thread_errors["robot"] = e


                    t_table = threading.Thread(target=table_thread, daemon=True, name=f"tbl-{self.number}")
                    t_robot = threading.Thread(target=robot_thread, daemon=True, name=f"bot-{self.number}")

                    t_table.start()
                    t_robot.start()

                    # ЖДЁМ ОКОНЧАНИЯ ОБОИХ ПОТОКОВ
                    t_table.join(timeout=SEW_WAIT_TIMEOUT)
                    t_robot.join(timeout=ROBOT_WAIT_TIMEOUT)

                    # Проверка таймаутов
                    if t_table.is_alive():
                        logging.error(f"[MAIN] Таймаут потока стола (103+sew) на ложе {next_loge}")
                        raise RuntimeError("Table thread timeout")
                    if t_robot.is_alive():
                        logging.error(f"[MAIN] Таймаут потока робота (23X/241/210/22X) на ложе %s", current_loge)
                        raise RuntimeError("Robot thread timeout")

                    # Прокинуть исключения из потоков
                    if thread_errors["table"]:
                        raise thread_errors["table"]
                    if thread_errors["robot"]:
                        raise thread_errors["robot"]

                    # Подготовка следующей итерации
                    if not dm_holder["dm"]:
                        raise RuntimeError("Не получен DM с камеры при перезарядке противоположного ложемента")

                    next_photodata = dm_holder["dm"]  # DM для следующей прошивки
                    current_loge = next_loge          # мы только что шили на next_loge
                    logging.info(f"[MAIN] Следующая итерация: current_loge={current_loge}, next_DM={next_photodata}")

            except Exception as e:
                logging.error(f"Ошибка в цикле обработки: {str(e)}")
                if EMERGENCY_STOP.is_set():
                    logging.critical(f"[MAIN] СТОЛ {self.number} аварийно остановлен во время восстановления")
                    return
                try:
                    self._send_table_command(104)
                    logging.info(f"[MAIN] СТОЛ {self.number} Восстановление: подняли прошивальщик")
                except Exception:
                    logging.exception(f"[MAIN] СТОЛ {self.number} Не удалось поднять прошивальщик в аварийной секции")
                try:
                    _move_table_to_loge(current_loge)
                    logging.info(f"[MAIN] СТОЛ {self.number} Восстановление: стол сдвинут по оси X (под головкой ложе {current_loge})")
                except Exception:
                    logging.exception(f"[MAIN] СТОЛ {self.number} Не удалось сдвинуть стол в аварийной секции")
                time.sleep(1)

    ####################### MAIN STOP ############################################################

    def testcycle(self):
        result, photo_id = self._take_photo()
        if result == 200:
            print(f"Успешно получено фото с ID: {photo_id}")
        else:
            print("Не удалось получить фото")

        # self._send_table_command(101)
        # self._send_table_command(102)
        # self._send_table_command(103)
        # self._send_table_command(104)
        
        """
        # 2. Забираем плату роботом
        while not self.rob_manager.acquire(self.number):
            logging.info(f"СТОЛ {self.number} ждет освобождения робота")
            time.sleep(1)  # Подождать 1 секунду

        try:
            self._send_robot_command1(230)  
            self._send_robot_command1(231)
            self._send_robot_command1(232)
        finally:
            self.rob_manager.release(self.number)

        """

    
################################################# STOP TABLE CLASS #####################################################################


    def pause(self):
        time.sleep(2)


#########################Блок логики запуска потоков#####################################################################################
# Глобальные переменные (у тебя уже есть)
# shared_data, shared_data_lock

# держим ссылки на запущенные потоки
running_threads = {}

def start_threads_if_needed(targets: dict, do_defence=False, do_setup=False):
    with shared_data_lock:
        opc_db = shared_data.get('OPC-DB', {})
        if not opc_db.get('OPC_START_RTK', False):
            return
        flags = {
            1: opc_db.get('OPC_strat_t1', False),
            2: opc_db.get('OPC_strat_t2', False),
            3: opc_db.get('OPC_strat_t3', False),
        }

    for tid, need_start in flags.items():
        if need_start and tid not in running_threads:
            table = targets[tid]
            t = threading.Thread(
                target=run_table_pipeline,
                args=(table, do_defence, do_setup),
                name=f"Table{tid}",
                daemon=False  # Лучше НЕ daemon, чтобы процесс не умер раньше времени
            )
            t.start()
            running_threads[tid] = t
            print(f"__________________{tid} стол")
            time.sleep(15)  # <-- пауза между столами

    # with shared_data_lock:
    #     shared_data['OPC-DB']['OPC_START'] = False


def run_table_pipeline(table: Table, do_defence=True, do_setup=True):
    try:
        if do_defence:
            table.defence_robo_cycle()
        if do_setup:
            table.setup_robo_cycle()
    except Exception:
        logging.exception(f"[PIPELINE] prep failed for table {table.number}")
        # по ситуации можно вызвать trigger_emergency(...)
    # после подготовки уходим в основной бесконечный цикл
    table.robo_main_cycle()

    


if __name__ == "__main__":

    modbus_provider = ModbusProvider()
    rob_manager = RobActionManager()
    

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

    # Стартуем вспосогательный сервер перепарвки данных от прошивальщика в основной скрпит. 
    # делаем его как дочерний подпроцесс
    proc = subprocess.Popen([sys.executable, "ServerRTK.py"])



    # Создаём столы
    table1 = Table("Table1", shared_data, shared_data_lock, 1, rob_manager)
    table2 = Table("Table2", shared_data, shared_data_lock, 2, rob_manager)
    table3 = Table("Table3", shared_data, shared_data_lock, 3, rob_manager)

    # Выполняем однократные методы для каждого стола
    # for table in (table1, table2, table3):
    #     table.defence_robo_cycle()
    #     table.setup_robo_cycle()

    # Создаем потоки для основного цикла
    
    thread1 = threading.Thread(target=table1.robo_main_cycle)
    thread2 = threading.Thread(target=table2.robo_main_cycle)
    thread3 = threading.Thread(target=table3.robo_main_cycle)

    # Тестовые циклы только прошивка
    # thread1 = threading.Thread(target=table1.test_botloader)
    # thread2 = threading.Thread(target=table2.test_botloader)
    # thread3 = threading.Thread(target=table3.test_botloader)

    while True:
        print (f'Ожидание от регула, что столы в начальной позиции')
        logging.info(f"Ожидание от регула, что столы в начальной позиции")
        time.sleep(1)
        SETUP_TABLE = 1
        if SUB_SETUP_TABLE == 1:
            SETUP_TABLE = 0
            logging.info(f"получен ответ от регула, что столы приведены в нулевое положении")
            print (f'получен ответ от регула, что столы приведены в нулевое положении ')
            break
        


    ##############################################Запускаем потоки#######################################

    # выставляешь флаги...
    # with shared_data_lock:
    #     shared_data['OPC-DB']['OPC_START_RTK'] = True
    #     shared_data['OPC-DB']['OPC_strat_t1'] = True
    #     shared_data['OPC-DB']['OPC_strat_t2'] = True
    #     shared_data['OPC-DB']['OPC_strat_t3'] = True

    # и запускаешь реальные циклы:
    # старт пайплайна (сейчас defence/setup можно выключить False/False, потом включишь True/True)
    start_threads_if_needed(
        {1: table1, 2: table2, 3: table3},
        do_defence=False,
        do_setup=False
    )

    # Ждём глобальной аварии или завершения потоков
    try:
        while True:
            if EMERGENCY_STOP.is_set():
                logging.critical("[MAIN] Поймали EMERGENCY_STOP. Останавливаемся.")
                break

            # Если хочешь поддержать «поздний старт по OPC», можно периодически вызывать:
            start_threads_if_needed({
                1: table1,
                2: table2,
                3: table3
            })

            # Если все запущенные потоки умерли — выходим
            if running_threads and all(not t.is_alive() for t in running_threads.values()):
                logging.error("[MAIN] Все потоки столов завершились")
                break

            time.sleep(1)
    finally:
        # Пытаемся штатно остановить сервисные части
        try:
            opc_client.stop()
        except Exception:
            logging.exception("Ошибка при остановке OPC клиента")

        try:
            db_sync.stop()
        except Exception:
            logging.exception("Ошибка при остановке потока синхронизации БД")

        # Дожимаем потоки столов
        for t in (thread1, thread2, thread3):
            try:
                if t.is_alive():
                    t.join(timeout=5)
            except Exception:
                pass


        print("Все потоки завершены.")

    proc.terminate()  # По выходу из main завершить сервер