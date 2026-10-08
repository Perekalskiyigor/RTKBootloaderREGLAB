# # python -m PyInstaller --onefile StrarterBotloader.py

# import os
# import sys
# import time
# import subprocess
# from pathlib import Path
# from opcua import Client, ua
# import sqlite3
# import threading
# import wmi
# import SQLite
# import pythoncom

# DB_PATH = r"orders.db"

# LOAD_NODES = {
#     1: "ns=2;s=Application.GVL.OPC_load_t1",
#     2: "ns=2;s=Application.GVL.OPC_load_t2",
#     3: "ns=2;s=Application.GVL.OPC_load_t3",
# }

# RES_NODES = {
#     1: "ns=2;s=Application.GVL.OPC_res_load_t1",
#     2: "ns=2;s=Application.GVL.OPC_res_load_t2",
#     3: "ns=2;s=Application.GVL.OPC_res_load_t3",
# }

# OPC_URL = "opc.tcp://192.168.1.3:48010"
# NODE_START   = "ns=2;s=Application.UserInterface.OPC_start_python"
# NODE_RUNNING = "ns=2;s=Application.UserInterface.OPC_log"
# POLL_SEC = 0.5

# EXE1 = r"C:\nails_table_v4\hub\nails_table_hub\nails_table_hub.exe"
# #EXE2 = r"C:\Users\i.perekalskii\Desktop\DEV\RTKBootloader\dist\WORK_FILE_21_07.exe"
# EXE2 = r"C:\DEV_С\RTKBootloaderREGLAB\dist\WORK_FILE_21_07.exe"
# #EXE3 = r"C:\Users\i.perekalskii\Desktop\DEV\RTKBootloader\dist\ServerRTK.exe"
# EXE3 = r"C:\DEV_С\RTKBootloaderREGLAB\dist\ServerRTK.exe"
# CONNECT_TIMEOUT_SEC = 8.0
# RECONNECT_DELAY_SEC = 2.0

# proc1 = None
# proc2 = None
# proc3 = None


# """Мониторинг ИБП"""
# def ups_monitor_thread():
#     """
#     Мониторинг питания ИБП через WMI.
#     BatteryStatus:
#     1 = питание от батареи
#     2 = питание от сети
#     """

#     pythoncom.CoInitialize()

#     last_status = 2  # при старте считаем, что питание нормальное

#     try:
#         c = wmi.WMI()
#         log("[UPS] monitor started")
#     except Exception as e:
#         log(f"[UPS] WMI init error: {e}")
#         pythoncom.CoUninitialize()
#         return

#     try:
#         while True:
#             try:
#                 batteries = c.Win32_Battery()

#                 if batteries:
#                     status = int(batteries[0].BatteryStatus)

#                     if status == 1 and last_status != 1:
#                         log("[UPS] 220В пропало. Питание от батареи.")
#                         SQLite.insert_log_for1C(
#                             description="220В пропало. Питание от батареи",
#                             user="UPS"
#                         )

#                     elif status == 2 and last_status != 2:
#                         log("[UPS] 220В восстановлено. Питание от сети.")
#                         SQLite.insert_log_for1C(
#                             description="220В восстановлено. Питание от сети",
#                             user="UPS"
#                         )

#                     last_status = status

#                 else:
#                     if last_status != -1:
#                         log("[UPS] ИБП не найден через Win32_Battery")
#                         last_status = -1

#             except Exception as e:
#                 log(f"[UPS] monitor error: {e}")

#             time.sleep(1)

#     finally:
#         pythoncom.CoUninitialize()


# def get_status_from_db(table_num):
#     conn = sqlite3.connect(DB_PATH, timeout=5)
#     cur = conn.cursor()

#     cur.execute("""
#         SELECT status, test_result
#         FROM order_details
#         WHERE stand_id IN (?, ?)
#         ORDER BY COALESCE(finished_at, started_at, reserved_at) DESC
#         LIMIT 1
#     """, (f"table_{table_num}", f"nt_cmpp_rtk_{table_num}"))

#     row = cur.fetchone()
#     conn.close()

#     if not row:
#         return None

#     status, test_result = row

#     if status == "sent":
#         return 1, 0

