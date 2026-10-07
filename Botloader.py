import time
from datetime import datetime

# Пользовательский класс БД
import SQLite as SQL

# Поьзовательский класс провайдера Иглостола
import ProviderIgleTable as Igable

# Отправка данных в 1С. Сделал этот модуль здесь
import SentLog1C



import logging

logger4 = logging.getLogger('LoggerMAIN')





################################################# Botloader class ###################################
class FirmwareLoader:
    def __init__(self,db_connection,igle_table,stand_id, Order, photodata, loge):
        logger4.info(
            f"[Botloader] Инициализация | stand_id={stand_id}, Order={Order}, photodata={photodata}, loge={loge}"
        )

        try:
            # Создаем экземпляр подключения к базе данных
            self.db_connection = db_connection
            logger4.info("[Botloader] Соединение с базой данных установлено")
        except Exception as e:
            logger4.exception(f"[Botloader] Ошибка при создании подключения с базой данных: {e}")
            raise

        try:
            # Создаем экземпляр провайдера
            self.igle_table = igle_table
            logger4.info("[Botloader] Соединение с провайдером Иглостола установлено")
        except Exception as e:
            logger4.exception(f"[Botloader] Ошибка при создании подключения с провайдером: {e}")
            raise
        self.stand_id = stand_id
        self.Order = Order
        self.photodata = photodata
        self.loge = loge

    def loader(self, photodata, loge, user):
        logger4.info(f"[Botloader] Вызов функции loader Команда на прошивку праметры  photodata = {photodata}, loge={loge}")
        print(f"[Botloader] Вызов функции loader Команда на прошивку праметры  photodata = {photodata}, loge={loge}")
        print(f"[Botloader] Значение user на входе: '{user}' (тип: {type(user)})")
        
        # Блок начала работы с БД: получаем свободный id для заказа
        try:
            self.db_connection.db_connect()
            logger4.info("[Botloader] Подключение к БД")
            # Берем свовобоный заказ
            logger4.info(
                f"[Botloader] Поиск свободного заказа | Order={self.Order}, stand_id={self.stand_id}"
            )
            
            record_id = self.db_connection.setTableByPhoto(
                self.Order,
                self.stand_id,
                photodata
            )
            logger4.info(f"[Botloader] БД вернула свободный заказ record_id={record_id}")
            print(f"[Botloader] БД вернула свободный заказ record_id={record_id}")
            if record_id is None:
                logger4.warning(f"[Botloader] Свободная запись не найдена")
                print(f"[Botloader] Свободная запись не найдена")
                return 404, None
            #  получаем для него данные из бд для прошивки
            data = self.db_connection.recievedata(record_id)
            # Если данные были получены, напечатаем их
            if data:
                 logger4.warning(f"[Botloader] Получены и успешно извлечены данные по прошивке для записи {record_id} data = {data}")
                 print(f"ID: {data['id']}")
                 print(f"Stand ID: {data['stand_id']}")
                 print(f"Module Type: {data['module_type']}")
                 print(f"Data Matrix: {data['data_matrix']}")
                 print(f"Serial Number_8: {data['serial_number_8']}")
                 print(f"Serial Number_9: {data['serial_number_9']}")
                 print(f"Serial Number_15: {data['serial_number_15']}")
                 print(f"Firmware Type: {data['fw_type']}")
                 print(f"Firmware Path: {data['fw_path']}")
                 print(f"Firmware Version: {data['fw_version']}")
                 print(f"Order_number: {data['order_name']}")
            else:
                 logger4.error(f"[Botloader] Не удалось получить данные для прошивки | record_id={record_id}")
                 print(f"[Botloader] Не удалось получить данные для прошивки | record_id={record_id}")
        except Exception as e:
            logger4.exception(f"[Botloader] Ошибка при работе с базой данных: {e}")
            print(f"[Botloader] Ошибка при работе с базой данных: {e}")
            return
        
        # Блок прошивки
        time.sleep(2)
        try:
            logger4.info(
                f"[Botloader] Отправляем команду на Иглостол | record_id={record_id}, photodata={photodata}, loge={loge}"
            )
            # print (data, photodata, loge)
            self.igle_table.control_igle_table(data, photodata, loge)
            logger4.info(f"[Botloader] Команда на Иглостол успешно отправлена | record_id={record_id}")
            # После отправки команды поставить sent в бд
            if not self.db_connection.mark_firmware_sent(record_id):
                logger4.error(f"[Botloader] Не удалось перевести запись в sent | record_id={record_id}")
                return 404, None
        except Exception as e:
            logger4.exception(f"[Botloader] Ошибка при отправке команды на прошивку Иглостолу: {e}")
            print(f"[Botloader] Ошибка при отправке команды на прошивку Иглостолу: {e}")
            return

        # Ждем результат прошивки из БД
        logger4.info(
            f"[Botloader] Ожидание результата прошивки из БД | "
            f"record_id={record_id}"
        )
        resultTest = self.db_connection.wait_firmware_result(record_id)

        if not isinstance(resultTest, dict):
            logger4.error(
                f"[Botloader] Некорректный результат wait_firmware_result | "
                f"record_id={record_id}"
            )
            self.cleanup()
            return 500, False

        loadresult = resultTest.get("test_result")

        logger4.info(
            f"[Botloader] Получен результат прошивки из БД | "
            f"record_id={record_id}, test_result={loadresult}, "
            f"status={resultTest.get('status')}"
        )

        # Отправляем лог в 1С
        try:
            self.send_log_to_1c_safe(data, resultTest, user)

            logger4.info(
                f"[Botloader] Лог в 1С отправлен/обработан | "
                f"record_id={record_id}"
            )

        except Exception as e:
            logger4.exception(
                f"[Botloader] Ошибка отправки лога в 1С | "
                f"record_id={record_id}, error={e}"
            )
        
        # Обработка данных и запись результатов в БД
        # При успешной прошивке извлекаем данные
        if resultTest.get("test_result") in (1, True, "1"):



            # Извлекаем необходимые данные
            data_matrix = resultTest.get("data_matrix")
            log_path = resultTest.get("log_path")
            report_path = resultTest.get("report_path")
            serial_number_8 = resultTest.get("serial_number_8")
            stand_id = resultTest.get("stand_id")
            test_result = resultTest.get("test_result")
            error_description = resultTest.get("error_description")

            try:
                logger4.info(
                    f"[Botloader] Запись успешного результата в БД | "
                    f"record_id={record_id}, stand_id={stand_id}, serial_8={serial_number_8}, "
                    f"test_result={test_result}, log_path={log_path}, report_path={report_path}"
                )
                # Записываем результаты прошивки в БД
                # self.db_connection.set_BoardTest_Result(record_id, stand_id, serial_number_8, data_matrix, test_result, log_path, report_path, error_description, user)
                # logger4.info(f"[Botloader] Результаты прошивки записаны в БД | record_id={record_id}")
                # print(f"[Botloader] Результаты прошивки успешно записаны в БД для заказа {record_id}")
                
                # Привязываем Data matrix к серийнику
                logger4.info(f"[Botloader] Привязка DataMatrix к серийному номеру | record_id={record_id}, photodata={photodata}")
                self.db_connection.ConnectPhotoSerial(record_id, photodata, loadresult, user)
                print(f"------------------------------{user}")
                print("[Botloader]Привязали Data matrix к серийному номеру")

                
                # Очищаем переменные
                self.cleanup()
                logger4.info(f"[Botloader] Цикл прошивки завершен успешно | record_id={record_id}")
                # Если с ошибкой прошивка возращаем статус error_description
                return 200, test_result
            except Exception as e:
                logger4.exception(f"[Botloader] Ошибка при записи успешного результата в БД: {e}")
                print(f"[Botloader] Ошибка при записи успешного результата в БД: {e}")
                # Очищаем переменные
                self.cleanup()
                return 404, test_result
        else:
            print("[Botloader] Ошибка: не удалось получить данные, запись в БД не выполнена.")
            logger4.error(
                f"[Botloader] Ошибка прошивки | "
                f"record_id={record_id}, resultTest={resultTest}"
            )

            # Если не удалось, сообщаем роботу переместить в брак
            try:
                log_path = resultTest.get("log_path")
                report_path = resultTest.get("report_path")
                serial_number_8 = resultTest.get("serial_number_8")
                error_description = resultTest.get("error_description") or "Ошибка прошивки"
                data_matrix = resultTest.get("data_matrix") or photodata
                stand_id = resultTest.get("stand_id")

                logger4.info(
                    f"[Botloader] Запись брака в БД | "
                    f"record_id={record_id}, stand_id={stand_id}, "
                    f"serial_8={serial_number_8}, data_matrix={data_matrix}, "
                    f"log_path={log_path}, report_path={report_path}, "
                    f"error_description={error_description}"
                )

                # self.db_connection.set_BoardTest_Result(
                #     record_id,
                #     stand_id,
                #     serial_number_8,
                #     data_matrix,
                #     "404",
                #     log_path,
                #     report_path,
                #     error_description,
                #     user
                # )
                # logger4.info(f"[Botloader] Брак записан в БД | record_id={record_id}")
                # print(f"[Botloader] Брак записан в БД | record_id={record_id}")
            except Exception as e:
                logger4.exception(f"[Botloader] Не удалось записать брак в БД: {e}")
                print("[Botloader] Не удалось записать брак в БД")

            self.db_connection.set_user(record_id, user)

            self.cleanup()
            logger4.info(f"[Botloader] Цикл прошивки завершен с ошибкой | record_id={record_id}")
            return 500, False
        

    def send_log_to_1c_safe(self, data, resultTest, user):
        """Отправка лога в 1С. Логи разные взависмоисти от успеха не успеха прошивки. Фомируеются 2 словаря"""
        try:
            logger4.info("[Botloader][1С] Начало отправки лога в 1С send_log_to_1c_safe")

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            test_result = resultTest.get("test_result", None)
            test_result_raw = resultTest.get("test_result", None)
            is_success = str(test_result_raw).strip() == "1" or test_result_raw is True

            serial_number = resultTest.get("data_matrix", "")
            log_path = resultTest.get("log_path") or ""

            logger4.info(
                f"[Botloader][1С] Подготовка payload для 1С | "
                f"test_result={test_result_raw}, is_success={is_success}, "
                f"serial_number={serial_number}, "
                f"order={data.get('order_name')}, fw_version={data.get('fw_version')}"
            )


            board_info = {
                "board": {
                    "number": serial_number,
                    "tray_number": "123455"
                },
                "operator": user,
                "log_path": log_path,
                "timestamps": {
                    "dm_code_time": now,
                    "firmware_finished_time": now,
                    "board_output_time": now
                }
            }

            common_payload = {
                "rtk_id": "RTK_R050_BoardsIO_1",
                "order": data.get('order_name'),
                "version": data.get('fw_version'),
                "message_type": "firmware_log",
            }

            if is_success:
                payload = {
                    **common_payload,
                    "good": [
                        {
                            **board_info,
                            "error": 0
                        }
                    ],
                    "bad": []
                }
                logger4.info(f"[Botloader][1С] Отправка успешного firmware_log в 1С | payload={payload}")
                response = SentLog1C.send_success_log(payload)
            else:
                payload = {
                    **common_payload,
                    "good": [],
                    "bad": [
                        {
                            **board_info,
                            "error": 2
                        }
                    ]
                }
                logger4.info(f"[Botloader][1С] Отправка не успешного firmware_log в 1С | payload={payload}")
                response = SentLog1C.send_unsuccess_log(payload)

            logger4.info(f"[Botloader][1С] Ответ сервера 1С: {response} Лог успешно отправлен в 1С")
            print(f"[Botloader][1С] Ответ сервера 1С: {response}")
            return True

        except Exception as e:
            logger4.exception(f"[Botloader][1С] 1С недоступна или ошибка отправки лога: {e}")
            print(f"[Botloader][1С] 1С недоступна или ошибка отправки лога: {e}")
            return False
        

        

    def cleanup(self):
        # Очищаем перменные после выполнения
        # self.db_connection = None
        # self.igle_table = None
        print("Переменные очищены.")
        logger4.info("[Botloader] cleanup: переменные очищены")


