import logging
import time
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading

# Пользовательский класс камеры
# mport CameraClass as CAM
import CameraSocket
 
 # Пользовательский класс БД
import SQLite as SQL

# OPC Класс
import OPCClient as OPC

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
    format='MAIN - %(asctime)s - %(levelname)s - %(message)s'
)

################################################# START CAMERA Communication class ###################################

# Пример использования
# camera_ip = '192.168.1.50'
# camera = CAM.CameraConnection(camera_ip)

################################################# STOP CAMERA Communication class ###################################

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
        input("нажми ентер")
        # 1. Регул <- Опусти прошивальщик ложе 2.
        print("1 Регул <- Опусти прошивальщик ложе 2")
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
        input("нажми ентер")
        
        # 2. Сервер <- Начни шить
        # 3. Сервер -> Ответ по прошивке (плохо, хорошо)
        print("2. Сервер <- Начни шить")
        print("3. Сервер -> Ответ по прошивке (плохо, хорошо)")
        input("нажми ентер")
        # 4. Регул <- Подними прошивальщик.
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

        input("нажми ентер")
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

        input("нажми ентер")
        # 6. Робот <- Забери плату с ложе 2.
        print("6 Робот <- Забери плату с ложе 2.")
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
        print("Стол 1ложе свободен")
        result1 = 0

        input("нажми ентер")
        # 7 Робот <- Уложи плату в тару
        print("# 7 Робот <- Уложи плату в тару.")
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

        input("нажми ентер")
        # 7 Робот <- Забери плату из тары
        print("7 Робот <- забрать плату из тары")
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
        result1=0
        
        input("нажми ентер")
        # 8 Делаем фото платы
        print("8 Камера <- сделай фото")
        a = CameraSocket.photo()
        print (a)
        time.sleep(1)
        a = CameraSocket.photo()
        print (a)
        time.sleep(1)
        a = CameraSocket.photo()
        print (a)
        time.sleep(1)
        
        input("нажми ентер")
        # 9 Робот <- Уложи плату в ложемент тетситрования 2
        print("9 Робот <- Уложи плату в ложемент тетситрования 2")
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

        # 10. Регул <- Опусти прошивальщик (плата на ложе1).
        print("10. Регул <- Опусти прошивальщик (плата на ложе1).")
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

        # 11. Сервер <- Начни шить
        # 12. Сервер -> Ответ по прошивке (плохо, хорошо)
        print("11. Сервер <- Начни шить")
        print("12. Сервер -> Ответ по прошивке (плохо, хорошо)")



        # 13 Регул <- Подними прошивальщик.
        print("13. Регул <- Подними прошивальщик.")
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


        # 14. Регул <- Сдвинь плату освободив ложе1.
        print("14 Регул <- Сдвинь плату освободив ложе1")
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
        print("Стол 1ложе свободен")


        # 15. Робот <- Забери плату с ложе 1.
        print("15 Робот <- Забери плату с ложе 1.")
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
        result1 = 0

        # 15 Робот <- Уложи плату в тару
        print("# 7 Робот <- Уложи плату в тару.")
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

        # 16 Робот <- Забери плату из тары
        print("16 Робот <- забрать плату из тары")
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
        result1=0

        # 17 Делаем фото платы
        print("17 Камера <- сделай фото")
        a = CameraSocket.photo()
        print (a)
        time.sleep(1)
        a = CameraSocket.photo()
        print (a)
        time.sleep(1)
        a = CameraSocket.photo()
        print (a)
        time.sleep(1)
        

        # 18 Робот <- Уложи плату в ложемент тетситрования 1
        print("18 Робот <- Уложи плату в ложемент тетситрования 1")
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
    
    
    ################################################# START OPC Communication class ###################################
    # Example usage
    url = "opc.tcp://172.21.10.39:48010"
    opc_client = OPC.OPCClient(url)

    # Graceful shutdown after some time
    time.sleep(10)  # Let the program run for 10 seconds
    opc_client.stop()  # Signal the threads to stop
    time.sleep(2)  # Wait a little for threads to finish
    opc_client.disconnect()


    ################################################# START OPC Communication class l ###################################
    
    table1 = Table("Table 1", dict_Table1)
         # Создание объекта и выполнение алгоритма
    table1 = Table("Table 1", dict_Table1)
    

    # Выполнение первого цикла
    flag1 = True
    if flag1 == True:
        table1.defence_cycle()
        flag1 = False
    

    
    # Выполнение первого цикла
    flag = True
    if flag == True:
        table1.setup_cycle()
        flag = False

    table1.main()
