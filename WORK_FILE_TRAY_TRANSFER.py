"""Упрощённый WORK_FILE_21_07.py: новая тара -> 4 ячейки готовой тары.

python WORK_FILE_TRAY_TRANSFER.py
Узел готовой тары: BOOL Application.UserInterface.OPC_ready_tray_full.
Python выставляет OPC_ready_tray_full, ПЛК сбрасывает его после замены готовой тары.
"""

# python -m PyInstaller --onefile WORK_FILE_TRAY_TRANSFER.py

import logging
import threading
import time
import SQLite

from opcua import Client, ua
from pymodbus.server.sync import ModbusTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from ReadyTrays import ReadyTrays, TrayStateError


# Сохраняем имена счётчиков и адреса оборудования из рабочего файла.
NEW_BOARD_CELL_LIMIT = 61
READY_BOARD_CELL_LIMIT = 4
ROBOT_TIMEOUT = 7200  # Таймаут команды как в _send_robot_command исходника.
OPC_URL = "opc.tcp://192.168.1.3:48010"
MODBUS_ADDRESS = ("192.168.1.100", 502)

Cell = 0
Cell1 = 0  # Сколько плат взято из новой тары: 0..61.
Cell2 = 0  # Сколько готовых ячеек заполнено: 0..4.
Tray_robot = 2  # Постоянная готовая тара; исходный ящик выбирается командой 211.


EMERGENCY_STOP = threading.Event()
# Общий менеджер двух пневмокареток
ready_trays = ReadyTrays(max_state_age=3.0)
READY_TRAY_REPLACED = threading.Event()
STOP_PROGRAM = threading.Event()
shared_data_lock = threading.Lock()
logger4 = logging.getLogger("LoggerTRAY_TRANSFER")


shared_data = {
    'OPC-DB': {
        'OPC_START_RTK': False,
        'OPC_pause_RTK': False,
        'OPC_restart_RTK': False,
        'OPC_finish_order': False,
        'OPC_ready_tray_full': False,
        'OPC_end_order': True,  
        'OPC_cnt_newBoard': NEW_BOARD_CELL_LIMIT,
        'OPC_cnt_Board': NEW_BOARD_CELL_LIMIT,
        'OPC_success_count': 0,
        'OPC_nonsuccess_count': 0,
        'OPC_nameboard': 'Перекладка плат',
        'OPC_firmware': '',
        'OPC_name': '',
        'OPC_log': 'Ожидание старта перекладки',
    }
}


def opc_set(key, value):
    with shared_data_lock:
        shared_data['OPC-DB'][key] = value


def log_message(message):
    logger4.info(message)
    opc_set('OPC_log', message)


def trigger_emergency(reason):
    # Только фиксируем ошибку: повторять движение с неизвестным положением платы нельзя.
    if not EMERGENCY_STOP.is_set():
        EMERGENCY_STOP.set()
        logger4.error(reason)
        opc_set('OPC_log', 'Остановка: ' + reason)


