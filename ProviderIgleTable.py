"""Класс стола но буду вероятно использовать класс тэйбл там многопоточность"""

import socket
import time
import requests
import json
import logging
import sqlite3
from datetime import datetime

"""
Данный класс реализует интеграцию между базой данных, системой прошивки и испытательным стендом (иглостолом).

1. Метод `control_igle_table`:
   Выполняет выборку данных из заказа, формирует необходимую команду управления, и передаёт её загрузчику для выполнения прошивки устройства. 
   В состав передаваемых параметров входят: тип модуля, серийный номер, путь к прошивке, версия прошивки, а также информация о стенде и посадочном месте.
    
    ПРИМЕР
    "stand_id" : "nt_cmpp_rtk_3",
    "module_type": "R050 DI 16 012-000-AAA",
    "data_matrix": ["Z01177337B"],
    "order_name": "ЗНП-123",
    "serial_number_8": "1",
    "serial_number_9": "2",
    "serial_number_15": "3",
    "lodgment_number": 2,

2. Метод `recentData`:
   Осуществляет опрос состояния иглостола. После завершения тестирования, иглостол отправляет результат на сервер, где данные временно сохраняются.
   Метод `recentData` запрашивает эти данные с REST API, обрабатывает и возвращает информацию, включая: результат тестирования, серийный номер, дата-матрицу, пути к логам и отчётам.

Таким образом, класс обеспечивает полный цикл взаимодействия: от подготовки и передачи задания на прошивку до получения и интерпретации результатов тестирования.
"""


class IgleTable:
    def __init__(self, urlIgleTabeControl, urlStatusFromIgleTabe):
        self.urlIgleTabeControl = urlIgleTabeControl
        self.urlStatusFromIgleTabe = urlStatusFromIgleTabe
        
        # Настройка логирования
        logging.basicConfig(
            filename='RTK.log',
            level=logging.INFO,
            format='%(asctime)s - ProviderIgleTable - %(levelname)s - %(message)s'
        )

       
    # Запрос на прошивку
    def control_igle_table(self,data, photodata, loge):
        """Метод для отправки команд иглостэнду."""
        logging.info("Method control_igle_table called.")
        
        # Проверим, что данные переданы
        if data:
            try:
                # Извлекаем параметры из данных
                # Изменен формат для апи Моржова
                stand_id = str(data.get('stand_id'))
                stand_id = f"nt_cmpp_rtk_{stand_id.split('_')[-1]}"
                
                module_type = data.get('module_type')
                data_matrix = photodata
                Order_number = data.get('order_name')
                # заглушка, т.к с 1с ничего не получаем
                #serial_number_8 = data.get('serial_number_8')
                serial_number_8 = "1"
                serial_number_9 = data.get('serial_number_9')
                # заглушка, т.к с 1с ничего не получаем
                #serial_number_15 = data.get('serial_number_15')
                serial_number_15 = "1"
                fw_type = data.get('fw_type')
                fw_path = data.get('fw_path')
                fw_version = data.get('fw_version')
                
                loge = loge

                print(f"ID: {data['id']}")
                print(f"Stand ID: {data['stand_id']}")
                print(f"Module Type: {data['module_type']}")
                print(f"Data Matrix: {data['data_matrix']}")
                print(f"=====Serial Number: {serial_number_8}")
                print(f"Serial Number_9: {data['serial_number_9']}")
                print(f"=====Serial Number_15: {serial_number_15}")
                print(f"Firmware Type: {data['fw_type']}")
                print(f"Firmware Path: {data['fw_path']}")
                print(f"Firmware Version: {data['fw_version']}")
                print(f"Order_number: {data['order_name']}")
                print(f"loge: {loge}")

                # Логируем полученные параметры
                logging.debug (f"Input parameters: stand_id={stand_id}, module_type={module_type}, "
                            f"data_matrix={data_matrix}, serial_number_8={serial_number_8}, "
                            f"fw_type={fw_type}, fw_path={fw_path}, fw_version={fw_version}, "
                            f"Order_number = {Order_number}, serial_number_9 = {serial_number_9}, "
                            f"serial_number_15 = {serial_number_15}")
            except KeyError as e:
                # Логируем ошибку, если какой-то из параметров отсутствует
                logging.error(f"Missing parameter: {e}")
        else:
            logging.error("No data received for firmware.")
        
        # Формируем payload с использованием данных, полученных из data
        payload = json.dumps({
            "stand_id": stand_id,
            "module_type": module_type,
            "data_matrix": [data_matrix],
            "order_name": Order_number,
            "serial_number_8": serial_number_8,
            "serial_number_9": serial_number_9,
            "serial_number_15": serial_number_15,
            "lodgment_number": loge,

            "firmwares": [
                {
                    "fw_type": "MCU",
                    "fw_path": fw_path,
                    "fw_version": fw_version
                }
            ]
        })

        # Напечатаем JSON, который будет отправлен
        print("Payload JSON that will be sent:")
        print(payload)

        
        headers = {
            'Content-Type': 'application/json'
        }

        # Отправляем POST запрос с сформированным JSON
        try:
            logging.info("Отправка запроса на %s", self.urlIgleTabeControl)
            response = requests.post(self.urlIgleTabeControl, headers=headers, data=payload)
            logging.info("Код ответа: %d", response.status_code)
            logging.info("Тело ответа: %s", response.text)
            return response.text
        except requests.RequestException as e:
            logging.error("Ошибка запроса: %s", str(e))
            return None
        

        
    # Перепарвка данных от иглостола в сервер ртк
    def recentData(self):
        url = self.urlStatusFromIgleTabe
        try:
            response = requests.get(url)
            if response.status_code == 200:
                json_data = response.json()
                data = json_data.get("data", {})
                result = json_data.get("result")
                test_result = data.get("test_result")
                datamatrix = data.get("data_matrix")

                return {
                    "data_matrix": datamatrix[0] if isinstance(datamatrix, list) and datamatrix else None,
                    "log_path": data.get("log_file_path"),
                    "report_path": data.get("report_file_path"),
                    "serial_number_8": data.get("serial_number_8") or data.get("serial"),
                    "stand_id": data.get("stand_id"),
                    "test_result": test_result, # По нему смотрю успех не успех
                    "error_description": data.get("error_description"),  # если сервер это поле отдает
                    "status_code": result
                }
            else:
                return {"status_code": 404}
        except Exception as e:
            logging.error(f"Error in recentData(): {str(e)}")
            return {"status_code": 404}
        

    


