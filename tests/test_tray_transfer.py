import unittest
from unittest.mock import Mock, patch

import WORK_FILE_TRAY_TRANSFER as app


class TransferTests(unittest.TestCase):
    def setUp(self):
        app.Cell = app.Cell1 = app.Cell2 = 0
        app.Tray_robot = 2
        app.EMERGENCY_STOP.clear()
        app.READY_TRAY_REPLACED.clear()
        app.STOP_PROGRAM.clear()
        app.shared_data['OPC-DB'].update(OPC_START_RTK=True, OPC_pause_RTK=False,
                                         OPC_finish_order=False, OPC_ready_tray_full=False)
        self.bus = Mock()
        self.commands = []

        def command(value):
            self.commands.append((value, app.Tray_robot, app.Cell))
            return True

        self.bus._send_robot_command.side_effect = command

    def test_61_boards_in_groups_of_four(self):
        batches = []

        def acknowledge(timeout):
            self.assertTrue(app.shared_data['OPC-DB']['OPC_ready_tray_full'])
            self.assertEqual(app.Cell2, 4)
            batches.append(app.Cell1)
            return True

        with patch.object(app.READY_TRAY_REPLACED, 'wait', side_effect=acknowledge):
            app.robo_main_cycle(self.bus)
        expected = [command for cell in range(1, 62)
                    for command in ((211, 2, cell), (241, 2, (cell - 1) % 4 + 1))]
        self.assertEqual(self.commands, expected)
        self.assertEqual(batches, list(range(4, 61, 4)))
        self.assertEqual((app.Cell1, app.Cell2), (61, 1))
        self.assertEqual(app.Tray_robot, 2)
        self.assertTrue(all(call.args[1] != 6 for call in self.bus.store.setValues.call_args_list))
        self.assertFalse(app.shared_data['OPC-DB']['OPC_end_order'])

    def test_full_tray_blocks_next_pick(self):
        app.Cell1 = app.Cell2 = 4

        def stop_without_ack(timeout):
            app.EMERGENCY_STOP.set()
            return False

        with patch.object(app.READY_TRAY_REPLACED, 'wait', side_effect=stop_without_ack):
            app.robo_main_cycle(self.bus)
        self.assertEqual(self.commands, [])
        self.assertEqual((app.Cell1, app.Cell2), (4, 4))
        self.assertTrue(app.shared_data['OPC-DB']['OPC_ready_tray_full'])

    def test_failed_place_does_not_increment_ready_count(self):
        self.bus._send_robot_command.side_effect = [True, False]
        self.assertFalse(app.transfer_board(self.bus))
        self.assertEqual((app.Cell1, app.Cell2), (1, 0))

    def test_failed_pick_does_not_place(self):
        self.bus._send_robot_command.side_effect = [False]
        self.assertFalse(app.transfer_board(self.bus))
        self.assertEqual((app.Cell1, app.Cell2), (0, 0))
        self.bus._send_robot_command.assert_called_once_with(211)

    def test_finish_requested_during_pick_still_places_board(self):
        def command(value):
            self.commands.append(value)
            if value == 211:
                app.opc_set('OPC_finish_order', True)
            return True

        self.bus._send_robot_command.side_effect = command
        app.robo_main_cycle(self.bus)
        self.assertEqual(self.commands, [211, 241])
        self.assertEqual(app.Cell2, 1)

    def test_opc_waits_for_plc_to_clear_full_flag_without_overwriting_it(self):
        with patch.object(app, 'Client'):
            opc = app.OPCClient('opc.tcp://unused')
        opc.connected.set()
        opc._write_stub = Mock()
        controls = dict.fromkeys(('OPC_start_RTK', 'OPC_pause_RTK', 'OPC_restart_RTK',
                                  'OPC_finish_order', 'OPC_ready_tray_full'), False)
        def write(name, value, vtype):
            if name == 'OPC_ready_tray_full':
                controls[name] = value
        opc._write = Mock(side_effect=write)
        opc.node = lambda name: Mock(get_value=lambda: controls[name])

        def poll():
            app.STOP_PROGRAM.clear()
            with patch.object(app.STOP_PROGRAM, 'wait', side_effect=lambda _: app.STOP_PROGRAM.set()):
                opc.update_registers()

        # Исходный False не является подтверждением: сначала отправляем True.
        poll()
        self.assertFalse(app.READY_TRAY_REPLACED.is_set())
        app.opc_set('OPC_ready_tray_full', True)
        poll()
        self.assertTrue(controls['OPC_ready_tray_full'])
        self.assertFalse(app.READY_TRAY_REPLACED.is_set())
        poll()
        self.assertFalse(app.READY_TRAY_REPLACED.is_set())
        controls['OPC_ready_tray_full'] = False  # ПЛК предоставил пустые ячейки.
        poll()
        self.assertTrue(app.READY_TRAY_REPLACED.is_set())
        self.assertFalse(controls['OPC_ready_tray_full'])
        poll()
        full_writes = [call for call in opc._write.call_args_list
                       if call.args[0] == 'OPC_ready_tray_full']
        self.assertEqual(len(full_writes), 1)
        # После обработки подтверждения следующий набор из четырёх запрашивается заново.
        app.opc_set('OPC_ready_tray_full', False)
        poll()
        app.READY_TRAY_REPLACED.clear()
        app.opc_set('OPC_ready_tray_full', True)
        poll()
        self.assertTrue(controls['OPC_ready_tray_full'])
        self.assertFalse(app.READY_TRAY_REPLACED.is_set())

    def test_modbus_error_clears_command(self):
        bus = app.ModbusProvider.__new__(app.ModbusProvider)
        bus.store = Mock()
        bus.store.getValues.return_value = [404]
        with patch.object(app.time, 'sleep'):
            self.assertFalse(bus._send_robot_command(211))
        self.assertTrue(app.EMERGENCY_STOP.is_set())
        self.assertEqual(bus.store.setValues.call_args.args, (3, 4, [0]))


if __name__ == '__main__':
    unittest.main()