#     if status == "done":
#         return 0, 2

#     if status == "failed":
#         return 0, 1

#     return None

# def _app_dir() -> Path:
#     # для pyinstaller onefile: sys.executable = путь к exe
#     return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


# LOG_DIR = _app_dir() / "logs"
# LOG_DIR.mkdir(parents=True, exist_ok=True)
# LOG_FILE = LOG_DIR / "starter.log"


# def log(msg: str):
#     ts = time.strftime("%Y-%m-%d %H:%M:%S")
#     line = f"{ts} {msg}"
#     print(line, flush=True)
#     try:
#         with open(LOG_FILE, "a", encoding="utf-8") as f:
#             f.write(line + "\n")
#     except Exception:
#         pass


# def is_running(p: subprocess.Popen | None) -> bool:
#     return p is not None and p.poll() is None


# def _popen_new_console(exe_path: str):
#     exe = Path(exe_path)
#     return subprocess.Popen(
#         [str(exe)],  # Запускаем напрямую, без cmd
#         cwd=str(exe.parent),
#         creationflags=subprocess.CREATE_NEW_CONSOLE,  # Всё равно откроет новое окно
#     )


# def start_procs_once():
#     global proc1, proc2, proc3

#     if not is_running(proc1):
#         proc1 = _popen_new_console(EXE1)
#         log(f"[APPS] started nails_table_bridge (new console), launcher pid={proc1.pid}")

#     time.sleep(10)

#     if not is_running(proc3):
#         proc3 = _popen_new_console(EXE3)
#         log(f"[APPS] started ServerRTK (new console), launcher pid={proc3.pid}")

#     time.sleep(3)

#     if not is_running(proc2):
#         proc2 = _popen_new_console(EXE2)
#         log(f"[APPS] started main.exe (new console), launcher pid={proc2.pid}")


# def _taskkill_pid(pid: int):
#     subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
#                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)


# def _taskkill_name(name: str):
#     subprocess.run(["taskkill", "/IM", name, "/T", "/F"],
#                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

# def is_process_running(exe_name):
#     result = subprocess.run(
#         ["tasklist"],
#         capture_output=True,
#         text=True
#     )
#     return exe_name.lower() in result.stdout.lower()

# def stop_procs_once():
#     global proc1, proc2, proc3

#     # Останавливаем прошивальщик / main
#     if is_running(proc2):
#         log("[APPS] stopping WORK_FILE_25_05.exe")
#         _taskkill_pid(proc2.pid)

#     # Останавливаем hub / bridge / скрипт
#     if is_running(proc1):
#         log("[APPS] stopping nails_table_hub.exe")
#         _taskkill_pid(proc1.pid)

#     # Добиваем по именам на случай, если PID уже не тот
#     _taskkill_name(Path(EXE2).name)
#     _taskkill_name(Path(EXE1).name)

#     # ServerRTK НЕ трогаем
#     proc1 = None
#     proc2 = None

#     proc1 = None
#     proc2 = None


# def read_bool(node) -> int:
#     v = node.get_value()
#     try:
#         return 1 if int(v) == 1 else 0
#     except Exception:
#         return 1 if bool(v) else 0


# def write_string(node, text: str):
#     node.set_value(ua.DataValue(ua.Variant(text, ua.VariantType.String)))

# def write_int(node, value: int):
#     node.set_value(ua.DataValue(ua.Variant(int(value), ua.VariantType.Int16)))


# def connect_with_timeout(url: str, timeout_sec: float) -> Client:
#     client = Client(url)
#     t0 = time.time()
#     log(f"[OPC] connecting to {url} ...")

#     # connect() может зависать, поэтому контролируем временем
#     # (в python-opcua нет простого параметра timeout на connect во всех версиях)
#     while True:
#         try:
#             client.connect()
#             log("[OPC] connected")
#             return client
#         except Exception as e:
#             # если сразу ошибка — выходим по таймауту
#             if time.time() - t0 >= timeout_sec:
#                 raise TimeoutError(f"connect timeout after {timeout_sec}s: {e}")
#             time.sleep(0.2)


# def main():
#     global proc1, proc2, proc3
#     log(f"[BOOT] pid={os.getpid()} exe={sys.executable}")

