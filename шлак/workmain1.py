import time
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading

dict_Table1 = {
    'Reg_move_Table': 0, 
    'sub_Reg_move_Table': 0, 
    'Reg_updown_Botloader': 0, 
    'sub_Reg_updown_Botloader': 0, 
    'Rob_Action': 0,
    'sub_Rob_Action': 0
}


################################################# START MODBUS Communication class with Modbus regul ###################################
class ModbusProvider:
    """Class MODBUS Communication with Modbus regul"""
    def __init__(self):
        self.store = ModbusSlaveContext(
            hr=ModbusSequentialDataBlock(0, [0] * 100)
        )
        self.lock = threading.Lock()

        self.Reg_move_Table = 0              # Move Table
        self.Reg_updown_Botloader = 0        # Move botloader
        self.Rob_Action = 0                  # Action to Robot

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
        self.change_value('Rob_Action', 301)
        while True:
            result1 = self.read_value("sub_Rob_Action")

            if result1 != 301:
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
        self.change_value('Rob_Action', 302)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 302:
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
        print("5 Робот <-  забрать плату из тары")
        self.change_value('Rob_Action', 100)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 100:
                print(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции забрать из тары плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)

        # 6 Делаем фото платы
        print("6 Камера <- сделай фото")
        time.sleep(1)
        

        # 7 Робот <- Уложи плату в ложемент тетситрования
        print("7 Робот <- Уложи плату в ложемент тетситрования 2")
        self.change_value('Rob_Action', 200)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 200:
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
        print("9 Робот <-  забрать плату из тары")
        self.change_value('Rob_Action', 100)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 100:
                print(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции забрать из тары плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)

        # 10 Делаем фото платы
        print("10 Камера <- сделай фото")
        time.sleep(1)
        

        # 11 Робот <- Уложи плату в ложемент тетситрования
        print("11 Робот <- Уложи плату в ложемент тетситрования 1")
        self.change_value('Rob_Action', 200)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 200:
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
        
        
        # 2. Сервер <- Начни шить
        # 3. Сервер -> Ответ по прошивке (плохо, хорошо)
        print("2. Сервер <- Начни шить")
        print("3. Сервер -> Ответ по прошивке (плохо, хорошо)")
        
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

        # 6. Робот <- Забери плату с ложе 2.
        print("6 Робот <- Забери плату с ложе 2.")
        self.change_value('Rob_Action', 300)
        while True:
            result1 = self.read_value("sub_Rob_Action")

            if result1 != 300:
                print(f"Ждем ответ от робота, что плату забрал получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции взять плату с ложа")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        print("Стол 1ложе свободен")
        result1 = 0


        # 7 Робот <- Забери плату из тары
        print("7 Робот <-  забрать плату из тары")
        self.change_value('Rob_Action', 100)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 100:
                print(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции забрать из тары плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1=0

        # 8 Делаем фото платы
        print("8 Камера <- сделай фото")
        time.sleep(1)
        

        # 9 Робот <- Уложи плату в ложемент тетситрования 2
        print("9 Робот <- Уложи плату в ложемент тетситрования 2")
        self.change_value('Rob_Action', 200)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 200:
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
        self.change_value('Rob_Action', 300)
        while True:
            result1 = self.read_value("sub_Rob_Action")

            if result1 != 300:
                print(f"Ждем ответ от робота, что плату забрал получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции взять плату с ложа")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1 = 0


        # 16 Робот <- Забери плату из тары
        print("16 Робот <-  забрать плату из тары")
        self.change_value('Rob_Action', 100)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 100:
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
        time.sleep(1)
        

        # 18 Робот <- Уложи плату в ложемент тетситрования 1
        print("18 Робот <- Уложи плату в ложемент тетситрования 1")
        self.change_value('Rob_Action', 200)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 200:
                print(f"Ждем ответ от робота, что плату уложили = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции уложить плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1=0

        # 19. Регул <- Опусти прошивальщик (плата на ложе2).
        print("19. Регул <- Опусти прошивальщик ложе2..")
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

        # 20. Сервер <- Начни шить
        # 21. Сервер -> Ответ по прошивке (плохо, хорошо)
        print("20. Сервер <- Начни шить")
        print("21. Сервер -> Ответ по прошивке (плохо, хорошо)")

        # 22. Регул <- Подними прошивальщик.
        print("22. Регул <- Подними прошивальщик.")
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

        # 23. Регул <- Сдвинь плату освободив ложе2.
        print("23 Регул <- Сдвинь плату освободив ложе2")
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
        print("Стол 1 ложе свободен")
        
        
        # 24. Робот <- Забери плату с ложе 2.
        print("24 Робот <- Забери плату с ложе 2.")
        self.change_value('Rob_Action', 300)
        while True:
            result1 = self.read_value("sub_Rob_Action")

            if result1 != 300:
                print(f"Ждем ответ от робота, что плату забрал получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции взять плату с ложа")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1 = 0

        # 25 Робот <- Забери плату из тары
        print("25 Робот <-  забрать плату из тары")
        self.change_value('Rob_Action', 100)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 100:
                print(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции забрать из тары плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1=0

        # 26 Делаем фото платы
        print("26 Камера <- сделай фото")
        time.sleep(1)
        

        # 27 Робот <- Уложи плату в ложемент тетситрования 2
        print("27 Робот <- Уложи плату в ложемент тетситрования 2")
        self.change_value('Rob_Action', 200)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 200:
                print(f"Ждем ответ от робота, что плату уложили = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции уложить плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1=0


        # 28. Регул <- Опусти прошивальщик (плата на ложе1).
        print("28 Регул <- Опусти прошивальщик ложе 1")
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

        # 29. Сервер <- Начни шить
        # 30. Сервер -> Ответ по прошивке (плохо, хорошо)
        print("29. Сервер <- Начни шить")
        print("30. Сервер -> Ответ по прошивке (плохо, хорошо)")

        # 31. Регул <- Подними прошивальщик.
        print("31. Регул <- Подними прошивальщик.")
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



        # 32. Регул <- Сдвинь плату освободив ложе 1.
        print("32. Регул <- Сдвинь плату освободив ложе1")
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
        print("Стол 1 ложе свободен")

        # 32. Робот <- Забери плату с ложе 1.
        print("32 Робот <- Забери плату с ложе 1.")
        self.change_value('Rob_Action', 300)
        while True:
            result1 = self.read_value("sub_Rob_Action")

            if result1 != 300:
                print(f"Ждем ответ от робота, что плату забрал получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции взять плату с ложа")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1 = 0


        # 33 Робот <- Забери плату из тары
        print("33 Робот <-  забрать плату из тары")
        self.change_value('Rob_Action', 100)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 100:
                print(f"Ждем ответ от робота, что плату забрал из тары получено от робота = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции забрать из тары плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1=0

        # 34 Делаем фото платы
        print("34 Камера <- сделай фото")
        time.sleep(1)
        

        # 35 Робот <- Уложи плату в ложемент тетситрования 1
        print("35 Робот <- Уложи плату в ложемент тетситрования 1")
        self.change_value('Rob_Action', 200)
        while True:
            result1 = self.read_value("sub_Rob_Action")
            if result1 != 200:
                print(f"Ждем ответ от робота, что плату уложили = {result1}")
            elif result1 == 404:
                print(f"От робота получен код 200 на на операции уложить плату")
            else:
                break
            time.sleep(1)
        self.change_value('Rob_Action', 0)
        result1=0



        # 36. Регул <- Опусти прошивальщик (плата на ложе2).
        print("36 Регул <- Опусти прошивальщик ложе2.")
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

        # 37. Сервер <- Начни шить
        # 38. Сервер -> Ответ по прошивке (плохо, хорошо)
        print("37. Сервер <- Начни шить")
        print("38. Сервер -> Ответ по прошивке (плохо, хорошо)")

        # 39. Регул <- Подними прошивальщик.
        print("39. Регул <- Подними прошивальщик.")
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

        #print("Стол 2ложе свободен")
        print("****ЦИКЛ MAIN END")

    ############# ****ЦИКЛ MAIN END ******"




    
################################################# STOP TABLE CLASS #####################################################################


    def pause(self):
        time.sleep(2)

    


if __name__ == "__main__":
    modbus_provider = ModbusProvider()
    
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