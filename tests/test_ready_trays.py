import threading
import unittest

from ReadyTrays import ReadyTrays, TrayStateError


class ReadyTraysTests(unittest.TestCase):
    def setUp(self):
        self.manager = ReadyTrays()
        self.stop = threading.Event()
        self.values = {'OPC_karetka1': True, 'OPC_karetka2': True}
        self.writes = []
        self.sync()

    def write(self, name, value):
        self.writes.append((name, value))
        self.values[name] = value

    def sync(self):
        self.manager.sync_opc(self.values.__getitem__, self.write)

    def reserve(self):
        return self.manager.wait_and_reserve_slot(self.stop, timeout=0)

    def place(self, cell):
        slot = self.reserve()
        self.assertEqual(slot['cell'], cell)
        self.manager.check_before_placement(slot)
        self.manager.confirm_placement(slot)

    def test_two_carts_dispatch_and_return(self):
        for cell in range(1, 5):
            self.place(cell)
        self.assertEqual(self.writes, [])
        self.sync()
        self.assertEqual(self.writes, [('OPC_karetka1', False)])
        self.place(5)
        self.values['OPC_karetka1'] = True
        self.sync()
        # Возврат первой не прерывает заполнение второй.
        for cell in range(6, 9):
            self.place(cell)
        self.sync()
        self.assertEqual(self.writes, [('OPC_karetka1', False), ('OPC_karetka2', False)])
        self.place(1)
        self.sync()
        self.assertEqual(len(self.writes), 2)

    def test_old_true_does_not_reset_full_cart(self):
        self.values['OPC_karetka2'] = False
        self.sync()
        for cell in range(1, 5):
            self.place(cell)
        self.sync()  # Прочитан старый True; затем записан False.
        self.assertIsNone(self.reserve())
        self.sync()
        self.assertIsNone(self.reserve())
        self.values['OPC_karetka1'] = True
        self.sync()
        self.assertEqual(self.reserve()['cell'], 1)

    def test_only_one_table_can_reserve_global_cell(self):
        slot = self.reserve()
        self.assertIsNone(self.reserve())
        self.manager.cancel_before_pick(slot)
        next_slot = self.reserve()
        self.assertEqual(next_slot['cell'], slot['cell'])
        with self.assertRaises(ValueError):
            self.manager.confirm_placement(slot)

    def test_disconnect_blocks_placement_and_preserves_reservation(self):
        slot = self.reserve()
        self.manager.connection_lost()
        with self.assertRaises(TrayStateError):
            self.manager.check_before_placement(slot)
        self.assertIsNone(self.reserve())
        self.sync()
        self.manager.check_before_placement(slot)

    def test_departure_during_operation_is_latched_fault(self):
        self.reserve()
        self.values['OPC_karetka1'] = False
        with self.assertRaises(TrayStateError):
            self.sync()
        with self.assertRaises(TrayStateError):
            self.reserve()

    def test_uncertain_write_is_not_repeated(self):
        for cell in range(1, 5):
            self.place(cell)

        def uncertain_write(name, value):
            self.write(name, value)
            raise TimeoutError('response lost')

        with self.assertRaises(TrayStateError):
            self.manager.sync_opc(self.values.__getitem__, uncertain_write)
        self.values['OPC_karetka1'] = True
        with self.assertRaises(TrayStateError):
            self.sync()
        self.assertEqual(len(self.writes), 1)

    def test_stop_interrupts_wait(self):
        self.stop.set()
        self.assertIsNone(self.manager.wait_and_reserve_slot(self.stop))


if __name__ == '__main__':
    unittest.main()