#     # Мониторинг ибп
#     threading.Thread(
#         target=ups_monitor_thread,
#         daemon=True
#     ).start()

    
#     last_log = None

#     while True:
#         client = None
#         try:
#             client = connect_with_timeout(OPC_URL, CONNECT_TIMEOUT_SEC)

            

#             node_start = client.get_node(NODE_START)
#             node_log = client.get_node(NODE_RUNNING)

#             load_nodes = {n: client.get_node(nodeid) for n, nodeid in LOAD_NODES.items()}
#             res_nodes = {n: client.get_node(nodeid) for n, nodeid in RES_NODES.items()}

#             last_state = None
#             t_heartbeat = 0.0

#             last_backup_states = {}

#             while True:
#                 main_alive = is_process_running(Path(EXE2).name)
#                 server_alive = is_process_running(Path(EXE3).name)
#                 bridge_alive = is_process_running(Path(EXE1).name)

#                 state = read_bool(node_start)

#                 if not server_alive:
#                     proc3 = _popen_new_console(EXE3)
#                     log(f"[APPS] ServerRTK restarted, pid={proc3.pid}")

#                 if state != last_state:
#                     log(f"[OPC] START changed: {last_state} -> {state}")
#                     if state == 1:
#                         start_procs_once()
#                     else:
#                         stop_procs_once()
#                     last_state = state

#                 running = server_alive and main_alive and bridge_alive
#                 msg = "RUNNING" if running else "STOPPED"
#                 if msg != last_log:
#                     write_string(node_log, msg)
#                     log(f"[OPC] wrote OPC_log='{msg}'")
#                     last_log = msg
                
#                 # Резервное обновление статусов прошивки из БД,
#                 # если основной main.exe не работает
#                 main_alive = is_process_running(Path(EXE2).name)

#                 if not main_alive:
#                     for table_num in (1, 2, 3):
#                         status = get_status_from_db(table_num)

#                         if status:
#                             load_value, res_value = status

#                             write_int(load_nodes[table_num], load_value)
#                             write_int(res_nodes[table_num], res_value)

#                             current_state = (load_value, res_value)

#                             if last_backup_states.get(table_num) != current_state:
#                                 log(
#                                     f"[OPC-BACKUP] table={table_num} "
#                                     f"load={load_value}, res={res_value}"
#                                 )
#                                 last_backup_states[table_num] = current_state

#                 # каждые 5 сек пишем что цикл жив
#                 if time.time() - t_heartbeat > 5:
#                     log("[HB] alive")
#                     t_heartbeat = time.time()

#                 time.sleep(POLL_SEC)

#         except Exception as e:
#             log(f"[OPC] error: {e}")
#             try:
#                 if client:
#                     client.disconnect()
#             except Exception:
#                 pass
#             time.sleep(RECONNECT_DELAY_SEC)


# if __name__ == "__main__":
#     main()

# python -m PyInstaller --onefile StrarterBotloader.py

import os
import sys
import time
import subprocess
from pathlib import Path
from opcua import Client, ua
import sqlite3
import threading
import wmi
import SQLite
import pythoncom

DB_PATH = r"orders.db"

LOAD_NODES = {
    1: "ns=2;s=Application.GVL.OPC_load_t1",
    2: "ns=2;s=Application.GVL.OPC_load_t2",
    3: "ns=2;s=Application.GVL.OPC_load_t3",
}

RES_NODES = {
    1: "ns=2;s=Application.GVL.OPC_res_load_t1",
    2: "ns=2;s=Application.GVL.OPC_res_load_t2",
    3: "ns=2;s=Application.GVL.OPC_res_load_t3",
}

OPC_URL = "opc.tcp://192.168.1.3:48010"
NODE_START   = "ns=2;s=Application.UserInterface.OPC_start_python"
NODE_RUNNING = "ns=2;s=Application.UserInterface.OPC_log"
POLL_SEC = 0.5

