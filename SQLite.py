"""Связь с базой данных сделана классом"""
import datetime
import sqlite3
import logging
from datetime import datetime
import logging
import time

logger4 = logging.getLogger('LoggerMAIN')
logger4.info('[SQLite] Запущен модуль провайдера')

class DatabaseConnection:
    def __init__(self):
        # logger4.info('[SQLite] Инициализация подключения к БД | db=orders.db')
        # Initialize the connection
        self.conn = sqlite3.connect('orders.db')
        self.cursor = self.conn.cursor()
        # logger4.info('[SQLite] Подключение к БД успешно создано')
        
        # Set up basic logging configuration
        logging.basicConfig(
            filename='RTK.log',
            level=logging.INFO,
            format='%(asctime)s - SQLite - %(levelname)s - %(message)s'
        )
        # logging.info("Database connection initialized.")

    def db_connect(self):
        """ Connect to the database and create tables """
        logger4.info('[SQLite] db_connect вызван | создание/проверка таблиц')
        try:
            self.cursor.execute(''' 
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    time_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    order_number TEXT NOT NULL UNIQUE,
                    module TEXT NOT NULL
                );
            ''')
            logging.info("Orders table checked/created.")

            self.cursor.execute(''' 
                CREATE TABLE IF NOT EXISTS order_details (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_number TEXT NOT NULL,
                    serial_number TEXT NOT NULL,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    date_sent TIMESTAMP,
                    status INTEGER,
                    desk_id INTEGER,
                    firmware_link TEXT NOT NULL,
                    test_result TEXT,
                    report_path  TEXT,
                    log_path    TEXT,
                    error_description TEXT,      
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
                );
            ''')

            self.conn.commit()            
            logger4.info('[SQLite] Таблицы orders/order_details проверены или созданы')
        except Exception as e:
            logger4.exception('[SQLite] Ошибка db_connect при создании таблиц')
            raise

    
    def camera_photo(self, QRresult, serial_id):
        """Добавление данных по штрих коду с камеры в базу"""
        logger4.info(f'[SQLite] camera_photo вызван | serial_id={serial_id}')

        try:
            # Update the record
            self.cursor.execute('''
                UPDATE order_details 
                SET data_matrix = ? 
                WHERE serial_number_8 = ?
            ''', (QRresult, serial_id))

            # Check if any row was updated
            if self.cursor.rowcount == 0:
                print(f"Error: No record found with Serial = {serial_id}")
                logger4.warning(f'[SQLite] camera_photo запись не найдена | serial_id={serial_id}')
                return 404
            else:
                # Commit changes if the update was successful
                self.conn.commit()
                logger4.info(f'[SQLite] camera_photo обновлено | serial_id={serial_id}')
                print(f"Successfully updated record with Serial = {serial_id}")
                return 200
        except Exception:
            logger4.exception(f'[SQLite] Ошибка camera_photo | serial_id={serial_id}')
            return 500

    
    def setOrder(self, order_number, Module, Nomeclature, Value, Version_Loader, QRresult, serial_number_8):
        """ Запрос заказов всех """
        logger4.info(f'[SQLite] setOrder вызван | order_number={order_number}, module={Module}, serial={serial_number_8}')
        try:
            current_time = datetime.now()
            # Update the record
            self.cursor.execute('''
                INSERT INTO order_details (
                    time_added,
                    order_number, 
                    module, 
                    nomenclature, 
                    value, 
                    version_loader, 
                    data_matrix, 
                    serial_number_8
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                current_time,
                order_number, 
                Module, 
                Nomeclature, 
                Value, 
                Version_Loader, 
                QRresult, 
                serial_number_8
            ))

            # Check if any row was updated
            if self.cursor.rowcount == 0:
                print(f"Error: No record found with Serial = {serial_number_8}")
            else:
                # Commit changes if the update was successful
                self.conn.commit()
                print(f"Successfully updated record with Serial = {serial_number_8}")
                logger4.info(f'[SQLite] setOrder запись добавлена | order_number={order_number}, serial={serial_number_8}')
                return True
        except Exception:
            logger4.exception(f'[SQLite] Ошибка setOrder | order_number={order_number}, serial={serial_number_8}')
            return False

    def setBoard(self,
            date_added,
            order_id,
            stand_id,
            serial_number_8,
            data_matrix,
            ERPMatrix,
            fw_type,
            fw_path,
            date_sent,
            stand_status,
            logStend,
            hard_stopToStand):
        logger4.info(f'[SQLite] setBoard вызван | order_id={order_id}, stand_id={stand_id}, serial={serial_number_8}')

        try:
            self.cursor.execute('''
                INSERT INTO order_details (
                    date_added,
                    order_id, 
                    stand_id, 
                    serial_number_8, 
                    data_matrix, 
                    ERPMatrix, 
                    fw_type, 
                    fw_path,
                    date_sent,
                    stand_status,
                    logStend,
                    hard_stopToStand
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                date_added,
                order_id,
                stand_id,
                serial_number_8,
                data_matrix,
                ERPMatrix,
                fw_type,
                fw_path,
                date_sent,
                stand_status,
                logStend,
                hard_stopToStand
            ))

            self.conn.commit()
            logger4.info(f'[SQLite] setBoard запись добавлена | order_id={order_id}, serial={serial_number_8}')
            return True

        except Exception as e:
            logger4.exception(f'[SQLite] Ошибка setBoard | order_id={order_id}, serial={serial_number_8}')
            print(f'[SQLite] Ошибка setBoard | order_id={order_id}, serial={serial_number_8}')
            return False
    
    
    # Этот метод удалить он не используется используется метод ниже
    def setTable(self, order_number, stand_id):
        """Поиск заказа и обновление одной записи в order_details."""
        logger4.info(f'[SQLite] setTable вызван | order_number={order_number}, stand_id={stand_id}')
        print(f"Метод setTable вызван с order_number = {order_number}")

        try:
            # Получаем ID заказа
            self.cursor.execute('''
                SELECT id
                FROM orders
                WHERE order_number = ?
                ORDER BY id DESC
                LIMIT 1
            ''', (order_number,))
            row = self.cursor.fetchone()

            if not row:
                logger4.warning(f'[SQLite] setTable заказ не найден | order_number={order_number}')
                print(f'[SQLite] setTable заказ не найден | order_number={order_number}')
                return None

            order_id = row[0]
            logger4.info(f'[SQLite] setTable заказ найден | order_id={order_id}, order_number={order_number}')
            print(f'[SQLite] setTable заказ найден | order_id={order_id}, order_number={order_number}')

            # Ищем свободную строку в order_details
            self.cursor.execute('''
                SELECT id
                FROM order_details
                WHERE order_id = ? AND (stand_id IS NULL OR stand_id = 0)
                ORDER BY id ASC
                LIMIT 1
            ''', (order_id,))
            row = self.cursor.fetchone()

            if not row:
                logger4.warning(f'[SQLite] setTable Нет свободных записей в order_details для order_id = {order_id}')
                print(f'[SQLite] setTable Нет свободных записей в order_details для order_id = {order_id}')
                return None

            serial_id = row[0]
            logging.info("Найдена свободная запись в order_details: id = %s", serial_id)
            print(f"Найдена свободная запись в order_details: id = {serial_id}")

        
            self.conn.execute('BEGIN IMMEDIATE')  # Начинаем транзакцию с блокировкой
            self.cursor.execute('''
                UPDATE order_details
                SET stand_id = ?
                WHERE id = ?
            ''', (stand_id, serial_id,))

            if self.cursor.rowcount > 0:
                self.conn.commit()
                logger4.info(f'[SQLite] setTable Заблокирована и обновлена запись order_details.id={serial_id}, stand_id={stand_id}')
                print(f'[SQLite] setTable Заблокирована и обновлена запись order_details.id={serial_id}, stand_id={stand_id}')
                return serial_id
            else:
                self.conn.rollback()
                logger4.warning(f'[SQLite] setTable Метод блокировки записей из order_details не смог заблокировать не одну из строк для order_details.id={serial_id}')
                print(f'[SQLite] setTable Метод блокировки записей из order_details не смог заблокировать не одну из строк для order_details.id={serial_id}')
                return None

        except Exception as e:
            self.conn.rollback()
            print(f'[SQLite] Ошибка setTable Ошибка при обновлении записи в order_details для записи ={order_number}, stand_id={stand_id} ошибка {e}')
            logger4.exception(f'[SQLite] Ошибка setTable Ошибка при обновлении записи в order_details для записи ={order_number}, stand_id={stand_id} ошибка {e}')
            return None
        
    
    def setTableByPhoto(self, order_number, stand_id, photodata):
        dm = photodata.strip()
        if dm.endswith("B"):
            dm = dm[:-1]

        logger4.info(
            f'[SQLite] setTableByPhoto вызван | '
            f'order_number={order_number}, stand_id={stand_id}, '
            f'photodata={photodata}, dm={dm}'
        )

        try:
            self.conn.execute('BEGIN IMMEDIATE')

            self.cursor.execute('''
                SELECT id
                FROM orders
                WHERE order_number = ?
                ORDER BY id DESC
                LIMIT 1
            ''', (order_number,))
            row = self.cursor.fetchone()

            if not row:
                self.conn.rollback()
                return None

            order_id = row[0]

            self.cursor.execute('''
                SELECT id, stand_id, status
                FROM order_details
                WHERE order_id = ?
                AND (
                    serial_number = ?
                    OR data_matrix = ?
                )
                AND (
                    status LIKE 'reserved_%'
                    OR status LIKE 'placed_%'
                    OR status = 'reserved'
                    OR status = 'sent'
                )
                LIMIT 1
            ''', (order_id, dm, dm))

            row = self.cursor.fetchone()

            if not row:
                self.conn.rollback()
                logger4.warning(
                    f'[SQLite] Плата {dm} не найдена среди reserved/placed/sent | order_id={order_id}'
                )
                return None

            serial_id, current_stand_id, current_status = row

            self.conn.commit()

            logger4.info(
                f'[SQLite] Плата найдена для прошивки | '
                f'id={serial_id}, stand_id={current_stand_id}, status={current_status}'
            )

            return serial_id

        except Exception as e:
            self.conn.rollback()
            logger4.exception(
                f'[SQLite] Ошибка setTableByPhoto | '
                f'order_number={order_number}, stand_id={stand_id}, photodata={photodata}, error={e}'
            )
            return None
    
    def mark_firmware_sent(self, record_id):
        try:
            self.cursor.execute("""
                UPDATE order_details
                SET
                    status = 'sent',
                    started_at = datetime('now', '+5 hours')
                WHERE id = ?
                AND (
                    status LIKE 'reserved_%'
                    OR status LIKE 'placed_%'
                    OR status = 'reserved'
                )
            """, (record_id,))

            if self.cursor.rowcount == 0:
                self.conn.rollback()
                logger4.warning(
                    f"[SQLite] mark_firmware_sent: запись не обновлена | id={record_id}"
                )
                return False

            self.conn.commit()
            logger4.info(f"[SQLite] mark_firmware_sent: запись переведена в sent | id={record_id}")
            return True

        except Exception as e:
            self.conn.rollback()
            logger4.exception(f"[SQLite] mark_firmware_sent: ошибка | id={record_id}, error={e}")
            return False
        
    
    def wait_firmware_result(self, record_id, timeout=300, poll_sec=2):
        """
        Ждет результат прошивки в БД.

        Сервер РТК должен записать:
            status = 'done' или 'failed'
            test_result = 1 или 404

        Если timeout — метод сам переводит запись в failed
        и возвращает resultTest с test_result=404.
        """

        import time

        start_time = time.time()

        while True:
            try:
                self.cursor.execute('''
                    SELECT
                        id,
                        stand_id,
                        serial_number_8,
                        data_matrix,
                        test_result,
                        log_path,
                        report_path,
                        error_description,
                        status,
                        finished_at
                    FROM order_details
                    WHERE id = ?
                    AND status IN ('done', 'failed')
                ''', (record_id,))

                row = self.cursor.fetchone()

                if row:
                    result = {
                        "id": row[0],
                        "stand_id": row[1],
                        "serial_number_8": row[2],
                        "data_matrix": row[3],
                        "test_result": row[4],
                        "log_path": row[5],
                        "report_path": row[6],
                        "error_description": row[7],
                        "status": row[8],
                        "finished_at": row[9],
                    }

                    logger4.info(
                        f"[SQLite] wait_firmware_result: результат получен | "
                        f"id={record_id}, status={result['status']}, "
                        f"test_result={result['test_result']}"
                    )

                    return result

                if time.time() - start_time > timeout:
                    error_text = "Timeout waiting firmware result"

                    self.cursor.execute('''
                        UPDATE order_details
                        SET
                            status = 'failed',
                            finished_at = datetime('now', '+5 hours'),
                            test_result = 404,
                            error_description = ?
                        WHERE id = ?
                        AND status = 'sent'
                    ''', (error_text, record_id))

                    if self.cursor.rowcount == 0:
                        logger4.warning(
                            f"[SQLite] wait_firmware_result: timeout, но запись не переведена в failed | "
                            f"id={record_id}. Возможно статус уже изменился."
                        )
                    else:
                        logger4.error(
                            f"[SQLite] wait_firmware_result: timeout, запись переведена в failed | "
                            f"id={record_id}, test_result=404"
                        )

                    self.conn.commit()

                    return {
                        "id": record_id,
                        "stand_id": None,
                        "serial_number_8": None,
                        "data_matrix": None,
                        "test_result": 404,
                        "log_path": None,
                        "report_path": None,
                        "error_description": error_text,
                        "status": "failed",
                        "finished_at": None,
                    }

                logger4.info(
                    f"[SQLite] wait_firmware_result: ждем результат | "
                    f"id={record_id}"
                )

                time.sleep(poll_sec)

            except Exception as e:
                self.conn.rollback()

                logger4.exception(
                    f"[SQLite] wait_firmware_result: ошибка | "
                    f"id={record_id}, error={e}"
                )

                return {
                    "id": record_id,
                    "stand_id": None,
                    "serial_number_8": None,
                    "data_matrix": None,
                    "test_result": 404,
                    "log_path": None,
                    "report_path": None,
                    "error_description": str(e),
                    "status": "failed",
                    "finished_at": None,
                }
    
    def ConnectPhotoSerial(self, record_id, photodata, loadresult, user= "-"):
        logger4.debug(
            f'[SQLite] Вызов ConnectPhotoSerial(record_id={record_id}, '
            f'photodata={photodata}, loadresult={loadresult}, user={user})'
        )

        try:
            update_query = """
            UPDATE order_details
            SET test_result = ?,
                data_matrix = ?,
                user = ?
            WHERE id = ?
            """

            self.cursor.execute(update_query, (loadresult, photodata, user, record_id))
            self.conn.commit()

            if self.cursor.rowcount == 0:
                logger4.warning(
                    f"[SQLite] ConnectPhotoSerial Не найдено записи id={record_id}"
                )
                return 404

            logger4.info(
                f"[SQLite] ConnectPhotoSerial обновлено | "
                f"id={record_id}, data_matrix={photodata}, user={user}"
            )
            return 200

        except Exception as e:
            logger4.error(
                f"[SQLite] ConnectPhotoSerial ошибка обновления записи {record_id}: {e}",
                exc_info=True
            )
            return 404


    def set_user(self, record_id, user):
        """Метод используется прошивальщиком для проставлени я пользователя при неуспешной прошивке"""
        logger4.debug(
            f"[SQLite] set_user вызван | record_id={record_id}, user={user}"
        )

        try:
            self.cursor.execute(
                """
                UPDATE order_details
                SET user = ?
                WHERE id = ?
                """,
                (user, record_id)
            )

            self.conn.commit()

            if self.cursor.rowcount == 0:
                logger4.warning(
                    f"[SQLite] set_user: запись не найдена | id={record_id}"
                )
                return False

            logger4.info(
                f"[SQLite] set_user: пользователь записан | "
                f"id={record_id}, user={user}"
            )
            return True

        except Exception as e:
            self.conn.rollback()
            logger4.exception(
                f"[SQLite] set_user ошибка | "
                f"id={record_id}, user={user}, error={e}"
            )
            return False



    
    
    def getBoard_id(self, order_number):
        """ Запрос заказов всех """
        logger4.info(f'[SQLite] getBoard_id вызван | order_number={order_number}')
        try:
            # Делаем с блокировкой записи
            self.cursor.execute('''
                        SELECT 
                            O.order_number, 
                            D.id, 
                            D.stand_id,
                            D.serial_number_8,
                            D.data_matrix, 
                            D.ERPMatrix, 
                            D.fw_type,
                            D.fw_path,
                            D.date_sent,
                            D.test_result
                        FROM orders AS O
                        JOIN order_details AS D ON O.id = D.order_id
                        WHERE O.order_number = ?
                            AND (D.test_result <> 200 OR D.test_result IS NULL)
                        ORDER BY id DESC
                        LIMIT 1
                        FOR UPDATE SKIP LOCKED
            ''', (order_number,))

            row = self.cursor.fetchone()

            if row:
                record_id = row[1]
                logger4.info(f'[SQLite] getBoard_id запись найдена | order_number={order_number}, record_id={record_id}')
                return row

            logger4.warning(f'[SQLite] getBoard_id запись не найдена | order_number={order_number}')
            return None

        except Exception:
            logger4.exception(f'[SQLite] Ошибка getBoard_id | order_number={order_number}')
            return None
        
        
    def check_order (self, order_number):
        # Делаем с блокировкой записи
        #logger4.info(f'[SQLite] check_order вызван | order_number={order_number}')

        try:
            self.cursor.execute('''
                SELECT id
                FROM orders
                WHERE order_number = ?
            ''', (order_number,))

            row = self.cursor.fetchone()
            result = bool(row)

            #logger4.info(f'[SQLite] check_order результат | order_number={order_number}, exists={result}')
            return result

        except Exception:
            logger4.exception(f'[SQLite] Ошибка check_order | order_number={order_number}')
            return False

    

    def set_BoardTest_Result(self, record_id, stand_id, serial_number_8, data_matrix, test_result, log_path, report_path, error_description, user):
        """ Установка результатов тестирования вызывается от Сервер РТК """
        logger4.info(
            f'[SQLite] set_BoardTest_Result вызван | '
            f'record_id={record_id}, '
            f'stand_id={stand_id}, '
            f'serial_number_8={serial_number_8}, '
            f'data_matrix={data_matrix}, '
            f'user={user}, '
            f'test_result={test_result}'
        )
        print(f"[RTK] Установка результатов тестирования для записи ID: {record_id}")
        
        try:
            # текущее время
            date_sent = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            update_query = """
            UPDATE order_details
            SET stand_id = ?,
                serial_number_8 = ?,
                data_matrix = ?,
                test_result = ?,
                log_path = ?,
                report_path = ?,
                error_description = ?,
                date_sent = ?,
                user = ?
            WHERE id = ?
            """

            logger4.info(
                f'[SQLite] Выполнение UPDATE order_details | '
                f'record_id={record_id}'
            )

            print(
                f"[DB] Выполнение запроса с параметрами: "
                f"({stand_id}, {serial_number_8}, {data_matrix}, "
                f"{test_result}, {log_path}, {report_path}, "
                f"{error_description}, {date_sent}, {user}, {record_id})"
            )

            # Выполнение
            self.cursor.execute(update_query, (
                stand_id,
                serial_number_8,
                data_matrix,
                test_result,
                log_path,
                report_path,
                error_description,
                date_sent,
                user,
                record_id
            ))
            self.conn.commit()

            print("[DB] Данные успешно сохранены:")

            logger4.info(
                f'[SQLite] set_BoardTest_Result успешно завершен | '
                f'record_id={record_id}, '
                f'test_result={test_result}, '
                f'user={user}, '
                f'date_sent={date_sent}'
            )
           
        except Exception as e:
            logger4.exception(
                f'[SQLite] Ошибка set_BoardTest_Result | '
                f'record_id={record_id}, '
                f'error={e}'
            )
            raise

        


        

    def get_order_insert_orders_frm1C(self, dictResult):
        """ Запрос информации по заказам и вставка данных в таблицы Orders и order_details """
        logger4.info('[SQLite] get_order_insert_orders_frm1C вызван')
        
        order_id = dictResult.get('order_id')
        components = dictResult.get('components', {})
        products = dictResult.get('products', {})
        firmware = products.get('firmware', '')
        board_name = products.get('board_name', None)
        batch = products.get('batch', {})
        count = products.get('count', 0)
        version = products.get('version', None)
        marking_templates = products.get('marking_templates', [])

        logger4.info(
            f'[SQLite] get_order_insert_orders_frm1C входные данные | '
            f'order_id={order_id}, '
            f'board_name={board_name}, '
            f'firmware={firmware}, '
            f'count={count}, '
            f'version={version}, '
            f'batch_count={len(batch) if isinstance(batch, list) else "invalid"}, '
            f'components={components}'
        )

        if not isinstance(batch, list) or not batch:
            logger4.warning(
                f'[SQLite] get_order_insert_orders_frm1C некорректный batch | '
                f'order_id={order_id}, batch_type={type(batch)}, batch={batch}'
            )
            return

        try:
            # Шаг 1: Вставка данных заказа в таблицу Orders
            logger4.info(
                f'[SQLite] Вставка заказа в Orders | '
                f'order_id={order_id}, module={board_name}'
            )
            self.cursor.execute('''
                INSERT INTO Orders (time_added, order_number, module, Nomenclature, Value, VersionLoadFile, fw_version, marking_templates)
                VALUES (datetime('now', '+5 hours'), ?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, board_name, components, count, firmware, version, marking_templates))
            self.conn.commit()

            # Получение ID вставленного заказа
            self.cursor.execute('SELECT last_insert_rowid()')
            inserted_order_id = self.cursor.fetchone()[0]
            
            logger4.info(
                f'[SQLite] Заказ успешно вставлен в Orders | '
                f'order_id={order_id}, inserted_order_id={inserted_order_id}'
            )

            logger4.info(
                f'[SQLite] Начало вставки плат в order_details | '
                f'inserted_order_id={inserted_order_id}'
            )

            for item in batch:
                serial = item["number"]
                serial_8 = item["number8"]
                serial_15 = item["number15"]
                self.cursor.execute('''
                    INSERT INTO order_details (order_id, serial_number, serial_number_8, serial_number_15)
                    VALUES (?, ?, ?, ?)
                ''', (inserted_order_id, serial, serial_8, serial_15))
                self.conn.commit()

            logger4.info(
                f'[SQLite] get_order_insert_orders_frm1C успешно завершен | '
                f'order_id={order_id}, '
                f'inserted_order_id={inserted_order_id}'
            )
            print("Заказ и его детали успешно вставлены.")

        except sqlite3.Error as e:
            logger4.exception(
                f'[SQLite] Ошибка SQLite get_order_insert_orders_frm1C | '
                f'order_id={order_id}, error={e}'
            )
            print(f"[SQLite] Ошибка вставки заказа или его данных в базу данных SQLite: {e}")
            self.conn.rollback()

    
    def recievedata(self, id):
        """Запрос данных для прошивки по ID"""
        logger4.info(
            f'[SQLite] recievedata вызван | record_id={id}'
        )
        query = """
            SELECT 
                S.id,
                S.stand_id,
                O.module AS module_type,
                S.data_matrix,
                S.serial_number_8,
                S.serial_number AS serial_number_9,
                S.serial_number_15,
                S.fw_type,
                O.VersionLoadFile AS fw_path,
                O.order_number AS order_name,
                O.fw_version
            FROM order_details AS S
            JOIN Orders AS O ON O.id = S.order_id
            WHERE S.id = ?
        """


        try:
            cur = self.conn.cursor()
            logger4.info(
                f'[SQLite] Выполнение SELECT recievedata | record_id={id}'
            )
            logging.debug("Выполняется SQL-запрос получения данных для ID: %s", id)
            cur.execute(query, (id,))
            result = cur.fetchone()

            if result is None:
                logger4.warning(
                    f'[SQLite] recievedata данные не найдены  по ID record_id={id}'
                )
                return None

            (order_id, stand_id, module_type, data_matrix, serial_number_8, serial_number_9, serial_number_15,
            fw_type, fw_path, order_name, fw_version) = result

            logger4.info(
                f'[SQLite] Данные успешно получены recievedata запись найдена | '
                f'record_id={id}, '
                f'order_id={order_id}, '
                f'stand_id={stand_id}, '
                f'module_type={module_type}, '
                f'order_name={order_name}, '
                f'fw_version={fw_version}'
            )


            return {
                'id': order_id,
                'stand_id': stand_id,
                'module_type': module_type,
                'data_matrix': data_matrix,
                'serial_number_8': serial_number_8,
                'serial_number_9': serial_number_9,
                'serial_number_15': serial_number_15,               
                'fw_type': fw_type,
                'fw_path': fw_path,
                'order_name': order_name,
                'fw_version': fw_version
            }

        except sqlite3.Error as e:
            logger4.exception(
                f'[SQLite] SQLite ошибка recievedata | '
                f'record_id={id}, error={e}'
            )
            return None
        
    # Получение данных из базы для интерфейса ОПС
    def getDatafromOOPC(self, order_number):
        try:
            self.cursor.execute('''
                SELECT 
                    O.ID
                FROM orders AS O
                WHERE O.order_number = ?
                ORDER BY O.order_number DESC
            ''', (order_number,))

            row = self.cursor.fetchone()
            if row:
                order_id = row[0]
                # logging.info(f"OPC Данные по заказу '{order_number}' получены успешно.")
            else:
                logger4.warning(
                    f'[SQLite] Заказ для OPC интерфейса не найден | '
                    f'order_number={order_number}'
                )
                return None
        except Exception as e:
            logger4.exception(
                f'[SQLite] Ошибка поиска заказа getDatafromOOPC | '
                f'order_number={order_number}, error={e}'
            )
            return None

        try:
            self.cursor.execute('''
                SELECT 
                    O.order_number,
                    O.module,
                    O.fw_version, 

                    COUNT(*) FILTER (
                        WHERE D.test_result IS NULL
                    ) AS Lastcount,

                    COUNT(D.id) AS CommonCount,

                    COUNT(*) FILTER (
                        WHERE D.test_result = 1
                    ) AS Sucesscount,

                    COUNT(*) FILTER (
                        WHERE D.test_result IS NOT NULL
                        AND D.test_result <> 1
                    ) AS NonSucesscount

                FROM orders AS O
                JOIN order_details AS D ON O.id = D.order_id
                WHERE D.order_id = ?
                GROUP BY O.order_number, O.module, O.fw_version
                ORDER BY O.order_number DESC
            ''', (order_id,))

            row = self.cursor.fetchone()

            if row:
                order_number = row[0]
                module = row[1]
                fw_version = row[2]
                last_count = row[3]
                common_count = row[4]
                success_count = row[5]
                nonsuccess_count = row[6]

                # logging.info(f"OPC Данные по заказу '{order_number}' получены успешно.")
                return order_number, module, fw_version, last_count, common_count, success_count, nonsuccess_count
            else:
                logger4.warning(
                    f'[SQLite] Статистика заказа не найдена не могу прокинуть данные на OPC ипнтерфейс | '
                    f'order_id={order_id}'
                )
                return None

        except Exception as e:
            logger4.exception(
                f'[SQLite] Ошибка получения статистики getDatafromOOPC | '
                f'order_id={order_id}, error={e}'
            )
            return None
        
    
        
    # Функция роверки платы в 1с
    def setCheckboardResult(self, record_id: int, check_result: bool):
        """
        Устанавливает результат проверки платы (Checkboard)
        для конкретной записи order_details.

        record_id   — id записи в order_details
        check_result — True / False
        """

        value = 1 if check_result else 0

        try:
            self.cursor.execute(
                '''
                UPDATE order_details
                SET Checkboard = ?
                WHERE id = ?
                ''',
                (value, record_id)
            )

            self.conn.commit()

            # logging.info(
            #     f"OPC Checkboard обновлён: record_id={record_id}, Checkboard={value}"
            # )

            return True

        except Exception as e:
            self.conn.rollback()
            logging.error(
                f"OPC Ошибка обновления Checkboard для record_id={record_id}: {e}",
                exc_info=True
            )
            return False
        
        
        
        
    def close_connection(self):
        """ Close the connection to the database """
        logging.info("Closing database connection.")
        self.conn.close()
        logging.info("Database connection closed.")


# Функция отправки логов в таблицу базы данных
def insert_log(description: str, user: str, status: int = 0):
    try:
        conn = sqlite3.connect("orders.db")
        cursor = conn.cursor()

        # создаём таблицу, если её нет
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT,
                data TEXT,
                status INTEGER,
                user TEXT
            )
        """)

        # текущая дата/время
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # вставка записи
        cursor.execute(
            "INSERT INTO Logs (description, data, status, user) VALUES (?, ?, ?, ?)",
            (description, data, status, user)
        )

        conn.commit()
    except sqlite3.Error as e:
        print("Ошибка при работе с БД:", e)
    finally:
        if conn:
            conn.close()


# Функция которая дает завершение заказа в опс
def end_order_toOPC(order_number):
        """
        True  = в заказе ещё есть непрошитые платы
        False = заказ завершён, непрошитых плат нет
        None  = ошибка / заказ не найден
        """
        try:
            conn = sqlite3.connect("orders.db")
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    O.ID
                FROM orders AS O
                WHERE O.order_number = ?
                ORDER BY O.order_number DESC
            ''', (order_number,))

            row = cursor.fetchone()
            if row:
                order_id = row[0]
                # logging.info(f"OPC Данные по заказу '{order_number}' получены успешно.")
            else:
                logger4.warning(
                    f'[SQLite] Заказ для OPC интерфейса не найден | '
                    f'order_number={order_number}'
                )
                return None
        except Exception as e:
            logger4.exception(
                f'[SQLite] Ошибка поиска заказа getDatafromOOPC | '
                f'order_number={order_number}, error={e}'
            )
            return None

        try:
            cursor.execute('''
                SELECT id
            FROM order_details
            WHERE order_id = ? 
            AND test_result IS NULL
            ''', (order_id,))

            row = cursor.fetchone()

            if row:
                order_id = row[0]
                # logging.info(f"OPC Данные по заказу '{order_number}' получены успешно.")
                return False
            else:
                logger4.warning(
                    f'[SQLite] Не могу получить состояние заказа для функциии окончания заказа опс '
                    f'order_id={order_id}'
                )
                return True

        except Exception as e:
            logger4.exception(
                f'[SQLite] Ошибка получения статистики end_order_toOPC | '
                f'order_id={order_id}, error={e}'
            )
            return None