class OPCClient:
    def __init__(self, url):
        self.client = Client(url, timeout=3)
        self.connected = threading.Event()
        self.user_ready = threading.Event()
        self.ready_full_sent = False
        self.nodes = {}
        self.disabled_stubs = set()
        self.update_thread = threading.Thread(target=self.update_registers, daemon=True)

        # ================= ПНЕВМОКАРЕТКИ =================

    def read_karetka(self, name):
        if not self.connected.is_set():
            raise RuntimeError("OPC отключён")

        node = self.node(name)
        value = node.get_value()

        if type(value) is not bool:
            raise RuntimeError(
                f"Неверный тип OPC-узла каретки: {name}"
            )

        return value

    def write_karetka(self, name, value):
        if not self.connected.is_set():
            raise RuntimeError("OPC отключён")

        self._write(
            name,
            bool(value),
            ua.VariantType.Boolean
        )

    # =================================================

    def node(self, name, group='UserInterface'):
        nodeid = f'ns=2;s=Application.{group}.{name}'
        if nodeid not in self.nodes:
            self.nodes[nodeid] = self.client.get_node(nodeid)
        return self.nodes[nodeid]

    
    def _write(self, name, value, vtype, group='UserInterface'):
        self.node(name, group).set_value(ua.DataValue(ua.Variant(value, vtype)))

    def _write_stub(self, name, value, vtype, group='UserInterface'):
        # Отсутствие ненужного узла витрины не мешает перекладке.
        key = (group, name)
        if key in self.disabled_stubs:
            return
        try:
            self._write(name, value, vtype, group)
        except ua.UaStatusCodeError as exc:
            if exc.code not in (ua.StatusCodes.BadNodeIdUnknown, ua.StatusCodes.BadNotWritable,
                                ua.StatusCodes.BadTypeMismatch, ua.StatusCodes.BadUserAccessDenied):
                raise
            self.disabled_stubs.add(key)
            logger4.warning('Заглушка %s.%s недоступна: %s', group, name, exc)

    def update_registers(self):
        while not STOP_PROGRAM.is_set():
            try:
                if not self.connected.is_set():
                    self.client.connect()
                    self.nodes.clear()
                    self.disabled_stubs.clear()
                    self.connected.set()
                    logger4.info('OPC подключён: %s', OPC_URL)

                # Синхронизация двух пневмокареток с Regul
                ready_trays.sync_opc(
                    self.read_karetka,
                    self.write_karetka
                )

                # Читаем те же кнопки панели, что и в основном рабочем файле.
                controls = {}
                user = self.node('OPC_name').get_value()
                if not isinstance(user, str):
                    raise ValueError('OPC_name: ожидался STRING')
                controls['OPC_name'] = user.strip()
                for name in ('OPC_start_RTK', 'OPC_pause_RTK', 'OPC_restart_RTK',
                             'OPC_finish_order'):
                    value = self.node(name).get_value()
                    if not isinstance(value, bool):
                        raise ValueError(f'{name}: ожидался BOOL')
                    controls['OPC_START_RTK' if name == 'OPC_start_RTK' else name] = value


                with shared_data_lock:
                    shared_data['OPC-DB'].update(controls)
                    opcdb = dict(shared_data['OPC-DB'])
                if controls['OPC_name']:
                    self.user_ready.set()
                else:
                    self.user_ready.clear()
                    

                self._write('OPC_log', opcdb['OPC_log'], ua.VariantType.String)
                self._write('OPC_end_order', opcdb['OPC_end_order'], ua.VariantType.Boolean)
                for name in ('OPC_cnt_newBoard', 'OPC_cnt_Board', 'OPC_success_count', 'OPC_nonsuccess_count'):
                    self._write_stub(name, opcdb[name], ua.VariantType.Int16)
                for name in ('OPC_nameboard', 'OPC_firmware'):
                    self._write_stub(name, opcdb[name], ua.VariantType.String)

                # Вместо прошивки, зрения и заказов отдаём постоянные заглушки.
                for number in (1, 2, 3):
                    for name in ('OPC_load_t', 'OPC_res_load_t'):
                        self._write_stub(f'{name}{number}', 0, ua.VariantType.Int16, 'GVL')
                for name in ('OPC_search_result', 'OPC_dataOrder'):
                    self._write_stub(name, [''], ua.VariantType.String)
                for name in ('OPC_vision_count', 'OPC_vision_status'):
                    self._write_stub(name, 0, ua.VariantType.Int16)
                for name in ('OPC_vision_occupied', 'OPC_vision_bad', 'OPC_vision_empty'):
                    self._write_stub(name, '', ua.VariantType.String)
                self._write_stub('OPC_vision_order', False, ua.VariantType.Boolean)
                if controls['OPC_restart_RTK']:
                    trigger_emergency('Получен OPC_restart_RTK')
                STOP_PROGRAM.wait(0.5)
            except TrayStateError as exc:
                ready_trays.connection_lost()

                trigger_emergency(
                    f"Ошибка состояния пневмокареток: {exc}"
                )

                self.connected.clear()
                self.user_ready.clear()

                logger4.exception(
                    "Ошибка управления пневмокаретками"
                )

                break
            except Exception as exc:
                if self.connected.is_set():
                    trigger_emergency(f'Ошибка OPC: {exc}')
                self.connected.clear()
                self.user_ready.clear()
                logger4.exception('Ошибка OPC; повтор подключения через 5 секунд')
                try:
                    self.client.disconnect()
                except Exception:
                    pass
                ready_trays.connection_lost()
                STOP_PROGRAM.wait(5)
        try:
            self.client.disconnect()
        except Exception:
            logger4.debug('OPC уже отключён', exc_info=True)