#EXE1 = r"C:\nails_table_v4\hub\nails_table_hub\nails_table_hub.exe"
EXE1 =  r"C:\nails_table_hub\v0.4.3\nails_table_hub\nails_table_hub.exe"
#EXE2 = r"C:\Users\i.perekalskii\Desktop\DEV\RTKBootloader\dist\WORK_FILE_21_07.exe"
EXE2 = r"C:\DEV_C\RTKBootloaderREGLAB\dist\WORK_FILE_21_07.exe"
#EXE3 = r"C:\Users\i.perekalskii\Desktop\DEV\RTKBootloader\dist\ServerRTK.exe"
EXE3 = r"C:\DEV_C\RTKBootloaderREGLAB\dist\ServerRTK.exe"
CONNECT_TIMEOUT_SEC = 8.0
RECONNECT_DELAY_SEC = 2.0

proc1 = None
proc2 = None
proc3 = None


# ---------------------------------------------------------------------------
# Логирование
# ---------------------------------------------------------------------------

def _app_dir() -> Path:
    # для pyinstaller onefile: sys.executable = путь к exe
    return Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent


LOG_DIR = _app_dir() / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "starter.log"


def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Мониторинг ИБП
# ---------------------------------------------------------------------------

def ups_monitor_thread():
    """
    Мониторинг питания ИБП через WMI.
    BatteryStatus:
    1 = питание от батареи
    2 = питание от сети
    """
    pythoncom.CoInitialize()

    last_status = 2  # при старте считаем, что питание нормальное

    try:
        c = wmi.WMI()
        log("[UPS] monitor started")
    except Exception as e:
        log(f"[UPS] WMI init error: {e}")
        pythoncom.CoUninitialize()
        return

    try:
        while True:
            try:
                batteries = c.Win32_Battery()

                if batteries:
                    status = int(batteries[0].BatteryStatus)

                    if status == 1 and last_status != 1:
                        log("[UPS] 220В пропало. Питание от батареи.")
                        try:
                            SQLite.insert_log_for1C(
                                description="220В пропало. Питание от батареи",
                                user="UPS"
                            )
                        except Exception as e:
                            log(f"[UPS] insert_log_for1C error: {e}")

                    elif status == 2 and last_status != 2:
                        log("[UPS] 220В восстановлено. Питание от сети.")
                        try:
                            SQLite.insert_log_for1C(
                                description="220В восстановлено. Питание от сети",
                                user="UPS"
                            )
                        except Exception as e:
                            log(f"[UPS] insert_log_for1C error: {e}")

                    last_status = status

                else:
                    if last_status != -1:
                        log("[UPS] ИБП не найден через Win32_Battery")
                        last_status = -1

            except Exception as e:
                log(f"[UPS] monitor error: {e}")

            time.sleep(1)

    finally:
        pythoncom.CoUninitialize()


# ---------------------------------------------------------------------------
# Работа с БД
# ---------------------------------------------------------------------------

def get_status_from_db(table_num):
    conn = sqlite3.connect(DB_PATH, timeout=5)
    cur = conn.cursor()

    cur.execute("""
        SELECT status, test_result
        FROM order_details
        WHERE stand_id IN (?, ?)
        ORDER BY COALESCE(finished_at, started_at, reserved_at) DESC
        LIMIT 1
    """, (f"table_{table_num}", f"nt_cmpp_rtk_{table_num}"))

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    status, test_result = row

    if status == "sent":
        return 1, 0

    if status == "done":
        return 0, 2

    if status == "failed":
        return 0, 1

    return None


# ---------------------------------------------------------------------------
# Запуск / остановка процессов
# ---------------------------------------------------------------------------

def is_running(p: subprocess.Popen | None) -> bool:
    return p is not None and p.poll() is None


