import pprint

import requests
import json
import logging
import sqlite3
from datetime import datetime
import SQLite
import configparser
import logging

logger4 = logging.getLogger('LoggerMAIN')

# Загрузка конфигурации
config = configparser.ConfigParser(interpolation=None)
config.read(r"config.ini", encoding="utf-8")

getOrders_url = config['serverOrder']['getOrders_url']
username = config['serverOrder']['password']
fetch_data_url = config['serverOrder']['fetch_data_url']

logger4.info('[Provider1C] Запущен модуль провайдера')

def getOrders():
    headers = {
        'Authorization': 'Basic bWFya19EUEE6MTIzNDU2elo='
    }

    try:
        response = requests.get(getOrders_url, headers=headers, verify=False)
        response.raise_for_status()  # выбросит исключение для кода ответа != 200

        data = response.json()  # преобразуем в словарь

        keys = list(data.keys())  # получаем только ключи

        if keys:
            logger4.info(f"[Provider1C] Найденные ключи: {keys}")
            print(f"[Provider1C] Найденные ключи: {keys}")
            return keys
        else:
            logger4.warning("[Provider1C] Ответ получен, но он пуст.")
            print("[Provider1C] Ответ получен, но он пуст.")


    except requests.exceptions.RequestException as e:
        logger4.error(f"[Provider1C] Ошибка при запросе: {e}")
        print(f"[Provider1C] Ошибка при запросе: {e}")
    except ValueError:
        print("Ошибка разбора JSON. Ответ не является допустимым JSON.")
        logger4.error("[Provider1C] Ошибка разбора JSON")
    except Exception as e:
        print("Произошла неизвестная ошибка:", e)
        logger4.exception(f"[Provider1C] Неизвестная ошибка: {e}")



def fetch_data(order):
    logger4.info(f"[Provider1C] Вызвана fetch_data(order={order})")
      
    
    try:
        order = order[4:]   # срезаем "ЗНП-"
        url = f"{fetch_data_url}{order}"
        logger4.info(f"[Provider1C] ФАКТИЧЕСКИЙ URL на который отправляем запрос: {url}")
        payload = {}
        headers = {
        'Authorization': 'Basic cnRrX2NtcHA6NDU2Nzg5QWE='
        }
        logger4.info(f"[Provider1C] Запрос данных по заказу: {order}")
        response = requests.get(url, headers=headers, verify=True, timeout=15)
        response.raise_for_status()
        #print(response.text)
        data = response.json()
        logger4.info(f"[Provider1C] получаем от 1с, сами не редачим {data}")
        print("\n=== RAW ИЗ 1С ===")
        print(repr(data['products']['firmware']))


        order_id = data.get('order')
        components = data.get('components', {})
        components_str = json.dumps(components, ensure_ascii=False)
        products = data.get('products', {})
        firmware = products.get('firmware', '')
        board_name = products.get('product', None)
        batch = products.get('batch', {})
        count = products.get('count', 0)
        version = products.get('version', None)
        marking_templates = products.get('marking_templates', [])
        marking_templates_str = json.dumps(marking_templates, ensure_ascii=False)

        result = {
            'order_id': order_id,
            'components': components_str,
            'products': {
                'firmware': firmware,
                'board_name': board_name,
                'batch': batch,
                'count': count,
                'version': version,
                'marking_templates': marking_templates_str
            }
        }
        logger4.info(f"[Provider1C] Подгрузили в словарь от 1с {result}")
        # Извлекаем данные первого шаблона (если он есть)
        if marking_templates:
            first_template = marking_templates[0]
            template_type = first_template.get('type')
            template_type_ru = first_template.get('type_RU')
            template_path = first_template.get('path')
            logger4.info(
                f"[Provider1C] Найден шаблон маркировки: "
                f"type={template_type}, type_RU={template_type_ru}, path={template_path}"
            )
        else:
            logger4.warning(f"[Provider1C] Для заказа {order} шаблоны маркировки не найдены")
            template_type = None
            template_type_ru = None
            template_path = None

        """
        # Вывод в консоль
        print("="*50)
        print(f"Order ID: {order_id}")
        print(f"Board Name: {board_name}")
        print(f"Version: {version}")
        print(f"Quantity: {count}")
        print(f"Firmware: {firmware}")
        print("\nComponents:")
        for comp_code, comp_desc in components.items():
            print(f"  {comp_code}: {comp_desc}")

        print("\nMarking Templates:")
        if marking_templates:
            print(f"  Type: {template_type}")
            print(f"  Type (RU): {template_type_ru}")
            print(f"  Path: {template_path}")
        else:
            print("  No marking templates available")

        print("\nBatch Numbers:")
        for i, item in enumerate(batch, 1):
            print(f"  {i}. Full: {item['number']} | 8-digit: {item['number8']} | 15-digit: {item['number15']}")
        print("="*50)
        """
        
        

        logger4.info(
            f"[Provider1C] Данные успешно получены: "
            f"order_id={order_id}, board_name={board_name}, version={version}, count={count}"
        )
        return result
    except requests.exceptions.Timeout:
        logger4.exception(f"[Provider1C] Таймаут при получении данных по заказу: {order}")
        raise
    except requests.exceptions.HTTPError as e:
        logger4.exception(f"[Provider1C] HTTP ошибка при получении данных по заказу {order}: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger4.exception(f"[Provider1C] Ошибка запроса к 1С по заказу {order}: {e}")
        raise
    except ValueError as e:
        logger4.exception(f"[Provider1C] Ошибка разбора JSON по заказу {order}: {e}")
        raise
    except Exception as e:
        logger4.exception(f"[Provider1C] Неизвестная ошибка в fetch_data по заказу {order}: {e}")
        raise




"""
# dict = fetch_data("ЗНП-5972.1.1")
# db_connection = SQLite.DatabaseConnection()
# db_connection.get_order_insert_orders_frm1C(dict)

# """ 
# getOrders()
# db_connection = SQLite.DatabaseConnection()

# getOrders()
# dict = fetch_data("ЗНП-48378.1.1")
# print(dict)


# db_connection = SQLite.DatabaseConnection()
# db_connection.get_order_insert_orders_frm1C(dict)


