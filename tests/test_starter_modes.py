"""Проверки запуска с подменой процессов, без OPC/WMI и запуска реальных EXE."""
import ast
import csv
from pathlib import Path, PureWindowsPath
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class StarterModeTests(unittest.TestCase):
    def setUp(self):
        # Изолируем функции управления процессами: импорт стартера создаёт logs
        # и загружает платформенные WMI/COM и SQLite.
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'StrarterBotloader.py')
                         .read_text(encoding='utf-8'))
        names = {'select_work_exe', 'running_work_exes', 'is_running',
                 'start_procs_once', 'stop_procs_once', 'is_process_running', 'switch_work_mode'}
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name in names]
        self.g = dict(EXE1='hub.exe', EXE2='WORK_FILE_21_07.exe', EXE3='ServerRTK.exe',
                      EXE_DEMO='WORK_DEMO.exe', EXE_NO_TEST='WORK_FILE_TRAY_TRANSFER.exe',
                      proc1=Mock(poll=Mock(return_value=None)),
                      proc2=None, proc3=Mock(poll=Mock(return_value=None)),
                      active_work_exe=None, Path=PureWindowsPath, csv=csv,
                      subprocess=Mock(Popen=object), time=Mock(), log=Mock(), print=Mock(),
                      _popen_new_console=Mock(return_value=Mock(pid=100, poll=Mock(return_value=None))),
                      _taskkill_pid=Mock(), _taskkill_name=Mock())
        self.g['WORK_EXES'] = tuple(self.g[key] for key in ('EXE2', 'EXE_DEMO', 'EXE_NO_TEST'))
        exec(compile(ast.Module(body=functions, type_ignores=[]), '<starter-functions>', 'exec'), self.g)
        self.g['subprocess'].run.return_value = SimpleNamespace(returncode=0, stdout='', stderr='')

    def test_all_mode_combinations(self):
        for start in (False, True):
            for demo in (False, True):
                for no_test in (False, True):
                    expected = (self.g['EXE_NO_TEST'] if no_test else self.g['EXE_DEMO'] if demo
                                else self.g['EXE2'] if start else None)
                    self.assertEqual(self.g['select_work_exe'](start, demo, no_test), expected)

    def test_switch_stops_before_starting_new_mode(self):
        calls = []
        self.g['running_work_exes'] = Mock(side_effect=[[self.g['EXE2']], []])
        self.g['stop_procs_once'] = Mock(side_effect=lambda: calls.append('stop'))
        self.g['start_procs_once'] = Mock(side_effect=lambda exe: calls.append(exe))
        self.g['switch_work_mode'](self.g['EXE_DEMO'])
        self.assertEqual(calls, ['stop', self.g['EXE_DEMO']])

    def test_failed_stop_blocks_mode_switch(self):
        self.g['running_work_exes'] = Mock(return_value=[self.g['EXE2']])
        self.g['stop_procs_once'] = Mock()
        self.g['start_procs_once'] = Mock()
        with self.assertRaises(RuntimeError):
            self.g['switch_work_mode'](self.g['EXE_DEMO'])
        self.g['start_procs_once'].assert_not_called()

    def test_all_signals_off_stops(self):
        self.g['stop_procs_once'] = Mock()
        self.g['start_procs_once'] = Mock()
        self.g['switch_work_mode'](self.g['select_work_exe'](False, False, False))
        self.g['stop_procs_once'].assert_called_once_with()
        self.g['start_procs_once'].assert_not_called()

    def test_selected_exe_is_started(self):
        self.g['start_procs_once'](self.g['EXE_DEMO'])
        self.g['_popen_new_console'].assert_called_once_with(self.g['EXE_DEMO'])
        self.assertEqual(self.g['active_work_exe'], self.g['EXE_DEMO'])

    def test_no_second_worker_in_any_mode(self):
        for existing in self.g['WORK_EXES']:
            self.g['subprocess'].run.return_value.stdout = f'"{existing}","100","Console","1","100 K"'
            self.g['start_procs_once'](self.g['EXE_DEMO'])
        self.g['_popen_new_console'].assert_not_called()

    def test_repeat_start_uses_process_handle_too(self):
        self.g['start_procs_once'](self.g['EXE2'])
        self.g['start_procs_once'](self.g['EXE_NO_TEST'])
        self.g['_popen_new_console'].assert_called_once_with(self.g['EXE2'])

    def test_stop_covers_all_modes_but_preserves_server(self):
        self.g['proc2'] = Mock(pid=100, poll=Mock(return_value=None))
        self.g['stop_procs_once']()
        killed = [call.args[0] for call in self.g['_taskkill_name'].call_args_list]
        self.assertEqual(killed, [*self.g['WORK_EXES'], self.g['EXE1']])
        self.assertIsNotNone(self.g['proc3'])
        self.assertIsNone(self.g['proc2'])

    def test_tasklist_failure_blocks_launch(self):
        self.g['subprocess'].run.return_value = SimpleNamespace(returncode=1, stdout='', stderr='failed')
        with self.assertRaises(RuntimeError):
            self.g['start_procs_once'](self.g['EXE_DEMO'])
        self.g['_popen_new_console'].assert_not_called()

    def test_long_exe_name_is_detected_exactly(self):
        self.g['subprocess'].run.return_value.stdout = '"WORK_FILE_TRAY_TRANSFER.exe","10","Console","1","100 K"'
        self.assertTrue(self.g['is_process_running']('WORK_FILE_TRAY_TRANSFER.exe'))
        self.assertFalse(self.g['is_process_running']('TRANSFER.exe'))


if __name__ == '__main__':
    unittest.main()