def _popen_new_console(exe_path: str):
    """
    Запуск exe в новом окне консоли.
    Все ошибки запуска логируются, исключение пробрасывается наверх.
    """
    exe = Path(exe_path)

    print(f"[APPS] trying to start: {exe}", flush=True)
    log(f"[APPS] trying to start: {exe}")

    # Проверка существования файла до запуска
    if not exe.exists():
        msg = f"[APPS] FILE NOT FOUND: {exe}"
        print(msg, flush=True)
        log(msg)
        raise FileNotFoundError(msg)

    # Проверка, что это файл, а не папка
    if not exe.is_file():
        msg = f"[APPS] NOT A FILE: {exe}"
        print(msg, flush=True)
        log(msg)
        raise IsADirectoryError(msg)

    try:
        proc = subprocess.Popen(
            [str(exe)],
            cwd=str(exe.parent),
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        log(f"[APPS] started OK: {exe} pid={proc.pid}")
        return proc

    except FileNotFoundError as e:
        msg = f"[APPS] WinError 2 — file not found: {exe} | {e}"
        print(msg, flush=True)
        log(msg)
        raise

    except OSError as e:
        msg = f"[APPS] OSError while starting {exe}: {e}"
        print(msg, flush=True)
        log(msg)
        raise

    except Exception as e:
        msg = f"[APPS] unexpected error while starting {exe}: {e}"
        print(msg, flush=True)
        log(msg)
        raise


def start_procs_once():
    global proc1, proc2, proc3

    # --- EXE1 ---
    if not is_running(proc1):
        try:
            print(f"[APPS] calling EXE1: {EXE1}", flush=True)
            proc1 = _popen_new_console(EXE1)
            log(f"[APPS] started nails_table_bridge (new console), launcher pid={proc1.pid}")
        except Exception as e:
            log(f"[APPS] FAILED to start EXE1 ({EXE1}): {e}")
            proc1 = None

    time.sleep(10)

    # --- EXE3 ---
    if not is_running(proc3):
        try:
            print(f"[APPS] calling EXE3: {EXE3}", flush=True)
            proc3 = _popen_new_console(EXE3)
            log(f"[APPS] started ServerRTK (new console), launcher pid={proc3.pid}")
        except Exception as e:
            log(f"[APPS] FAILED to start EXE3 ({EXE3}): {e}")
            proc3 = None

    time.sleep(3)

    # --- EXE2 ---
    if not is_running(proc2):
        try:
            print(f"[APPS] calling EXE2: {EXE2}", flush=True)
            proc2 = _popen_new_console(EXE2)
            log(f"[APPS] started main.exe (new console), launcher pid={proc2.pid}")
        except Exception as e:
            log(f"[APPS] FAILED to start EXE2 ({EXE2}): {e}")
            proc2 = None


def _taskkill_pid(pid: int):
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except FileNotFoundError as e:
        log(f"[APPS] taskkill not found: {e}")
    except Exception as e:
        log(f"[APPS] taskkill pid={pid} error: {e}")


def _taskkill_name(name: str):
    try:
        subprocess.run(
            ["taskkill", "/IM", name, "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except FileNotFoundError as e:
        log(f"[APPS] taskkill not found: {e}")
    except Exception as e:
        log(f"[APPS] taskkill name={name} error: {e}")


def is_process_running(exe_name):
    try:
        result = subprocess.run(
            ["tasklist"],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return exe_name.lower() in result.stdout.lower()
    except FileNotFoundError as e:
        log(f"[APPS] tasklist not found: {e}")
        return False
    except Exception as e:
        log(f"[APPS] is_process_running error: {e}")
        return False


def stop_procs_once():
    global proc1, proc2, proc3

    # Останавливаем прошивальщик / main
    if is_running(proc2):
        log("[APPS] stopping WORK_FILE_21_07.exe")
        _taskkill_pid(proc2.pid)

    # Останавливаем hub / bridge / скрипт
    if is_running(proc1):
        log("[APPS] stopping nails_table_hub.exe")
        _taskkill_pid(proc1.pid)

    # Добиваем по именам на случай, если PID уже не тот
    _taskkill_name(Path(EXE2).name)
    _taskkill_name(Path(EXE1).name)

    # ServerRTK НЕ трогаем
    proc1 = None
    proc2 = None


# ---------------------------------------------------------------------------
# OPC-обёртки
# ---------------------------------------------------------------------------

def read_bool(node) -> int:
    v = node.get_value()
    try:
        return 1 if int(v) == 1 else 0
    except Exception:
        return 1 if bool(v) else 0


def write_string(node, text: str):
    node.set_value(ua.DataValue(ua.Variant(text, ua.VariantType.String)))


def write_int(node, value: int):
    node.set_value(ua.DataValue(ua.Variant(int(value), ua.VariantType.Int16)))


def connect_with_timeout(url: str, timeout_sec: float) -> Client:
    client = Client(url)
    t0 = time.time()
    log(f"[OPC] connecting to {url} ...")

    while True:
        try:
            client.connect()
            log("[OPC] connected")
            return client
        except Exception as e:
            if time.time() - t0 >= timeout_sec:
                raise TimeoutError(f"connect timeout after {timeout_sec}s: {e}")
            time.sleep(0.2)


# ---------------------------------------------------------------------------
# Главный цикл
# ---------------------------------------------------------------------------

def main():
    global proc1, proc2, proc3
    log(f"[BOOT] pid={os.getpid()} exe={sys.executable}")

    # Мониторинг ИБП
    threading.Thread(
        target=ups_monitor_thread,
        daemon=True
    ).start()

    last_log = None

    while True:
        client = None
        try:
            client = connect_with_timeout(OPC_URL, CONNECT_TIMEOUT_SEC)

            node_start = client.get_node(NODE_START)
            node_log = client.get_node(NODE_RUNNING)

            load_nodes = {n: client.get_node(nodeid) for n, nodeid in LOAD_NODES.items()}
            res_nodes = {n: client.get_node(nodeid) for n, nodeid in RES_NODES.items()}

            last_state = None
            t_heartbeat = 0.0

            last_backup_states = {}

            while True:
                main_alive = is_process_running(Path(EXE2).name)
                server_alive = is_process_running(Path(EXE3).name)
                bridge_alive = is_process_running(Path(EXE1).name)

                state = read_bool(node_start)

                # Перезапуск ServerRTK, если он упал
                if not server_alive:
                    try:
                        print(f"[APPS] restarting EXE3: {EXE3}", flush=True)
                        proc3 = _popen_new_console(EXE3)
                        log(f"[APPS] ServerRTK restarted, pid={proc3.pid}")
                        server_alive = True
                    except Exception as e:
                        log(f"[APPS] FAILED to restart EXE3 ({EXE3}): {e}")
                        proc3 = None

                if state != last_state:
                    log(f"[OPC] START changed: {last_state} -> {state}")
                    if state == 1:
                        start_procs_once()
                    else:
                        stop_procs_once()
                    last_state = state

                # Пересчитываем флаги после возможного запуска
                main_alive = is_process_running(Path(EXE2).name)
                bridge_alive = is_process_running(Path(EXE1).name)
                server_alive = is_process_running(Path(EXE3).name)

                running = server_alive and main_alive and bridge_alive
                msg = "RUNNING" if running else "STOPPED"
                if msg != last_log:
                    try:
                        write_string(node_log, msg)
                        log(f"[OPC] wrote OPC_log='{msg}'")
                    except Exception as e:
                        log(f"[OPC] write OPC_log error: {e}")
                    last_log = msg

                # Резервное обновление статусов прошивки из БД,
                # если основной main.exe не работает
                if not main_alive:
                    for table_num in (1, 2, 3):
                        try:
                            status = get_status_from_db(table_num)
                        except Exception as e:
                            log(f"[OPC-BACKUP] db error for table={table_num}: {e}")
                            continue

                        if status:
                            load_value, res_value = status

                            try:
                                write_int(load_nodes[table_num], load_value)
                                write_int(res_nodes[table_num], res_value)
                            except Exception as e:
                                log(f"[OPC-BACKUP] write error for table={table_num}: {e}")
                                continue

                            current_state = (load_value, res_value)

                            if last_backup_states.get(table_num) != current_state:
                                log(
                                    f"[OPC-BACKUP] table={table_num} "
                                    f"load={load_value}, res={res_value}"
                                )
                                last_backup_states[table_num] = current_state

                # каждые 5 сек пишем что цикл жив
                if time.time() - t_heartbeat > 5:
                    log("[HB] alive")
                    t_heartbeat = time.time()

                time.sleep(POLL_SEC)

        except Exception as e:
            log(f"[OPC] error: {e}")
            try:
                if client:
                    client.disconnect()
            except Exception:
                pass
            time.sleep(RECONNECT_DELAY_SEC)


if __name__ == "__main__":
    main()