if __name__ == "__main__":

    """

    ################################################# IgleTable Communication Class ###################################
    
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
    
    try:
            # Create an instance of DatabaseConnection
            db_connection = SQL.DatabaseConnection()
    except Exception as e:
            logging.error(f"Error Create an instance of DatabaseConnection: {e}")
    ################################################# STOP SQL Communication class ###################################

    Order = "ЗНП-2160.1.1"
    photodata = "45654465"
    stand_id = "table_3"
    loge = 1
    firmware_loader = FirmwareLoader(db_connection,igle_table3,stand_id, Order, photodata, loge)
    res = firmware_loader.loader(photodata, loge)
    print (f"***************{res}")


    """
"""
Order = "ЗНП-9087.2.1"
photodata = "45654465"
firmware_loader = FirmwareLoader(db_connection,igle_table,1, Order, photodata)
res = firmware_loader.loader()
print (f"***************{res}")
"""


# #Тест отправки данных на прошивку
# igle_table3 = Igable.IgleTable(
#         urlIgleTabeControl=f"http://192.168.1.100:5000/nails_table/start_test_board_with_rtk",
#         urlStatusFromIgleTabe=f"http://192.168.1.100:5003/get_test_results/1")

# db_connection = SQL.DatabaseConnection()
# Order = "ЗНП-29973.1.1"
# photodata = "U00075415B"
# stand_id = "table_3"
# loge = 2
# firmware_loader = FirmwareLoader(db_connection,igle_table3,stand_id, Order, photodata, loge)
# res = firmware_loader.loader(photodata, loge)
# print (f"***************{res}")

