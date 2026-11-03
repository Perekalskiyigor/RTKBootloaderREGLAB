"""Упрощённый WORK_FILE_21_07.py: новая тара -> 4 ячейки готовой тары.

python WORK_FILE_TRAY_TRANSFER.py
Узел готовой тары: BOOL Application.UserInterface.OPC_ready_tray_full.
Python выставляет OPC_ready_tray_full, ПЛК сбрасывает его после замены готовой тары.
"""

import logging
import threading
import time

from opcua import Client, ua
from pymodbus.server.sync import ModbusTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext


# Сохраняем имена счётчиков и адреса оборудования из рабочего файла.
NEW_BOARD_CELL_LIMIT = 61
READY_BOARD_CELL_LIMIT = 4
ROBOT_TIMEOUT = 7200  # Таймаут команды как в _send_robot_command исходника.
OPC_URL = "opc.tcp://192.168.1.3:48010"
MODBUS_ADDRESS = ("192.168.1.100", 502)

Cell = 0
Cell1 = 0  # Сколько плат взято из новой тары: 0..61.
Cell2 = 0  # Сколько готовых ячеек заполнено: 0..4.
Tray_robot = 0


EMERGENCY_STOP = threading.Event()
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
        self.ready_full_sent = False
        self.nodes = {}
        self.disabled_stubs = set()
        self.update_thread = threading.Thread(target=self.update_registers, daemon=True)

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

                # Читаем те же кнопки панели, что и в основном рабочем файле.
                controls = {}
                for name in ('OPC_start_RTK', 'OPC_pause_RTK', 'OPC_restart_RTK',
                             'OPC_finish_order'):
                    value = self.node(name).get_value()
                    if not isinstance(value, bool):
                        raise ValueError(f'{name}: ожидался BOOL')
                    controls['OPC_START_RTK' if name == 'OPC_start_RTK' else name] = value

                # ВРЕМЕННЫЕ ЗАГЛУШКИ ПОСЛЕ ЧТЕНИЯ OPC: автоматический старт без паузы.
                # Для управления с панели закомментировать следующие две строки.
                controls['OPC_START_RTK'] = True
                controls['OPC_pause_RTK'] = False

                with shared_data_lock:
                    shared_data['OPC-DB'].update(controls)
                    opcdb = dict(shared_data['OPC-DB'])

                # Один флаг для запроса и подтверждения замены ГОТОВОЙ тары.
                # True пишем один раз: иначе затрём сброс False, поступивший от ПЛК.
                if not EMERGENCY_STOP.is_set():
                    if not opcdb['OPC_ready_tray_full']:
                        self.ready_full_sent = False
                    elif not self.ready_full_sent:
                        self._write('OPC_ready_tray_full', True, ua.VariantType.Boolean)
                        self.ready_full_sent = True
                    elif not READY_TRAY_REPLACED.is_set():
                        ready_full = self.node('OPC_ready_tray_full').get_value()
                        if not isinstance(ready_full, bool):
                            raise ValueError('OPC_ready_tray_full: ожидался BOOL')
                        if not ready_full:
                            READY_TRAY_REPLACED.set()
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
            except Exception as exc:
                if self.connected.is_set():
                    trigger_emergency(f'Ошибка OPC: {exc}')
                self.connected.clear()
                logger4.exception('Ошибка OPC; повтор подключения через 5 секунд')
                try:
                    self.client.disconnect()
                except Exception:
                    pass
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
        # Выходы движения столов/прошивальщиков/подготовки оставляем нулевыми.
        for address in (0, 2, 10, 12, 18, 20, 24, 25):
            self.store.setValues(3, address, [0])

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
        # Убраны только команды столов: здесь используются 210 и 241.
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


def wait_for_start():
    while not EMERGENCY_STOP.is_set() and not STOP_PROGRAM.is_set():
        with shared_data_lock:
            opcdb = shared_data['OPC-DB']
            enabled = opcdb['OPC_START_RTK'] and not opcdb['OPC_pause_RTK']
        if enabled:
            return True
        time.sleep(0.1)
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
    global Cell, Cell1, Cell2, Tray_robot
    # Вместо setup/прошивки/ложементов — только забор и сразу укладка в готовую тару.
    Cell = Cell1 + 1
    Tray_robot = 1
    log_message(f'Забор платы из новой тары, ячейка {Cell}')
    if not modbus_provider._send_robot_command(210):
        return False
    Cell1 += 1
    opc_set('OPC_cnt_newBoard', NEW_BOARD_CELL_LIMIT - Cell1)

    if not wait_for_start():
        return False
    Cell = Cell2 + 1
    Tray_robot = 2
    log_message(f'Укладка платы в готовую тару, ячейка {Cell}/4')
    if not modbus_provider._send_robot_command(241):
        return False
    Cell2 += 1  # Учитываем только подтверждённую укладку.
    opc_set('OPC_success_count', Cell1)
    Cell = 0
    Tray_robot = 0
    modbus_provider.store.setValues(3, 6, [0])
    modbus_provider.store.setValues(3, 8, [0])
    return True


def robo_main_cycle(modbus_provider):
    while not EMERGENCY_STOP.is_set() and not STOP_PROGRAM.is_set():
        if Cell2 >= READY_BOARD_CELL_LIMIT:
            if not wait_for_ready_tray():
                return
        with shared_data_lock:
            finish = shared_data['OPC-DB']['OPC_finish_order']
        if Cell1 >= NEW_BOARD_CELL_LIMIT or finish:
            opc_set('OPC_end_order', False)
            log_message(f'Перекладка завершена. Переложено плат: {Cell1}; в готовой таре: {Cell2}')
            return
        if not wait_for_start():
            return
        # Завершение могло прийти, пока оператор держал цикл на паузе.
        with shared_data_lock:
            finish = shared_data['OPC-DB']['OPC_finish_order']
        if finish:
            continue
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
    logger4.info('Активны заглушки: автоматический старт, пауза отключена')
    modbus_provider = ModbusProvider()
    opc_client = OPCClient(OPC_URL)
    logger4.info('Ожидание подключения OPC: %s', OPC_URL)
    modbus_provider.server_thread.start()
    opc_client.update_thread.start()
    try:
        while not opc_client.connected.wait(0.1):
            if EMERGENCY_STOP.is_set():
                return
        robo_main_cycle(modbus_provider)
        # После завершения сохраняем OPC-витрину и счётчики до закрытия программы.
        while not STOP_PROGRAM.wait(0.5):
            pass
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