class ModbusProvider:
    def __init__(self):
        # Сохраняем адресацию ModbusSlaveContext из исходного файла.
        self.store = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [0] * 100))
        self.server = ModbusTcpServer(
            ModbusServerContext(slaves=self.store, single=True), address=MODBUS_ADDRESS)
        self.server_thread = threading.Thread(target=self.run_modbus_server, daemon=True)
        # Начальные значения выходов движения столов/прошивальщиков/подготовки.
        for address in (0, 2, 10, 12, 18, 20, 24, 25):
            self.store.setValues(3, address, [0])
        self.store.setValues(3, 6, [Tray_robot])

    def run_modbus_server(self):
        try:
            logger4.info('Modbus-сервер запущен: %s:%s', *MODBUS_ADDRESS)
            self.server.serve_forever()
        except Exception as exc:
            logger4.exception('Ошибка Modbus')
            trigger_emergency(f'Ошибка Modbus: {exc}')
        finally:
            if not STOP_PROGRAM.is_set():
                trigger_emergency('Modbus-сервер остановлен')

    def _send_robot_command(self, command, timeout_s=ROBOT_TIMEOUT):
        # Тот же обмен: Rob_Action (4) -> sub_Rob_Action (5).
        # 211 — забор из ящика, 241 — укладка в готовую тару. Tray всегда равен 2.
        if EMERGENCY_STOP.is_set() or STOP_PROGRAM.is_set():
            return False
        self.store.setValues(3, 6, [Tray_robot])
        self.store.setValues(3, 8, [Cell])
        # Как в исходнике, сначала даём ПЛК время прочитать тару и ячейку.
        time.sleep(1)
        if EMERGENCY_STOP.is_set() or STOP_PROGRAM.is_set():
            return False
        self.store.setValues(3, 4, [command])
        logger4.info('Команда %s отправлена роботу; ожидаем подтверждение в регистре 5', command)
        start_time = time.monotonic()
        try:
            while time.monotonic() - start_time < timeout_s:
                if EMERGENCY_STOP.is_set() or STOP_PROGRAM.is_set():
                    return False
                result = self.store.getValues(3, 5, count=1)[0]
                if result == command:
                    logger4.info('Робот подтвердил выполнение команды %s', command)
                    return True
                if result == 404:
                    trigger_emergency(f'Робот вернул 404 для команды {command}')
                    return False
                time.sleep(0.1)
            trigger_emergency(f'Таймаут команды робота {command}')
            return False
        finally:
            self.store.setValues(3, 4, [0])
            # ПЛК должен увидеть ноль между соседними командами.
            time.sleep(1)


def prepare_tables(modbus_provider):
    # Как в рабочем режиме: SETUP_TABLE (25) -> SUB_SETUP_TABLE (26).
    log_message('Ожидание от регула, что столы в начальной позиции')
    try:
        if EMERGENCY_STOP.is_set() or STOP_PROGRAM.is_set():
            return False
        modbus_provider.store.setValues(3, 25, [1])
        while not EMERGENCY_STOP.is_set() and not STOP_PROGRAM.is_set():
            if STOP_PROGRAM.wait(1):
                return False
            if EMERGENCY_STOP.is_set():
                return False
            if modbus_provider.store.getValues(3, 26, count=1)[0] == 1:
                log_message('Система подготовлена к работе')
                return True
        return False
    finally:
        modbus_provider.store.setValues(3, 25, [0])