def has_new_boards(order_number):
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()

    cur.execute("""
        SELECT O.id
        FROM orders O
        WHERE O.order_number = ?
        LIMIT 1
    """, (order_number,))
    row = cur.fetchone()

    if not row:
        return None

    order_id = row[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM order_details
        WHERE order_id = ?
        AND (
            status IS NULL
            OR status = 'new'
        )
    """, (order_id,))

    count_new = cur.fetchone()[0]
    conn.close()

    return count_new > 0


def reserve_board_for_loge(order_number, dm, stand_id, table_no, loge):
    """
    Найти конкретную плату по DM в заказе и подготовить её
    к новой прошивке независимо от предыдущего результата.
    new       → возьмёт
    done      → возьмёт
    failed    → возьмёт     
    """

    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()

    dm_full = dm.strip()

    dm_norm = dm_full
    if dm_norm.endswith("B"):
        dm_norm = dm_norm[:-1]

    try:
        # плату, которая прямо сейчас уже занята другим столом.  не разрешать reserved_*, placed_*, sent.
        cur.execute("""
            SELECT D.id
                FROM order_details D
                JOIN orders O ON O.id = D.order_id
                WHERE O.order_number = ?
                AND (
                        D.serial_number = ?
                        OR D.serial_number_8 = ?
                        OR D.data_matrix = ?
                    )
                AND (
                        D.status IS NULL
                        OR D.status IN ('new', 'done', 'failed')
                    )
                LIMIT 1
        """, (
            order_number,
            dm_norm,
            dm_norm,
            dm_norm
        ))

        row = cur.fetchone()

        if not row:
            conn.close()
            logger4.warning(
                f"[SQLite] Плата {dm_norm} не найдена "
                f"в заказе {order_number}"
            )
            return None

        record_id = row[0]

        # Начинаем НОВЫЙ цикл прошивки этой же платы.
        cur.execute("""
            UPDATE order_details
            SET
                status = ?,
                stand_id = ?,
                data_matrix = ?,

                test_result = NULL,
                log_path = NULL,
                report_path = NULL,
                error_description = NULL,

                started_at = NULL,
                finished_at = NULL,
                date_sent = NULL

            WHERE id = ?
        """, (
            f"reserved_t{table_no}_l{loge}",
            stand_id,
            dm_full,
            record_id
        ))

        conn.commit()

        logger4.info(
            f"[SQLite] Плата {dm_norm} подготовлена "
            f"к повторной прошивке | "
            f"id={record_id}, "
            f"status=reserved_t{table_no}_l{loge}"
        )

        return record_id

    except Exception as e:
        conn.rollback()
        logger4.exception(
            f"[SQLite] Ошибка резервирования платы "
            f"{dm_norm}: {e}"
        )
        return None

    finally:
        conn.close()


def mark_board_placed(record_id, table_no, loge):
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()

    cur.execute("""
        UPDATE order_details
        SET status = ?
        WHERE id = ?
    """, (f"placed_t{table_no}_l{loge}", record_id))

    conn.commit()
    return cur.rowcount > 0


def release_reserved_board(record_id):
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()

    cur.execute("""
        UPDATE order_details
        SET status = 'new',
            stand_id = NULL
        WHERE id = ?
          AND status LIKE 'reserved_%'
    """, (record_id,))

    conn.commit()
    return cur.rowcount > 0


# Функция отправки логов в таблицу LogRTKto1C это для 1С зпускается и отправялети логи
def insert_log_for1C(description: str, user: str, status: int = 0):
    try:
        conn = sqlite3.connect("orders.db")
        cursor = conn.cursor()

        # создаём таблицу, если её нет
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS LogRTKto1C (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT,
                data TEXT,
                status INTEGER,
                user TEXT
            )
        """)

        # текущая дата/время
        data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # вставка записи
        cursor.execute(
            "INSERT INTO LogRTKto1C (description, data, status, user) VALUES (?, ?, ?, ?)",
            (description, data, status, user)
        )

        conn.commit()
    except sqlite3.Error as e:
        print("Ошибка при работе с БД:", e)
    finally:
        if conn:
            conn.close()

