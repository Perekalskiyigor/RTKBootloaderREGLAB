import requests
import json
import logging
import configparser
import datetime
from requests.auth import HTTPBasicAuth
import logging
logger1c = logging.getLogger("API1CLog")
logger1c.setLevel(logging.INFO)

# Чтобы при повторном import не добавлялись обработчики повторно
if not logger1c.handlers:
    file_handler = logging.FileHandler(
        "API1C.log",
        encoding="utf-8"
    )

    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s"
    )

    file_handler.setFormatter(formatter)
    logger1c.addHandler(file_handler)

# Не передаём сообщения в общий root logger
logger1c.propagate = False

# Загрузка конфигурации
config = configparser.ConfigParser()
config.read('config.ini')

url_send_data = config['server']['url']
username = config['server']['username']
password = config['server']['password']
url_token = config['server']['url_token']

import requests
import json
import logging
import configparser
import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

config = configparser.ConfigParser()
config.read('config.ini', encoding='utf-8')

url_send_data = config['server']['url']
username = config['server']['username']
password = config['server']['password']
url_token = config['server']['url_token']


def get_token():
    logger1c.info("Receive new token")
    data = {
        'grant_type': 'CLIENT_CREDENTIALS'
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    try:
        response = requests.post(
            url_token,
            data=data,
            headers=headers,
            auth=(username, password),
            verify=False,
            timeout=10
        )

        print("TOKEN STATUS:", response.status_code)
        print("TOKEN RESPONSE:", response.text)

        if response.status_code == 200:
            token_data = response.json()
            token = token_data.get('id_token') or token_data.get('access_token')
            logging.info("API1C - Receive new token")
            return token
        else:
            logging.error(
                f"API1C - Token request failed with status {response.status_code}: {response.text}"
            )
            logger1c.error(
                "Token request failed | HTTP=%s | response=%s",
                response.status_code,
                response.text
            )
            return None

    except Exception as e:
        logger1c.exception(
        "Error receiving token | error=%s",
        str(e)
        )
        return None


# ====================== УСПЕШНАЯ ПРОШИВКА ======================
def send_success_log(board_dict):
    """
    Формируем JSON вида:

    {
      "rtk_id": "...",
      "order": "...",
      "version": "...",
      "good": [{
        "board": {
          "number": "Z00390116",
          "tray_number": "123455"
        },
        "operator": "A.Eliseeva",
        "error": 0,
        "dm_code_time": "...",
        "firmware_finished_time": "...",
        "board_output_time": "..."
      }],
      "bad": []
    }
    """

    token = get_token()
    if not token:
        logging.error("Не удалось получить токен")
        print("Не удалось получить токен")
        return None

    now = datetime.datetime.now().isoformat()

    good_item = board_dict["good"][0]

    # Берём таймстемпы из словаря, если есть, иначе ставим now
    ts = good_item.get("timestamps", {})
    dm_code_time = ts.get("dm_code_time", now)
    firmware_finished_time = ts.get("firmware_finished_time", now)
    board_output_time = ts.get("board_output_time", now)

    payload = {
        "rtk_id": "RTK_R050_BoardsIO_1",
        "order": board_dict["order"],
        "version": board_dict["version"],
        "message_type": board_dict.get("message_type"),  # если нужно — раскомментировать
        "good": [
            {
                "board": {
                    "number": good_item["board"]["number"],
                    # tray_number можем брать, если он есть
                    "tray_number": good_item["board"].get("tray_number")
                },
                "operator": good_item["operator"],
                "error": good_item.get("error", 0),
                "timestamps":ts,
                "full_log_path": "",
                "dm_code_time": dm_code_time,
                "firmware_finished_time": firmware_finished_time,
                "board_output_time": board_output_time
            }
        ],
        "bad": []
    }

    print("== JSON Request Body (SUCCESS) ==")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    logger1c.info(
    "SEND BOARD_GOOD | payload=%s",
    json.dumps(payload, ensure_ascii=False)
    )

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }

    try:
        response = requests.post(
            url_send_data,
            json=payload,
            headers=headers,
            verify=False,
            timeout=10
        )

        logger1c.info(
                    "RESPONSE BOARD_GOOD | HTTP=%s | response=%s",
                    response.status_code,
                    response.text
                )
        
        response.raise_for_status()

        
        print(f"\nУспешно отправлено: {response.status_code}")

        try:
            return response.json()
        except ValueError:
            logging.warning("Response is not JSON or empty")
            return response.text

    except requests.exceptions.RequestException as e:
        logger1c.exception(
        "REQUEST ERROR | error=%s",
        str(e)
        )
        print(f"\nОшибка отправки: {e}")
        return None