def wait_for_start():
    waiting_logged = False

    while not EMERGENCY_STOP.is_set() and not STOP_PROGRAM.is_set():

        with shared_data_lock:
            start = shared_data['OPC-DB']['OPC_START_RTK']
            pause = shared_data['OPC-DB']['OPC_pause_RTK']
            finish = shared_data['OPC-DB']['OPC_finish_order']

        if finish:
            return True  # Основной цикл обработает завершение заказа

        if start and not pause:
            if waiting_logged:
                log_message("Перекладка возобновлена")
            return True

        if not waiting_logged:
            log_message(
                "Перекладка на паузе"
                if pause else
                "Ожидание команды START от Regul"
            )
            waiting_logged = True

        STOP_PROGRAM.wait(0.1)

    return False


def wait_for_ready_tray():
    global Cell2
    # Платы больше не берём, пока не придёт подтверждение смены четырёх ячеек.
    READY_TRAY_REPLACED.clear()
    opc_set('OPC_ready_tray_full', True)
    log_message('Готовые ячейки заполнены (4/4). Ожидание сброса OPC_ready_tray_full от ПЛК')
    while not EMERGENCY_STOP.is_set() and not STOP_PROGRAM.is_set():
        if READY_TRAY_REPLACED.wait(0.1):
            Cell2 = 0  # ВАЖНО: Cell1 не сбрасываем, продолжаем исходную тару.
            # Меняем только локальное состояние: в OPC флаг уже сброшен ПЛК.
            opc_set('OPC_ready_tray_full', False)
            log_message(f'Новые готовые ячейки приняты. Следующая исходная ячейка: {Cell1 + 1}')
            return True
    return False


def transfer_board(modbus_provider):
    global Cell, Cell1

    slot = None
    board_picked = False
    pick_started = False

    try:
        # 1. Резервируем свободную ячейку готовой тары
        slot = ready_trays.wait_and_reserve_slot(
            EMERGENCY_STOP
        )

        if slot is None:
            raise RuntimeError(
                "Ожидание свободной каретки прервано"
            )

        logger4.info(
            f"[KARETKA] Резерв: каретка {slot['cart']}, "
            f"ячейка {slot['cell']}"
        )
        # После ожидания каретки повторно проверяем START и PAUSE
        if not wait_for_start():
            raise RuntimeError(
                "Остановка во время ожидания разрешения START"
            )

        # 2. Забираем плату из исходной тары
        Cell = Cell1 + 1

        log_message(
            f"Забор платы из исходной тары, ячейка {Cell}"
        )

        pick_started = True
        if not modbus_provider._send_robot_command(211):
            raise RuntimeError(
                f"Ошибка забора платы из ячейки {Cell}"
            )

        board_picked = True

        # 3. Указываем ячейку готовой каретки
        Cell = slot['cell']

        # Проверяем состояние каретки перед укладкой
        ready_trays.check_before_placement(slot)

        log_message(
            f"Укладка платы: каретка {slot['cart']}, "
            f"ячейка {Cell}"
        )

        # 4. Укладываем плату
        if not modbus_provider._send_robot_command(241):
            raise RuntimeError(
                "Робот не подтвердил укладку 241"
            )

        # 5. Подтверждаем успешную укладку
        ready_trays.confirm_placement(slot)
        slot = None

        Cell1 += 1

        opc_set(
            'OPC_cnt_newBoard',
            NEW_BOARD_CELL_LIMIT - Cell1
        )

        opc_set('OPC_success_count', Cell1)

        log_message(
            f"Плата {Cell1} успешно переложена"
        )

        return True

    except Exception as exc:
        if slot is not None:
            try:
                if not pick_started:
                    ready_trays.cancel_before_pick(slot)
                else:
                    ready_trays.placement_failed(
                        slot,
                        f"Ошибка перекладки: {exc}"
                    )
            except Exception:
                logger4.exception(
                    "Не удалось зафиксировать ошибку каретки"
                )

        trigger_emergency(
            f"Ошибка перекладки, "
            f"плата в захвате={board_picked}: {exc}"
        )

        return False

    finally:
        Cell = 0
        modbus_provider.store.setValues(3, 8, [0])