# igle_table1 = IgleTable(
#     urlIgleTabeControl="http://172.21.10.182:5000/nails_table/start_test_board_with_rtk",
#     urlStatusFromIgleTabe="http://172.21.10.182:5003/get_test_results/1"
# )

# result1 = igle_table1.recentData()
# print("Received from RTK server (stand 1):")
# print(result1)
"""
time.sleep(1.5)  # ⏱️ Пауза 1.5 секунды

igle_table2 = IgleTable(
    urlIgleTabeControl="http://172.21.10.182:5000/nails_table/start_test_board_with_rtk",
    urlStatusFromIgleTabe="http://172.21.10.182:5003/get_test_results/2"
)

result2 = igle_table2.recentData()
print("Received from RTK server (stand 2):")
print(result2)

time.sleep(1.5)  # ⏱️ Пауза 1.5 секунды

igle_table3 = IgleTable(
    urlIgleTabeControl="http://172.21.10.182:5000/nails_table/start_test_board_with_rtk",
    urlStatusFromIgleTabe="http://172.21.10.182:5003/get_test_results/3"
)

result3 = igle_table3.recentData()
print("Received from RTK server (stand 3):")
print(result3)

"""



# s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
# try:
#     # Подключаемся к "левому" адресу — не важно, доступен он или нет
#     s.connect(("8.8.8.8", 80))
#     ip = s.getsockname()[0]
# finally:
#     s.close()
# print(f"Локальный IP-адрес: {ip}")
   

# igle_table = IgleTable(
#         urlIgleTabeControl=f"http://192.168.1.100:5000/nails_table/start_test_board_with_rtk",
#         urlStatusFromIgleTabe=f"http://192.168.1.100:5003/get_test_results",

#         module_type="R050 DI 16 011-000-AAA",
#         stand_id="nt_kto_rtk_3",
#         serial_number_8="1",
#         data_matrix=["11"],
#         firmwares = [
#             {
#             "fw_type": "MCU",
#             "fw_path": "C:\\nails_table_bridge\\plc050_di16012-full.hex",
#             "fw_version": "1.0.36.0"
#             }
#         ]

        
#     )
# resultTest = igle_table.recentData()
# print(f"Локальныйvvvv IP-адрес: {igle_table.urlStatusFromIgleTabe}")

# # Выводим все данные
# for key, value in resultTest.items():
#     print(f"{key}: {value}")
# # Проверяем, что ответ успешный


# igle_table3 = IgleTable(
#         urlIgleTabeControl=f"http://192.168.1.100:5000/nails_table/start_test_board_with_rtk",
#         urlStatusFromIgleTabe=f"http://192.168.1.100:5003/get_test_results/3")

# data4 = {
#     "id" : "8137",
#     "stand_id": "nt_cmpp_rtk_3",
#     "module_type": "R050 DI 16 012-000-AAA",
#     "data_matrix": ["111"],
#     "order_name": "\u0417\u041d\u041f-37025.1.1",
#     "serial_number_8": "1",
#     "serial_number_9": "Z01745817",
#     "serial_number_15": "1",
#     "lodgment_number": 2,
#     "firmwares":[
#         {
#             "fw_type": "MCU",
#             "fw_path": "C:\\\\nails_table_bridge\\\\plc050_di16012-full.hex",
#             "fw_version": "1.0.36.0"
#         }
#     ]
#     }

# igle_table3.control_igle_table(data4, "Z01177337B", 1)