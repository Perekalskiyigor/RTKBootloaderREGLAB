# pyinstaller --onefile Log_Forwarder.py

"""Служба которая мониторит бд таблицу лог и шлет логи которые накопил ртк. Работает как отдельная служба"""
import os
import sys
import time
import json
import logging
import sqlite3
from contextlib import closing
from typing import List, Dict, Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime

"""
SQLite → HTTP forwarder (конфиг прямо в коде)

- Ищет в SQLite таблице `Logs` строки со `status = 0`
- Формирует JSON:
{
    "rtk_id": "RTK_R050_BoardsIO_1",
    "event_log": [
        {"operator": <user>, "event": <description>, "time": <data>},
        ...
    ]
}
- Делает POST на ENDPOINT_URL
- При 2xx — проставляет статус=1 для отправленных id; иначе оставляет 0

Отредактируйте блок CONFIG ниже под себя и запускайте: `python sqlite_log_forwarder.py`
"""

if getattr(sys, "frozen", False):
    # Запущено как PyInstaller EXE
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Запущено как обычный .py
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# =========================
# CONFIG — правьте под себя
# =========================
DAILY_TIME = "15:07"                              # время ежедневного запуска (локальное время, HH:MM или HH:MM:SS)
RUN_ON_STARTUP = False                              # если True — выполнит отправку сразу при старте
# =========================


DB_PATH = os.path.join(BASE_DIR, "orders.db")
ENDPOINT_URL = "https://c.prosyst.ru/prosoft_erp_work/hs/rtk/eventlog/"      # ваш эндпоинт
RTK_ID = "RTK_R050_BoardsIO_1"                         # идентификатор в payload
POLL_INTERVAL_SEC = 300                              # период опроса (сек)
BATCH_SIZE = 100                                   # размер партии
LOG_PATH = os.path.join(BASE_DIR, "LogForwarderLog.log")        # путь к лог-файлу
USERNAME = "rtk_cmpp"
PASSWORD = "456789Aa"
# =========================


def build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    # --- добавляем авторизацию ---
    session.auth = (USERNAME, PASSWORD)
    # ------------------------------

    return session


def get_logger(log_path: str) -> logging.Logger:
    logger = logging.getLogger("forwarder")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(fmt)
        logger.addHandler(sh)
    return logger


def fetch_pending(conn: sqlite3.Connection, batch_size: int) -> List[Dict[str, Any]]:
    conn.row_factory = sqlite3.Row
    with closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT id, description, data, status, user, order_num, vendor_code
            FROM LogsLogRTKto1C
            WHERE status = 0
            ORDER BY id
            LIMIT ?
            """,
            (batch_size,),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]
    

def fetch_today(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """
    Возвращает все записи из Logs за текущие сутки (по полю data).
    Ориентируется на полночь localtime.
    """
    conn.row_factory = sqlite3.Row
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start.replace(hour=23, minute=59, second=59)

    # Преобразуем в строки для SQL-условия.
    # Если data — тип DATETIME или текст в формате "YYYY-MM-DD HH:MM:SS"
    # Можно отфильтровать через BETWEEN.
    start_str = today_start.strftime("%Y-%m-%d %H:%M:%S")
    end_str = today_end.strftime("%Y-%m-%d %H:%M:%S")

    with closing(conn.cursor()) as cur:
        cur.execute(
            """
            SELECT id, description, data, status, user, order_num, vendor_code
            FROM LogRTKto1C
            WHERE data BETWEEN ? AND ?
            ORDER BY id
            """,
            (start_str, end_str),
        )
        rows = cur.fetchall()
        return [dict(r) for r in rows]



def mark_sent(conn: sqlite3.Connection, ids: List[int]) -> None:
    if not ids:
        return
    with closing(conn.cursor()) as cur:
        qmarks = ",".join(["?"] * len(ids))
        cur.execute(f"UPDATE LogRTKto1C SET status = 1 WHERE id IN ({qmarks})", ids)
    conn.commit()


def make_payload(rtk_id: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    event_log = []
    for r in rows:
        event_item = {
            "operator": r.get("user") or "",
            "event": r.get("description") or "",
            "time": str(r.get("data") or ""),
        }
        # Если есть order_num и vendor_code, добавляем их в словарь
        if "order_num" in r:
            event_item["order_num"] = r.get("order_num") or ""
        if "vendor_code" in r:
            event_item["vendor_code"] = r.get("vendor_code") or ""
        event_log.append(event_item)
    return {"rtk_id": rtk_id, "event_log": event_log}


def process_once(
    db_path: str,
    endpoint_url: str,
    rtk_id: str,
    batch_size: int,
    session: requests.Session,
    logger: logging.Logger,
) -> int:
    """Отправляет одну партию. Возвращает число успешно помеченных строк."""
    if not os.path.exists(db_path):
        logger.error(f"DB not found: {db_path}")
        return 0

    with sqlite3.connect(db_path, timeout=30) as conn:
        rows = fetch_today(conn)
        if not rows:
            logger.info("Нет новых строк (status=0)")
            return 0

        payload = make_payload(rtk_id, rows)
        print(payload)  # замените эту строку на
        print(json.dumps(payload, ensure_ascii=False, indent=4))
        try:
            resp = session.post(endpoint_url, json=payload, timeout=30)
        except Exception as e:
            logger.error(f"POST failed: {e}")
            return 0

        if 200 <= resp.status_code < 300:
            ids = [r["id"] for r in rows]
            mark_sent(conn, ids)
            logger.info(
                f"Отправлено {len(rows)} событий → {endpoint_url}; помечены status=1: {ids[0]}..{ids[-1]}"
            )
            return len(rows)
        else:
            try:
                body = resp.text[:500]
            except Exception:
                body = "<no body>"
            logger.error(
                f"Эндпоинт вернул {resp.status_code}. Body: {body} — оставляю status=0"
            )
            return 0


def process_all(
    db_path: str,
    endpoint_url: str,
    rtk_id: str,
    batch_size: int,
    session: requests.Session,
    logger: logging.Logger,
) -> int:
    """Гонит несколько партий подряд, пока не закончатся записи или не случится ошибка.
    Возвращает общее число успешно помеченных строк за этот прогон.
    """
    total = 0
    while True:
        n = process_once(db_path, endpoint_url, rtk_id, batch_size, session, logger)
        total += n
        if n == 0 or n < batch_size:
            break
    return total





def main():
    logger = get_logger(LOG_PATH)
    session = build_session()

    logger.info(
        f"Старт: db={DB_PATH} url={ENDPOINT_URL} interval={POLL_INTERVAL_SEC} batch={BATCH_SIZE}"
    )

    if RUN_ON_STARTUP:
        processed = process_all(DB_PATH, ENDPOINT_URL, RTK_ID, BATCH_SIZE, session, logger)
        logger.info(f"Первичный прогон завершён, отправлено {processed} строк")

    while True:
        processed = process_all(DB_PATH, ENDPOINT_URL, RTK_ID, BATCH_SIZE, session, logger)
        logger.info(f"Очередной прогон завершён, отправлено {processed} строк")
        time.sleep(POLL_INTERVAL_SEC)


if __name__ == "__main__":
    main()
