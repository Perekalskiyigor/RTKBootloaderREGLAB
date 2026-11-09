"""Общие готовые каретки для WORK, DEMO и TRAY_TRANSFER.

Один экземпляр ReadyTrays на процесс, общий для всех столов.
sync_opc() вызывается только из OPC-потока, с реальными read/write OPC.
Cell остаётся глобальной переменной рабочего файла, модуль её не меняет.
См. READY_TRAYS.md: порядок вызовов и пример подключения.
"""

import threading
import time


class TrayStateError(RuntimeError):
    """Состояние каретки требует остановки и проверки оператором."""


class ReadyTrays:
    def __init__(self, max_state_age=3.0):
        if max_state_age <= 0:
            raise ValueError('max_state_age должен быть положительным')
        self._max_state_age = max_state_age
        self._condition = threading.Condition()
        self._carts = {
            1: {'count': 0, 'present': False, 'phase': 'initial'},
            2: {'count': 0, 'present': False, 'phase': 'initial'},
        }
        self._active_cart = None
        self._reservation = None
        self._token = 0
        self._last_sync = None
        self._fault = None

    def _fail(self, message):
        self._fault = message
        self._condition.notify_all()
        raise TrayStateError(message)

    def _check_fault(self):
        if self._fault:
            raise TrayStateError(self._fault)

    def _fresh(self):
        return (self._last_sync is not None
                and time.monotonic() - self._last_sync <= self._max_state_age)

    def connection_lost(self):
        """Вызывать при потере OPC. Счётчики и резервирование сохраняются."""
        with self._condition:
            self._last_sync = None
            self._condition.notify_all()

    def sync_opc(self, read_bool, write_bool):
        """Один цикл обмена; исключения передаются вызывающему OPC-потоку.

        read_bool(name) -> bool: непосредственное чтение узла из ПЛК.
        write_bool(name, value): синхронная запись, ошибка должна вызывать исключение.
        Имена: OPC_karetka1, OPC_karetka2 (группа Application.UserInterface).

        После записи False возврат True читается только в СЛЕДУЮЩЕМ цикле.
        Повторно False не пишем. При ошибке записи результат неопределён:
        фиксируем неисправность, чтобы не отправить уже вернувшуюся каретку.
        """
        with self._condition:
            self._check_fault()
            try:
                values = {n: read_bool(f'OPC_karetka{n}') for n in (1, 2)}
                if any(type(value) is not bool for value in values.values()):
                    raise ValueError('OPC_karetka1/2 должны иметь тип BOOL')

                for n, cart in self._carts.items():
                    value = values[n]
                    reserved = self._reservation is not None and self._reservation['cart'] == n
                    if cart['phase'] == 'initial':
                        # Первый True означает пустую каретку по контракту запуска.
                        cart['phase'] = 'filling' if value else 'away'
                        cart['present'] = value
                    elif cart['phase'] == 'away':
                        cart['present'] = value
                        if value:
                            cart['count'] = 0
                            cart['phase'] = 'filling'
                    elif cart['phase'] == 'filling':
                        if not value and (cart['count'] or reserved):
                            self._fail(f'Каретка {n} ушла до завершения заполнения')
                        cart['present'] = value
                        if not value:
                            cart['phase'] = 'away'
                    elif cart['phase'] == 'pending_send':
                        # Эта каретка уже локально недоступна, старый True игнорируем.
                        try:
                            write_bool(f'OPC_karetka{n}', False)
                        except Exception as exc:
                            self._fail(f'Неизвестен результат отправки каретки {n}: {exc}')
                        cart['phase'] = 'away'
                        cart['present'] = False

                self._last_sync = time.monotonic()
            except Exception:
                self._last_sync = None
                raise
            finally:
                self._condition.notify_all()

    def wait_and_reserve_slot(self, stop_event, timeout=None):
        """Возвращает словарь {'cart', 'cell', 'token'} или None при останове/таймауте.

        Одновременно выдаётся один резерв: робот и глобальная Cell общие.
        stop_event должен отражать как аварийный, так и штатный останов алгоритма.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        with self._condition:
            while True:
                if stop_event.is_set():
                    return None
                self._check_fault()
                if self._fresh() and self._reservation is None:
                    order = [1, 2]
                    if self._active_cart == 2:
                        order = [2, 1]
                    for n in order:
                        cart = self._carts[n]
                        if cart['phase'] == 'filling' and cart['present'] and cart['count'] < 4:
                            self._token += 1
                            slot = {'cart': n, 'cell': (n - 1) * 4 + cart['count'] + 1,
                                    'token': self._token}
                            self._reservation = slot.copy()
                            self._active_cart = n
                            return slot
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    return None
                self._condition.wait(0.1 if remaining is None else min(0.1, remaining))

    def _validate_slot(self, slot):
        self._check_fault()
        if self._reservation is None or slot != self._reservation:
            raise ValueError('Ячейка не зарезервирована или резерв уже завершён')

    def check_before_placement(self, slot):
        """Проверка непосредственно перед командой укладки роботу."""
        with self._condition:
            self._validate_slot(slot)
            if not self._fresh():
                raise TrayStateError('Нет свежих данных OPC о каретках')
            cart = self._carts[slot['cart']]
            if cart['phase'] != 'filling' or not cart['present']:
                self._fail(f"Каретка {slot['cart']} недоступна для укладки")

    def confirm_placement(self, slot):
        """Вызывать ТОЛЬКО после подтверждения роботом успешной укладки."""
        with self._condition:
            self._validate_slot(slot)
            cart = self._carts[slot['cart']]
            cart['count'] += 1
            self._reservation = None
            if cart['count'] == 4:
                cart['phase'] = 'pending_send'
                cart['present'] = False
                self._active_cart = None
            self._condition.notify_all()

    def cancel_before_pick(self, slot):
        """Отмена только если плата ещё НЕ взята и движение НЕ начиналось."""
        with self._condition:
            self._validate_slot(slot)
            self._reservation = None
            self._condition.notify_all()

    def placement_failed(self, slot, reason):
        """Неизвестное положение платы: резерв сохраняется, новые выдачи запрещены."""
        with self._condition:
            self._validate_slot(slot)
            self._fail(f"Ошибка укладки в ячейку {slot['cell']}: {reason}")
