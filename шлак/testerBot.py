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

# Пользовательский калсс прошивальщика
import Botloader as Bot

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
            except Exception as e:
                print(f"Error updating registers: {e}")
            time.sleep(1)

################################################# START MODBUS Communication class with Modbus regul ###################################


################################################# START TABLE CLASS #####################################################################
class Table:
    """ TABLE CLASS"""
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
                logging.info(f"Ожидание ответа от стола... Текущее значение: {result1}")
            elif result1 == 404:
                print(f"От регула получен код 404 на операции движения стола")
                logging.info("От регула получен код 404 (успех операции движения стола)")
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
                print(f"Ждем ответ от робота, что плату забрал получено от робота = {result1}")
                logging.info(f"Ожидание ответа от робота... Текущее значение: {result1}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции взять плату с ложа")
                logging.info("От робота получен код 404 (успех операции 'взять плату')")
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
                logging.info(f"Ждем ответ о том что стол сдвинут - сейчас значение = {result1}")
            elif result1 == 404:
                print(f"От регула получен код 404 на операции движения стола")
                logging.info(f"От регула получен код 404 на операции движения стола")
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

        # 5 Робот <- Забери плату из тары
        print("5 Робот <- забрать плату из тары")
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
        print("6 Камера <- сделай фото")
        a = CameraSocket.photo()
        print (a)
        time.sleep(1)
        a = CameraSocket.photo()
        print (a)
        time.sleep(1)
        a = CameraSocket.photo()
        print (a)
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
        a = CameraSocket.photo()
        print (a)
        time.sleep(1)
        a = CameraSocket.photo()
        print (a)
        time.sleep(1)
        a = CameraSocket.photo()
        print (a)
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
        print("****ЦИКЛ MAIN")
        
        ######################################################
        # input("нажми ентер")
        # 1 Робот <- Забери плату из тары
        print("1 Робот <- забрать плату из тары")
        logging.info(f"[НАЧАЛО] Робот <- забрать плату из тары")
        self.change_value('Rob_Action', 210)
        while True:
            logging.debug(f"[Статус] sub_Rob_Action = {result1}")

            result1 = self.read_value("sub_Rob_Action")
            if result1 != 210:
                print(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
                logging.info(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции забрать из тары плату")
                logging.info(f"От робота получен код 404 на на операции забрать из тары плату")
                
            else:
                logging.info("Операция забора из тары успешно завершена")
                break
            time.sleep(1)

        logging.info(f"[Завершение] Робот <- забрать плату из тары")
        self.change_value('Rob_Action', 0)
        result1=0
        ##########################################################
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
        ###########################################################################



        ############################################################
        # 3 Робот <- Уложи плату в ложемент тетситрования
        print("3 Робот <- Уложи плату в ложемент тетситрования 1")
        logging.info(f"[НАЧАЛО] Робот <- Уложи плату в ложемент тетситрования 1")
        
        self.change_value('Rob_Action', 221)
        logging.debug("Отправлена команда Rob_Action=221")
        while True:
            result1 = self.read_value("sub_Rob_Action")
            logging.debug(f"[Статус] sub_Rob_Action = {result1}")

            if result1 != 221:

                logging.info(f"Ждем ответ от робота, что плата уложена в ложемент, получено от робота = {result1}")
                print(f"Ждем ответ от робота, что плата уложена в ложемент, получено от робота = {result1}")
                time.sleep(1)
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции уложить плату в ложемент")
                logging.info(f"От робота получен код 404 на на операции уложить плату в ложемент")
                time.sleep(1)
            else:
                break
            logging.info(f"[Завершение] Робот <- Уложи плату в ложемент тетситрования 1")
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1 = 0
        ####################################################################
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


        
        #############################################################################
        # 5 Робот <- Забери плату из тары
        print("5 Робот <- Забери плату из тары")
        logging.info(f"[НАЧАЛО] Робот <- Забери плату из тары")
        self.change_value('Rob_Action', 210)
        logging.debug("Отправлена команда Rob_Action', 210")
        while True:
            result1 = self.read_value("sub_Rob_Action")
            logging.debug(f"[Статус] sub_Reg_move_Table = {result1}")
            if result1 != 210:
                print(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
                logging.info(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции забрать из тары плату")
            else:
                break
            time.sleep(1)
        logging.info(f"[Завершение] Робот <- Забери плату из тары")
        self.change_value('Rob_Action', 0)
        ##################################################################################
        #input("нажми ентер")



        ################################################################
        # 6 Делаем фото платы
        print("6 Камера <- сделай фото")
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
        ###################################################################################
        # 7 Робот <- Уложи плату в ложемент тетситрования
        print("7 Робот <- Уложи плату в ложемент тетситрования 2")
        logging.info(f"[НАЧАЛО] Робот <- Уложи плату в ложемент тетситрования 2")
        self.change_value('Rob_Action', 222)
        logging.debug("Отправлена команда 'Rob_Action', 222")
        while True:
            result1 = self.read_value("sub_Rob_Action")
            logging.debug(f"[Статус] sub_Rob_Action = {result1}")

            if result1 != 222:
                print(f"Ждем ответ от робота, что плату уложили = {result1}")
                logging.info(f"Ждем ответ от робота, что плату уложили = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции уложить плату")
                logging.info(f"От робота получен код 404 на на операции уложить плату")
            else:
                break
            time.sleep(1)
        logging.info(f"[Завершение] Робот <- Уложи плату в ложемент тетситрования 2")
        self.change_value('Rob_Action', 0)
        result1 = 0
        ######################################################################################
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
        firmware_loader = Bot.FirmwareLoader(db_connection,igle_table,1, Order, photodata)
        while True:
            result1 = firmware_loader.loader()
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


        ###################################################################################################
        # 13. Робот <- Забери плату с ложе 1.
        print("13 Робот <- Забери плату с ложе 1.")
        logging.info(f"[НАЧАЛО] Робот <- Забери плату с ложе 1.")
        self.change_value('Rob_Action', 231)
        logging.debug("Отправлена команда 'Rob_Action', 231")

        while True:
            result1 = self.read_value("sub_Rob_Action")

            if result1 != 231:
                print(f"Ждем ответ от робота, что плату забрал получено от робота = {result1}")
                logging.info(f"Ждем ответ от робота, что плату забрал получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции взять плату с ложа")
                logging.info(f"От робота получен код 404 на на операции взять плату с ложа")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        logging.info(f"[Завершение] Робот <- Забери плату с ложе 1.")
        print("Стол 1ложе свободен")
        result1 = 0
        #######################################################################################################
        # input("нажми ентер")


        #########################################################################################################
        # 14 Робот <- Уложи плату в тару
        print("# 14 Робот <- Уложи плату в тару.")
        logging.info(f"[НАЧАЛО] Робот <- Уложи плату в тару.")
        self.change_value('Rob_Action', 241)
        logging.debug("Отправлена команда 'Rob_Action', 241")

        while True:
            result1 = self.read_value("sub_Rob_Action")

            if result1 != 241:
                print(f"Ждем ответ от робота, что плату уложил получено от робота = {result1}")
                logging.info(f"Ждем ответ от робота, что плату уложил получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции уложить плату")
                logging.info(f"От робота получен код 404 на на операции уложить плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        logging.info(f"[Завершение]  Робот <- Уложи плату в тару.")
        result1 = 0
        ##########################################################################################################
        # input("нажми ентер")


        ##########################################################################################################
        # 15 Робот <- Забери плату из тары
        print("15 Робот <- забрать плату из тары")
        logging.info(f"[НАЧАЛО] Робот <- забрать плату из тары")
        self.change_value('Rob_Action', 210)
        logging.debug("Отправлена команда 'Rob_Action', 210")

        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 210:
                print(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
                logging.info(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции забрать из тары плату")
                logging.info(f"От робота получен код 404 на на операции забрать из тары плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        logging.info(f"[Завершение]  Робот <- забрать плату из тары")
        result1=0
        ###############################################################################################################
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


        ################################################################################################################
        # 17 Робот <- Уложи плату в ложемент тетситрования 1
        print("17 Робот <- Уложи плату в ложемент тетситрования 1")
        logging.info(f"[НАЧАЛО] Робот <- Уложи плату в ложемент тетситрования 1")
        self.change_value('Rob_Action', 221)
        logging.debug("Отправлена команда 'Rob_Action', 221")
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 221:
                print(f"Ждем ответ от робота, что плату уложили = {result1}")
                logging.info(f"Ждем ответ от робота, что плату уложили = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции уложить плату")
                logging.info(f"От робота получен код 404 на на операции уложить плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        logging.info(f"[Завершение] Робот <- Уложи плату в ложемент тетситрования 1")
        result1=0
        ######################################################################################################################
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
        # photodata = "Z45564564645"
        firmware_loader = Bot.FirmwareLoader(db_connection,igle_table,1, Order, photodata)
        while True:
            result1 = firmware_loader.loader()
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



        ###################################################################################################
        # 23. Робот <- Забери плату с ложе 2.
        print("23 Робот <- Забери плату с ложе 2.")
        logging.info(f"[НАЧАЛО] Робот <- Забери плату с ложе 2.")
        self.change_value('Rob_Action', 232)
        logging.debug("Отправлена команда 'Rob_Action', 232")

        while True:
            result1 = self.read_value("sub_Rob_Action")

            if result1 != 232:
                print(f"Ждем ответ от робота, что плату забрал получено от робота = {result1}")
                logging.info(f"Ждем ответ от робота, что плату забрал получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции взять плату с ложа")
                logging.info(f"От робота получен код 404 на на операции взять плату с ложа")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        logging.info(f"[Завершение] Робот <- Забери плату с ложе 2.")
        result1 = 0
        #######################################################################################################
        # input("нажми ентер")


        #########################################################################################################
        # 24 Робот <- Уложи плату в тару
        print("24 Робот <- Уложи плату в тару.")
        logging.info(f"[НАЧАЛО] Робот <- Уложи плату в тару.")
        self.change_value('Rob_Action', 241)
        logging.debug("Отправлена команда 'Rob_Action', 241")

        while True:
            result1 = self.read_value("sub_Rob_Action")

            if result1 != 241:
                print(f"Ждем ответ от робота, что плату уложил получено от робота = {result1}")
                logging.info(f"Ждем ответ от робота, что плату уложил получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции уложить плату")
                logging.info(f"От робота получен код 404 на на операции уложить плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        logging.info(f"[Завершение]  Робот <- Уложи плату в тару.")
        result1 = 0
        ##########################################################################################################
        # input("нажми ентер")


        ##########################################################################################################
        # 25 Робот <- Забери плату из тары
        print("25 Робот <- забрать плату из тары")
        logging.info(f"[НАЧАЛО] Робот <- забрать плату из тары")
        self.change_value('Rob_Action', 210)
        logging.debug("Отправлена команда 'Rob_Action', 210")

        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 210:
                print(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
                logging.info(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции забрать из тары плату")
                logging.info(f"От робота получен код 404 на на операции забрать из тары плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        logging.info(f"[Завершение]  Робот <- забрать плату из тары")
        result1=0
        ###############################################################################################################
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



        ###################################################################################
        # 27 Робот <- Уложи плату в ложемент тетситрования
        print("27 Робот <- Уложи плату в ложемент тетситрования 2")
        logging.info(f"[НАЧАЛО] Робот <- Уложи плату в ложемент тетситрования 2")
        self.change_value('Rob_Action', 222)
        logging.debug("Отправлена команда 'Rob_Action', 222")
        while True:
            result1 = self.read_value("sub_Rob_Action")
            logging.debug(f"[Статус] sub_Rob_Action = {result1}")

            if result1 != 222:
                print(f"Ждем ответ от робота, что плату уложили = {result1}")
                logging.info(f"Ждем ответ от робота, что плату уложили = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 404 на на операции уложить плату")
                logging.info(f"От робота получен код 404 на на операции уложить плату")
            else:
                break
            time.sleep(1)
        logging.info(f"[Завершение] Робот <- Уложи плату в ложемент тетситрования 2")
        self.change_value('Rob_Action', 0)
        result1 = 0
        ######################################################################################
        #input("нажми ентер")

        print("****ЦИКЛ MAIN END")

    ############# ****ЦИКЛ MAIN END ******"




    
################################################# STOP TABLE CLASS #####################################################################


    def pause(self):
        time.sleep(2)

    


if __name__ == "__main__":
    modbus_provider = ModbusProvider()
    
    
    

    ################################################# START OPC Communication class l ###################################
    
    table1 = Table("Table 1", dict_Table1)
   
    


    table1.main()
