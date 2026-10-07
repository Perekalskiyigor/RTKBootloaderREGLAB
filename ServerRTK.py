# python -m PyInstaller --onefile ServerRTK.py

from flask import Flask, request, jsonify
import logging
import socket

import threading
import os
import time
import sqlite3

# Глобальная переменная для хранения последних данных
latest_data = None
# Хранилище данных для каждого стенда
latest_data_by_stand = {}

# Настройка логирования
logging.basicConfig(
    filename='RTKServer.log',
    level=logging.INFO,
    format='%(asctime)s - ServerRTK - %(levelname)s - %(message)s'
)

logging.info(f"[RTK SERVER] DB path={os.path.abspath('orders.db')}")

def save_firmware_result(data):
    """
    Запись результата прошивки в SQLite.
    Поиск записи по data_matrix.
    """

    print("\n================ SAVE_FIRMWARE_RESULT START ================")
    print(f"[RTK SERVER] Входящие данные: {data}")

    try:
        conn = sqlite3.connect('orders.db')
        cursor = conn.cursor()

        print("[RTK SERVER] Подключение к БД успешно")

        stand_id = data.get("stand_id")
        serial_number_8 = data.get("serial_number_8")

        data_matrix = data.get("data_matrix")

        print(f"[RTK SERVER] stand_id={stand_id}")
        print(f"[RTK SERVER] serial_number_8={serial_number_8}")
        print(f"[RTK SERVER] raw data_matrix={data_matrix}")

        # Иглостол может прислать список
        if isinstance(data_matrix, list):
            print("[RTK SERVER] data_matrix пришел как LIST")
            data_matrix = data_matrix[0] if data_matrix else None
        
        if isinstance(data_matrix, str):
            data_matrix = data_matrix.strip()
        
        # Сохраняем оба варианта DataMatrix
        data_matrix_full = data_matrix
        
        data_matrix_norm = data_matrix
        if isinstance(data_matrix_norm, str) and data_matrix_norm.endswith("B"):
            data_matrix_norm = data_matrix_norm[:-1]
        
        print(f"[RTK SERVER] full data_matrix={data_matrix_full}")
        print(f"[RTK SERVER] normalized data_matrix={data_matrix_norm}")

        log_path = data.get("log_file_path")
        report_path = data.get("report_file_path")
        error_description = data.get("error_description")

        test_result = data.get("test_result")

        print(f"[RTK SERVER] log_path={log_path}")
        print(f"[RTK SERVER] report_path={report_path}")
        print(f"[RTK SERVER] error_description={error_description}")
        print(f"[RTK SERVER] test_result={test_result}")

        if not data_matrix:
            print("[RTK SERVER][ERROR] data_matrix отсутствует")
            logging.error("[RTK SERVER] data_matrix отсутствует")
            return False

        # Определяем статус
        if test_result in (1, True, "1"):
            status = "done"
            db_result = 1
        else:
            status = "failed"
            db_result = 404

        print(f"[RTK SERVER] status={status}")
        print(f"[RTK SERVER] db_result={db_result}")

        print("[RTK SERVER] Выполняем UPDATE...")

        cursor.execute('''
            UPDATE order_details
            SET
                stand_id = ?,
                serial_number_8 = ?,
                test_result = ?,
                log_path = ?,
                report_path = ?,
                error_description = ?,
                status = ?,
                finished_at = CURRENT_TIMESTAMP,
                result_source = 'rtk_server'
            WHERE (data_matrix = ? OR data_matrix = ?)
              AND status = 'sent'
        ''', (
            stand_id,
            serial_number_8,
            db_result,
            log_path,
            report_path,
            error_description,
            status,
            data_matrix_full,
            data_matrix_norm
        ))

        print(f"[RTK SERVER] cursor.rowcount={cursor.rowcount}")

        conn.commit()

        print("[RTK SERVER] COMMIT выполнен")

        if cursor.rowcount == 0:
            print(
                f"[RTK SERVER][WARNING] Ничего не обновлено | "
                f"full={data_matrix_full}, norm={data_matrix_norm}"
            )

            # Дополнительная диагностика
            cursor.execute('''
                SELECT id, data_matrix, status
                FROM order_details
                WHERE data_matrix = ? OR data_matrix = ?
            ''', (data_matrix_full, data_matrix_norm))

            row = cursor.fetchone()

            if row:
                print(f"[RTK SERVER] Запись найдена но status != sent | row={row}")
            else:
                print(
                    f"[RTK SERVER] Вообще не найден data_matrix | "
                    f"full={data_matrix_full}, norm={data_matrix_norm}"
                )
        else:
            print(
                f"[RTK SERVER][OK] Результат записан | "
                f"data_matrix={data_matrix}, status={status}, test_result={db_result}"
            )

            logging.info(
                f"[RTK SERVER] Результат записан в БД | "
                f"data_matrix={data_matrix}, status={status}, test_result={db_result}"
            )

        conn.close()

        print("[RTK SERVER] Соединение с БД закрыто")
        print("================ SAVE_FIRMWARE_RESULT END =================\n")

        return True

    except Exception as e:
        print(f"[RTK SERVER][EXCEPTION] {e}")

        logging.exception(
            f"[RTK SERVER] Ошибка записи результата в БД | "
            f"error={e}"
        )

        return False
    

app = Flask(__name__)