def clear_all_except_finished():
    """
    Сбрасывает промежуточные статусы плат после аварийного останова.

    Не трогаем:
        done
        failed

    Сбрасываем в NULL:
        new
        reserved_*
        placed_*
        sent
        любые другие статусы
    """

    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE order_details
            SET status = NULL
            WHERE status IS NOT NULL
              AND status NOT IN ('done', 'failed')
        """)

        updated_count = cur.rowcount
        conn.commit()

        logger4.info(
            f"[SQLite] clear_all_except_finished: "
            f"сброшено статусов={updated_count}"
        )

        return updated_count

    except Exception as e:
        conn.rollback()

        logger4.exception(
            f"[SQLite] clear_all_except_finished ошибка: {e}"
        )

        return None

    finally:
        conn.close()


# res = has_new_boards('ЗНП-29961.1.1')
# print(res)
# res = record_id = end_order_toOPC(
#     order_number='ЗНП-29961.1.1'
# )

# print(f"Взаказе есть гнепрошитые платы {record_id}")


# db_connection = DatabaseConnection()
# record_id = db_connection.setTableByPhoto(
#     order_number='ЗНП-29961.1.1',
#     stand_id=1,
#     photodata='U00079882'
# )

# print(f"record_id = {record_id}")



"""
# Create an instance of DatabaseConnection
db_connection = DatabaseConnection()
Order = "ЗНП-0005747"
record_id = db_connection.setTable(Order)