# ####################################################
# # Тестирование лога 1С
# firmware_loader = FirmwareLoader(
#         db_connection=None,
#         igle_table=None,
#         stand_id="table_3",
#         Order="ЗНП-29973.1.1",
#         photodata="U00075415B",
#         loge=1
#     )

# data = {
#         "order_name": "ЗНП-37025.1.1",
#         "fw_version": "1.0.36.0"
#     }

# resultTest = {
#         "status_code": "OK",
#         "serial_number_8": "U00075415B",
#         "error_description": 1
#     }

# res = firmware_loader.send_log_to_1c_safe(data, resultTest)
# print("Результат вызова:", res)

# now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

# payload = {
#     "rtk_id": "RTK_R050_BoardsIO_1",
#     "order": "ЗНП-29973.1.1",
#     "version": "R050_DI_16_012_000_AAA",
#     "message_type": "firmware_log",

#     "good": [
#         {
#             "board": {
#                 "number": "U00075415B",
#                 "tray_number": "123455"
#             },

#             "operator": "I.Perekalskii",

#             "timestamps": {
#                 "dm_code_time": now,
#                 "firmware_finished_time": now,
#                 "board_output_time": now
#             },

#             "error": 0
#         }
#     ],

#     "bad": []
# }

# response = SentLog1C.send_success_log(payload)

# print(response)