def robo_main_cycle(modbus_provider):

    while not EMERGENCY_STOP.is_set() and not STOP_PROGRAM.is_set():

        # Проверяем завершение заказа
        with shared_data_lock:
            finish = shared_data['OPC-DB']['OPC_finish_order']

        if Cell1 >= NEW_BOARD_CELL_LIMIT or finish:
            opc_set('OPC_end_order', False)

            log_message(
                f"Перекладка завершена. "
                f"Успешно переложено плат: {Cell1}"
            )
            return

        # Ожидаем разрешение работы
        if not wait_for_start():
            return

        # Повторно проверяем завершение после ожидания
        with shared_data_lock:
            finish = shared_data['OPC-DB']['OPC_finish_order']

        if finish:
            continue

        # transfer_board сама ожидает свободную каретку,
        # резервирует ячейку и выполняет перекладку.
        if not transfer_board(modbus_provider):
            return


def main():
    
    # Одни и те же сообщения выводим в консоль и сохраняем в файл.
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - MAIN - %(levelname)s - %(message)s',
                        handlers=[logging.FileHandler('TrayTransfer.log', encoding='utf-8'),
                                  logging.StreamHandler()])
    # Убираем служебные сообщения OPC о каждом пакете; предупреждения и ошибки остаются.
    logging.getLogger('opcua').setLevel(logging.WARNING)
    logger4.info('Программа перекладки запущена: исходная тара — %s ячеек, готовая — %s',
                 NEW_BOARD_CELL_LIMIT, READY_BOARD_CELL_LIMIT)
    modbus_provider = ModbusProvider()
    opc_client = OPCClient(OPC_URL)
    logger4.info('Ожидание подключения OPC и имени оператора OPC_name: %s', OPC_URL)
    modbus_provider.server_thread.start()
    opc_client.update_thread.start()
    try:
        while not opc_client.user_ready.wait(0.1):
            if EMERGENCY_STOP.is_set():
                return
        with shared_data_lock:
            user = shared_data['OPC-DB']['OPC_name']
        SQLite.insert_log_for1C(
            description="Запущен режим Только перекладка",
            user=user
        )

        log_message('Старт режима Только перекладка')

        # Даем OPC-потоку отправить сообщение,
        # а ПЛК — обработать его
        time.sleep(2)

        if not prepare_tables(modbus_provider):
            return
        robo_main_cycle(modbus_provider)
        # После завершения сохраняем OPC-витрину и счётчики до закрытия программы.
        while not STOP_PROGRAM.is_set():

            if EMERGENCY_STOP.is_set():
                logger4.error(
                    "Аварийная остановка. Завершение программы."
                )
                break

            STOP_PROGRAM.wait(0.5)

    except KeyboardInterrupt:
        log_message('Программа остановлена оператором')
    except Exception as exc:
        trigger_emergency(str(exc))
        logger4.exception('Ошибка основного цикла')
    finally:
        STOP_PROGRAM.set()
        modbus_provider.store.setValues(3, 4, [0])
        if modbus_provider.server_thread.is_alive():
            modbus_provider.server.shutdown()
        modbus_provider.server.server_close()
        opc_client.update_thread.join(timeout=20)


if __name__ == '__main__':
    main()