@app.route('/set_test_results', methods=['POST'])
def set_test_results():
    try:
        data = request.get_json()
        print(data)

        if not data:
            logging.warning("No JSON data received.")
            return jsonify({"error description": "No data received", "result": "FAIL"}), 400

        logging.info(f"Received data: {data}")

        stand_id = data.get("stand_id")
        if not stand_id:
            logging.warning("Missing 'stand_id' in the request.")
            return jsonify({"error description": "Missing stand_id", "result": "FAIL"}), 400

        latest_data_by_stand[stand_id] = data
        save_firmware_result(data)
        logging.info(f"Data stored for stand_id: {stand_id}")

        return jsonify({"error description": "All very Good", "result": "OK"})

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return jsonify({"error description": "FAIL", "result": str(e)}), 500


@app.route('/get_test_results/1', methods=['GET'])
def get_test_results1():
    try:
        stand_id = "nt_cmpp_rtk_1"  # Изменено с table_1
        data = latest_data_by_stand.get(stand_id)

        if not data:
            logging.info(f"No data available for stand_id: {stand_id}")
            return jsonify({"error description": "No data available", "result": "FAIL"}), 404

        del latest_data_by_stand[stand_id]
        logging.info(f"Data for {stand_id} retrieved and cleared.")
        return jsonify({"result": "OK", "data": data})

    except Exception as e:
        logging.error(f"Error retrieving data for stand 1: {str(e)}")
        return jsonify({"error description": "FAIL", "result": str(e)}), 500
    
@app.route('/get_test_results/2', methods=['GET'])
def get_test_results2():
    try:
        stand_id = "nt_cmpp_rtk_2"  # Изменено с table_2
        data = latest_data_by_stand.get(stand_id)

        if not data:
            logging.info(f"No data available for stand_id: {stand_id}")
            return jsonify({"error description": "No data available", "result": "FAIL"}), 404

        del latest_data_by_stand[stand_id]
        logging.info(f"Data for {stand_id} retrieved and cleared.")
        return jsonify({"result": "OK", "data": data})

    except Exception as e:
        logging.error(f"Error retrieving data for stand 2: {str(e)}")
        return jsonify({"error description": "FAIL", "result": str(e)}), 500
    
@app.route('/get_test_results/3', methods=['GET'])
def get_test_results3():
    try:
        stand_id = "nt_cmpp_rtk_3"  # Изменено с table_3
        data = latest_data_by_stand.get(stand_id)

        if not data:
            logging.info(f"No data available for stand_id: {stand_id}")
            return jsonify({"error description": "No data available", "result": "FAIL"}), 404

        del latest_data_by_stand[stand_id]
        logging.info(f"Data for {stand_id} retrieved and cleared.")
        return jsonify({"result": "OK", "data": data})

    except Exception as e:
        logging.error(f"Error retrieving data for stand 3: {str(e)}")
        return jsonify({"error description": "FAIL", "result": str(e)}), 500

if __name__ == '__main__':
    # app.run(host="172.21.10.182", port=5003)
    # проверка на то что у этого экземпляра сервера существует свой родитель если нет его надо убить иначе данные будут попадать в него.
    parent_pid = os.getppid()
    def monitor_parent():
        while True:
            # На Windows и Unix: если родительский процесс сменился — завершаемся
            if os.getppid() != parent_pid:
                os._exit(0)
            time.sleep(1)
    threading.Thread(target=monitor_parent, daemon=True).start()
    app.run(host="192.168.1.100", port=5003)
    input()


"""
new          — запись свободна
reserved     — основной скрипт забрал запись
sent         — команда отправлена на иглостол
in_progress  — стол начал прошивку
done         — прошивка успешна
failed       — прошивка неуспешна
timeout      — стол не ответил
"""


"""
@app.route('/set_test_results', methods=['POST'])
def set_test_results():
    global latest_data
    try:
        data = request.get_json()

        if not data:
            logging.warning("No JSON data received.")
            return jsonify({"error description": "No data received", "result": "FAIL"}), 404

        logging.info(f"Received data: {data}")
        latest_data = data

        return jsonify({"error description": "All very Good", "result": "OK"})

    except Exception as e:
        logging.error(f"Error occurred: {str(e)}")
        return jsonify({"error description": "FAIL", "result": str(e)}), 500


@app.route('/get_test_results', methods=['GET'])
def get_test_results():
    global latest_data
    try:
        if latest_data is None:
            logging.info("No data available to retrieve.")
            return jsonify({"error description": "No data available", "result": "FAIL"}), 404

        data_to_return = latest_data
        latest_data = None  # очищаем после получения

        logging.info("Data retrieved and cleared.")
        return jsonify({"result": "OK", "data": data_to_return})

    except Exception as e:
        logging.error(f"Error retrieving data: {str(e)}")
        return jsonify({"error description": "FAIL", "result": str(e)}), 500
    

@app.route('/get_test_results/<int:stand_number>', methods=['GET'])
def get_test_results(stand_number):
    try:
        stand_id = f"RTK_{stand_number}"
        data = latest_data.get(stand_id)

        if not data:
            logging.info(f"No data available for stand_id: {stand_id}")
            return jsonify({"error description": "No data available", "result": "FAIL"}), 404

        # Удаляем после получения
        del latest_data[stand_id]

        logging.info(f"Data for {stand_id} retrieved and cleared.")
        return jsonify({"result": "OK", "data": data})

    except Exception as e:
        logging.error(f"Error retrieving data for stand {stand_number}: {str(e)}")
        return jsonify({"error description": "FAIL", "result": str(e)}), 500


if __name__ == '__main__':
    app.run(host="192.168.1.100", port=5003)  # Можно менять порт/IP при необходимости

"""



 