# ====================== НЕУСПЕШНАЯ ПРОШИВКА ======================
def send_unsuccess_log(board_dict):
    """
    Формируем JSON вида:

    {
      "rtk_id": "...",
      "order": "...",
      "version": "...",
      "good": [],
      "bad": [{
        "board": {"number": "Z01137499"},
        "error": 6,
        "operator": "A.Eliseeva",
        "dm_code_time": "...",
        "firmware_finished_time": "...",
        "board_output_time": "..."
      }]
    }
    """

    now = datetime.datetime.now().isoformat()

    bad_item = board_dict["bad"][0]

    ts = bad_item.get("timestamps", {})
    dm_code_time = ts.get("dm_code_time", now)
    firmware_finished_time = ts.get("firmware_finished_time", now)
    board_output_time = ts.get("board_output_time", now)

    payload = {
        "rtk_id": "RTK_R050_BoardsIO_1",
        "order": board_dict["order"],
        "version": board_dict["version"],
        "message_type": board_dict.get("message_type"),
        "good": [],
        "bad": [
            {
                "board": {
                    "number": bad_item["board"]["number"]
                },
                "operator": bad_item["operator"],
                "error": bad_item["error"],
                "timestamps":ts,
                "full_log_path": bad_item.get("full_log_path", ""),
                "dm_code_time": dm_code_time,
                "firmware_finished_time": firmware_finished_time,
                "board_output_time": board_output_time
            }
        ]
    }

    print("== JSON Request Body (UNSUCCESS) ==")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    logger1c.info(
    "SEND BOARD_BAD | payload=%s",
    json.dumps(payload, ensure_ascii=False)
    )

    # Лучше тоже через токен, чтобы было одинаково,
    # но если сервер ждёт BasicAuth — можно вернуть как у тебя было.
    token = get_token()
    if not token:
        logging.error("Не удалось получить токен")
        print("Не удалось получить токен")
        return None

    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    }

    try:
        response = requests.post(
            url_send_data,
            json=payload,
            headers=headers,
            verify=False,
            timeout=10
        )

        logger1c.info(
                    "RESPONSE BOARD_BAD | HTTP=%s | response=%s",
                    response.status_code,
                    response.text
                )
        
        response.raise_for_status()

        
        print(f"\nУспешно отправлено: {response.status_code}")

        try:
            return response.json()
        except ValueError:
            logging.warning("Response is not JSON or empty")
            return response.text

    except requests.exceptions.RequestException as e:
        logger1c.exception(
        "REQUEST ERROR | error=%s",
        str(e)
        )
        print(f"\nОшибка отправки: {e}")
        return None


board_dict_success = {
    "rtk_id": "RTK_R050_BoardsIO_1",
    "order": "ЗНП-37025.1.1",
    "version": "",
    "message_type": "firmware_log",
    "good": [
        {
            "board": {
                "number": "Z01745814T",
                "tray_number": "123455"
            },
            "operator": "A.Eliseeva",
            "error": 0,
            "timestamps": {
                "dm_code_time": "2026-04-20 10:51:35.798732",
                "firmware_finished_time": "2026-04-20 10:52:12.725689",
                "board_output_time": "2026-04-20 10:52:15.725689"
            }
        }
    ],
    "bad": []
}

# Вызов
# response = send_success_log(board_dict_success)
# print("Ответ сервера:", response)


board_dict_fail = {
    "rtk_id": "RTK_R050_BoardsIO_1",
    "order": "ЗНП-29961.1.1",
    "version": "R050_DO_16_012_000_ABA",
    "message_type": "firmware_log",
    "good": [],
    "bad": [
        {
            "board": {
                "number": "U00082801B",
                "tray_number": "123455"
            },
            "operator": "rtk_server",
            "error": 2,

            "full_log_path": r"C:\nails_table_v4\hub\nails_table_hub\resources\outputs\reports\nt_cmpp_rtk_2\ЗНП_29961_1_1\log_R050_DO_16_012_000_ABA_U00082801B_N1_1.txt",

            "timestamps": {
                "dm_code_time": "2026-09-24 05:14:24",
                "firmware_finished_time": "2026-09-24 05:15:46",
                "board_output_time": "2026-09-24 05:15:46"
            }
        }
    ]
}

# response = send_unsuccess_log(board_dict_fail)
# print("Ответ сервера:", response)

# Вызов
#response = send_unsuccess_log(board_dict_fail)
#response = send_success_log(board_dict_success)
#print("Ответ сервера:", response)