"""

"""
# Create an instance of DatabaseConnection
db_connection = DatabaseConnection()
res = db_connection.recievedata(464)
print(res)
"""


"""
# Проверка функции OPC
# Проверка функции OPC
db_connection = DatabaseConnection()
result = db_connection.getDatafromOOPC('ЗНП-29961.1.1')

if result:
    order_number, module, fw_version, last_count, common_count, success_count, nonsuccess_count = result

    print(f"Номер заказа: {order_number}")
    print(f"Модуль: {module}")
    print(f"Версия ПО: {fw_version}")
    print(f"Количество оставшихся: {last_count}")
    print(f"Общее количество записей: {common_count}")
    print(f"Успешно прошитые: {success_count}")
    print(f"Неуспешно прошитые: {nonsuccess_count}")
else:
    print("Данные по заказу не найдены или произошла ошибка.")
"""

# insert_log(f"Для стола получено фото datamatrix платы значение =", 0)


# erp_response = {
#     'order': 'ЗНП-24576.1.1',
#     'board': 'V01240234',
#     'result': False
# }

# record_id = 1  # id записи order_details
#db_connection = DatabaseConnection()
# db_connection.setCheckboardResult(
#     record_id=record_id,
#     check_result=erp_response["result"]
# )
#print(db_connection.getDatafromOOPC("ЗНП-241.1.1"))


# db_connection = DatabaseConnection()
# result = db_connection.getDatafromOOPC('ЗНП-29961.1.1')
# print(result)


# Пример тестовых данных
# record_id = 8013

# stand_id = "STAND_1"
# serial_number_8 = "SN12345678"
# data_matrix = "DM_TEST_123456"
# test_result = 1  # например: 1 = OK, 0 = FAIL
# log_path = "C:/logs/test.log"
# report_path = "C:/reports/report.pdf"
# error_description = ""

# db = DatabaseConnection()

# db.set_BoardTest_Result(
#     record_id=9267,
#     stand_id="TEST_STAND",
#     serial_number_8="TEST9254",
#     data_matrix="DM_TEST_9254",
#     test_result=1,
#     log_path="C:/RTK/logs/test9254.log",
#     report_path="C:/RTK/reports/test9254.pdf",
#     error_description="",
#     user="OPC_USER_TEST"
# )

# print("Тест записи 9267 завершен")



# db = DatabaseConnection()
# db.db_connect()

# result = db.setTableByPhoto(
#     order_number="ЗНП-29973.1.1",
#     stand_id="ТЕСТ",
#     photodata="U00075196B"
# )

# print(f"RESULT = {result}")

# db = DatabaseConnection()
# db.db_connect()
# insert_log_for1C(
# description="Test",
# user="V.Ovchinnikov"
# )


# res= clear_all_except_finished()
# print(res)