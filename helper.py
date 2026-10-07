#python -m PyInstaller --onefile helper.py 
import os
import sqlite3
import subprocess
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from SentLog1C import send_success_log, send_unsuccess_log

      
# ============================================================
# НАСТРОЙКИ
# ============================================================

DEFAULT_DB_PATH = r"e:\DEV\RTKBootloader\orders.db"


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def normalize_serial(value: str) -> str:
    """
    Сканер присылает, например:
        U00072570B

    В базе хранится:
        U00072570

    Поэтому последнюю букву убираем.
    """

    value = value.strip().upper()

    if value and value[-1].isalpha():
        value = value[:-1]

    return value


def open_path(path: str):
    """
    Открытие файла или папки.
    """

    if not path:
        raise ValueError("Путь пустой")

    path = path.strip().strip('"')

    if sys.platform.startswith("win"):
        os.startfile(path)

    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])

    else:
        subprocess.Popen(["xdg-open", path])


# ============================================================
# ОСНОВНОЕ ПРИЛОЖЕНИЕ
# ============================================================

class OrdersApp(tk.Tk):

    def __init__(self):
        super().__init__()

        self.title("Orders — обслуживание плат")
        self.geometry("1250x850")
        self.minsize(950, 650)

        self.db_path = tk.StringVar(
            value=DEFAULT_DB_PATH
        )

        self.order_by_display = {}

        self.current_log_path = None
        self.manual_send_running = False

        self.create_ui()

        if os.path.isfile(
            self.db_path.get()
        ):
            self.after(
                200,
                self.refresh_orders
            )

    # ========================================================
    # БАЗА
    # ========================================================

    def get_connection(self):

        path = self.db_path.get().strip()

        if not path:
            raise RuntimeError(
                "Не указан путь к базе"
            )

        if not os.path.isfile(path):
            raise FileNotFoundError(
                f"Файл базы не найден:\n{path}"
            )

        conn = sqlite3.connect(
            path,
            timeout=10
        )

        conn.row_factory = sqlite3.Row

        return conn

    # ========================================================
    # ОБЩИЙ ИНТЕРФЕЙС
    # ========================================================

    def create_ui(self):

        main_frame = ttk.Frame(
            self,
            padding=10
        )

        main_frame.pack(
            fill="both",
            expand=True
        )

        # ----------------------------------------------------
        # База
        # ----------------------------------------------------

        db_frame = ttk.LabelFrame(
            main_frame,
            text="База данных"
        )

        db_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        self.db_entry = ttk.Entry(
            db_frame,
            textvariable=self.db_path
        )

        self.db_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(10, 5),
            pady=10
        )

        ttk.Button(
            db_frame,
            text="Выбрать...",
            command=self.choose_database
        ).pack(
            side="left",
            padx=5
        )

        ttk.Button(
            db_frame,
            text="Подключить / обновить",
            command=self.refresh_orders
        ).pack(
            side="left",
            padx=(5, 10)
        )

        # ----------------------------------------------------
        # Вкладки
        # ----------------------------------------------------

        self.notebook = ttk.Notebook(
            main_frame
        )

        self.notebook.pack(
            fill="both",
            expand=True
        )

        self.reset_tab = ttk.Frame(
            self.notebook,
            padding=10
        )

        self.status_tab = ttk.Frame(
            self.notebook,
            padding=10
        )

        self.manual_1c_tab = ttk.Frame(
            self.notebook,
            padding=10
        )

        self.notebook.add(
            self.reset_tab,
            text="Повторная прошивка / сброс"
        )

        self.notebook.add(
            self.status_tab,
            text="Статус платы"
        )

        self.notebook.add(
            self.manual_1c_tab,
            text="Ручная отправка в 1С"
        )

        self.create_reset_tab()
        self.create_status_tab()
        self.create_manual_1c_tab()

    # ========================================================
    # ВКЛАДКА 1
    # ========================================================

    def create_reset_tab(self):

        # ----------------------------------------------------
        # Выбор заказа
        # ----------------------------------------------------

        order_frame = ttk.LabelFrame(
            self.reset_tab,
            text="1. Выбор заказа"
        )

        order_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Label(
            order_frame,
            text="Заказ:"
        ).grid(
            row=0,
            column=0,
            padx=(10, 5),
            pady=10,
            sticky="w"
        )

        self.order_combo = ttk.Combobox(
            order_frame,
            state="readonly"
        )

        self.order_combo.grid(
            row=0,
            column=1,
            padx=5,
            pady=10,
            sticky="ew"
        )

        self.order_combo.bind(
            "<<ComboboxSelected>>",
            self.on_order_selected
        )

        ttk.Button(
            order_frame,
            text="Обновить список",
            command=self.refresh_orders
        ).grid(
            row=0,
            column=2,
            padx=(5, 10),
            pady=10
        )

        order_frame.columnconfigure(
            1,
            weight=1
        )

        self.order_info_label = ttk.Label(
            order_frame,
            text="Заказ не выбран",
            wraplength=1100
        )

        self.order_info_label.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            padx=10,
            pady=(0, 10)
        )

        # ----------------------------------------------------
        # Сканирование
        # ----------------------------------------------------

        scan_frame = ttk.LabelFrame(
            self.reset_tab,
            text="2. Сканирование плат"
        )

        scan_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Label(
            scan_frame,
            text=(
                "Сканируйте платы подряд. "
                "Каждый номер должен завершаться Enter.\n"
                "Например U00072570B будет обработан как U00072570."
            )
        ).pack(
            anchor="w",
            padx=10,
            pady=(10, 5)
        )

        text_frame = ttk.Frame(
            scan_frame
        )

        text_frame.pack(
            fill="x",
            padx=10,
            pady=(0, 5)
        )

        self.serial_text = tk.Text(
            text_frame,
            height=10,
            wrap="none",
            font=("Consolas", 13)
        )

        self.serial_text.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=self.serial_text.yview
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.serial_text.configure(
            yscrollcommand=scrollbar.set
        )

        self.serial_text.bind(
            "<KeyRelease>",
            self.on_serial_text_change
        )

        # ----------------------------------------------------
        # Счетчик
        # ----------------------------------------------------

        control_frame = ttk.Frame(
            scan_frame
        )

        control_frame.pack(
            fill="x",
            padx=10,
            pady=(0, 10)
        )

        self.serial_count_label = ttk.Label(
            control_frame,
            text="Уникальных плат: 0"
        )

        self.serial_count_label.pack(
            side="left"
        )

        ttk.Button(
            control_frame,
            text="Очистить список",
            command=self.clear_serials
        ).pack(
            side="right"
        )

        # ----------------------------------------------------
        # КНОПКА ВЫПОЛНЕНИЯ
        # ----------------------------------------------------

        action_frame = ttk.LabelFrame(
            self.reset_tab,
            text="3. Выполнение"
        )

        action_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        self.reset_button = ttk.Button(
            action_frame,
            text="ВЫПОЛНИТЬ СБРОС ДАННЫХ",
            command=self.reset_selected_boards
        )

        self.reset_button.pack(
            fill="x",
            padx=10,
            pady=10,
            ipady=8
        )

        # ----------------------------------------------------
        # РЕЗУЛЬТАТ
        # ----------------------------------------------------

        result_frame = ttk.LabelFrame(
            self.reset_tab,
            text="Результат"
        )

        result_frame.pack(
            fill="both",
            expand=True
        )

        self.reset_result_text = tk.Text(
            result_frame,
            height=10,
            font=("Consolas", 11),
            state="disabled"
        )

        self.reset_result_text.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

    # ========================================================
    # ВКЛАДКА 2
    # ========================================================

    def create_status_tab(self):

        # ----------------------------------------------------
        # Поиск
        # ----------------------------------------------------

        search_frame = ttk.LabelFrame(
            self.status_tab,
            text="Поиск платы"
        )

        search_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Label(
            search_frame,
            text="Номер платы:"
        ).pack(
            side="left",
            padx=(10, 5),
            pady=10
        )

        self.status_serial_var = tk.StringVar()

        self.status_serial_entry = ttk.Entry(
            search_frame,
            textvariable=self.status_serial_var,
            font=("Consolas", 13)
        )

        self.status_serial_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=5,
            pady=10
        )

        self.status_serial_entry.bind(
            "<Return>",
            lambda event: self.find_board_status()
        )

        ttk.Button(
            search_frame,
            text="Найти",
            command=self.find_board_status
        ).pack(
            side="left",
            padx=(5, 10)
        )

        # ----------------------------------------------------
        # Результат
        # ----------------------------------------------------

        result_frame = ttk.LabelFrame(
            self.status_tab,
            text="Статус платы"
        )

        result_frame.pack(
            fill="both",
            expand=True
        )

        content = ttk.Frame(
            result_frame,
            padding=15
        )

        content.pack(
            fill="both",
            expand=True
        )

        content.columnconfigure(
            1,
            weight=1
        )

        self.status_labels = {}

        fields = [
            ("order_id", "Order ID"),
            ("serial_number", "Serial number"),
            ("user", "User"),
            ("test_result", "Test result"),
            ("report_path", "Report path"),
        ]

        row_index = 0

        for field, title in fields:

            ttk.Label(
                content,
                text=f"{title}:"
            ).grid(
                row=row_index,
                column=0,
                sticky="nw",
                padx=(0, 15),
                pady=8
            )

            label = ttk.Label(
                content,
                text="-",
                wraplength=800,
                justify="left"
            )

            label.grid(
                row=row_index,
                column=1,
                sticky="nw",
                pady=8
            )

            self.status_labels[field] = label

            row_index += 1

        # ----------------------------------------------------
        # log_path
        # ----------------------------------------------------

        ttk.Label(
            content,
            text="Log path:"
        ).grid(
            row=row_index,
            column=0,
            sticky="nw",
            padx=(0, 15),
            pady=8
        )

        self.log_path_label = tk.Label(
            content,
            text="-",
            fg="blue",
            cursor="hand2",
            font=("Segoe UI", 10, "underline"),
            anchor="w",
            justify="left",
            wraplength=800
        )

        self.log_path_label.grid(
            row=row_index,
            column=1,
            sticky="nw",
            pady=8
        )

        self.log_path_label.bind(
            "<Button-1>",
            self.open_log_path
        )

        row_index += 1

        self.status_message_label = ttk.Label(
            content,
            text=""
        )

        self.status_message_label.grid(
            row=row_index,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(15, 0)
        )

    # ========================================================
    # ВКЛАДКА 3 — РУЧНАЯ ОТПРАВКА В 1С
    # ========================================================

    def create_manual_1c_tab(self):

        order_frame = ttk.LabelFrame(
            self.manual_1c_tab,
            text="1. Выбор заказа"
        )
        order_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Label(
            order_frame,
            text="Заказ:"
        ).grid(
            row=0,
            column=0,
            padx=(10, 5),
            pady=10,
            sticky="w"
        )

        self.manual_order_combo = ttk.Combobox(
            order_frame,
            state="readonly"
        )
        self.manual_order_combo.grid(
            row=0,
            column=1,
            padx=5,
            pady=10,
            sticky="ew"
        )
        self.manual_order_combo.bind(
            "<<ComboboxSelected>>",
            self.on_manual_order_selected
        )

        ttk.Button(
            order_frame,
            text="Обновить список",
            command=self.refresh_orders
        ).grid(
            row=0,
            column=2,
            padx=(5, 10),
            pady=10
        )

        order_frame.columnconfigure(
            1,
            weight=1
        )

        self.manual_order_info_label = ttk.Label(
            order_frame,
            text="Заказ не выбран",
            wraplength=1100
        )
        self.manual_order_info_label.grid(
            row=1,
            column=0,
            columnspan=3,
            sticky="w",
            padx=10,
            pady=(0, 10)
        )

        action_frame = ttk.LabelFrame(
            self.manual_1c_tab,
            text="2. Отправка"
        )
        action_frame.pack(
            fill="x",
            pady=(0, 10)
        )

        ttk.Label(
            action_frame,
            text=(
                "Будут отправлены платы выбранного заказа: "
                "test_result = 1 — успешно, error = 0; "
                "test_result = 404 — брак прошивки, error = 2. "
                "Номер платы берётся только из data_matrix. "
                "Между платами выдерживается пауза 1 секунда."
            ),
            wraplength=1100
        ).pack(
            anchor="w",
            padx=10,
            pady=(10, 5)
        )

        self.manual_send_button = ttk.Button(
            action_frame,
            text="НАЧАТЬ ОТПРАВКУ В 1С",
            command=self.start_manual_1c_send
        )
        self.manual_send_button.pack(
            fill="x",
            padx=10,
            pady=(5, 10),
            ipady=8
        )

        log_frame = ttk.LabelFrame(
            self.manual_1c_tab,
            text="Лог ручной отправки"
        )
        log_frame.pack(
            fill="both",
            expand=True
        )

        text_frame = ttk.Frame(
            log_frame
        )
        text_frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )

        self.manual_1c_log_text = tk.Text(
            text_frame,
            height=20,
            wrap="word",
            font=("Consolas", 11),
            state="disabled"
        )
        self.manual_1c_log_text.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar = ttk.Scrollbar(
            text_frame,
            orient="vertical",
            command=self.manual_1c_log_text.yview
        )
        scrollbar.pack(
            side="right",
            fill="y"
        )

        self.manual_1c_log_text.configure(
            yscrollcommand=scrollbar.set
        )

    def on_manual_order_selected(self, event=None):

        display = self.manual_order_combo.get()

        if not display:
            self.manual_order_info_label.config(
                text="Заказ не выбран"
            )
            return

        row = self.order_by_display.get(display)

        if not row:
            return

        info = (
            f"ID: {row['id']}    "
            f"Order: {row['order_number']}    "
            f"Module: {row['module']}    "
            f"Nomenclature: {row['Nomenclature']}"
        )

        self.manual_order_info_label.config(
            text=info
        )

    def get_selected_manual_order(self):

        display = self.manual_order_combo.get()

        if not display:
            return None

        return self.order_by_display.get(display)

    def append_manual_1c_log(self, text):

        def _append():

            self.manual_1c_log_text.config(
                state="normal"
            )

            stamp = time.strftime("%H:%M:%S")

            self.manual_1c_log_text.insert(
                "end",
                f"[{stamp}] {text}\n"
            )

            self.manual_1c_log_text.see(
                "end"
            )

            self.manual_1c_log_text.config(
                state="disabled"
            )

        self.after(0, _append)

    @staticmethod
    def _manual_rtk_id(stand_id):

        if stand_id is None:
            return "RTK_R050_BoardsIO_1"

        value = str(stand_id).strip()

        if not value:
            return "RTK_R050_BoardsIO_1"

        if value.upper().startswith("RTK_"):
            return value

        if value.isdigit():
            return f"RTK_R050_BoardsIO_{value}"

        return value

    @staticmethod
    def _first_not_empty(row, *fields):

        for field in fields:
            try:
                value = row[field]
            except (IndexError, KeyError):
                continue

            if value is not None and str(value).strip():
                return value

        return None

    def build_manual_board_dict(self, board_row, order_row):

        board_number = board_row["data_matrix"]

        if board_number is None or not str(board_number).strip():
            raise ValueError(
                f"ID {board_row['id']}: data_matrix пустой"
            )

        operator = (
            self._first_not_empty(
                board_row,
                "user"
            )
            or ""
        )

        timestamps = {}

        dm_time = self._first_not_empty(
            board_row,
            "date_sent",
            "started_at",
            "date_added"
        )
        firmware_time = self._first_not_empty(
            board_row,
            "finished_at"
        )
        output_time = self._first_not_empty(
            board_row,
            "finished_at"
        )

        if dm_time is not None:
            timestamps["dm_code_time"] = str(dm_time)

        if firmware_time is not None:
            timestamps["firmware_finished_time"] = str(firmware_time)

        if output_time is not None:
            timestamps["board_output_time"] = str(output_time)

        version = (
            self._first_not_empty(
                order_row,
                "fw_version",
                "VersionLoadFile"
            )
            or ""
        )

        common = {
            "rtk_id": self._manual_rtk_id(
                board_row["stand_id"]
            ),
            "order": str(order_row["order_number"]),
            "version": str(version),
            "message_type": "firmware_log"
        }

        test_result = str(
            board_row["test_result"]
        ).strip()

        if test_result == "1":

            common["good"] = [
                {
                    "board": {
                        "number": str(board_number),
                        "tray_number": (
                            str(board_row["table_no"])
                            if board_row["table_no"] is not None
                            else None
                        )
                    },
                    "operator": str(operator),
                    "error": 0,
                    "timestamps": timestamps
                }
            ]
            common["bad"] = []

            return common

        if test_result == "404":

            common["good"] = []
            common["bad"] = [
                {
                    "board": {
                        "number": str(board_number),
                        "tray_number": (
                            str(board_row["table_no"])
                            if board_row["table_no"] is not None
                            else None
                        )
                    },
                    "operator": str(operator),
                    "error": 2,
                    "timestamps": timestamps,
                    "full_log_path": (
                        str(board_row["log_path"])
                        if board_row["log_path"]
                        else ""
                    )
                }
            ]

            return common

        raise ValueError(
            f"ID {board_row['id']}: неподдерживаемый test_result={test_result}"
        )

    def start_manual_1c_send(self):

        if self.manual_send_running:
            messagebox.showinfo(
                "1С",
                "Ручная отправка уже выполняется"
            )
            return

        order_row = self.get_selected_manual_order()

        if order_row is None:
            messagebox.showwarning(
                "Заказ",
                "Выберите заказ"
            )
            return

        order_id = order_row["id"]
        order_number = order_row["order_number"]

        sql = """
            SELECT
                id,
                date_added,
                order_id,
                stand_id,
                serial_number_8,
                data_matrix,
                ERPMatrix,
                date_sent,
                user,
                test_result,
                log_path,
                serial_number_9,
                serial_number_15,
                serial_number,
                table_no,
                started_at,
                finished_at
            FROM order_details
            WHERE order_id = ?
              AND CAST(test_result AS TEXT) IN ('1', '404')
            ORDER BY id ASC;
        """

        try:

            with self.get_connection() as conn:

                rows = conn.execute(
                    sql,
                    (order_id,)
                ).fetchall()

        except Exception as exc:

            messagebox.showerror(
                "Ошибка базы",
                str(exc)
            )
            return

        if not rows:

            messagebox.showinfo(
                "1С",
                (
                    f"В заказе {order_number} нет плат "
                    f"с test_result = 1 или 404"
                )
            )
            return

        answer = messagebox.askyesno(
            "Ручная отправка в 1С",
            (
                f"Заказ: {order_number}\n"
                f"ID: {order_id}\n"
                f"Плат к отправке: {len(rows)}\n\n"
                f"Начать ручную отправку в 1С?"
            )
        )

        if not answer:
            return

        self.manual_1c_log_text.config(
            state="normal"
        )
        self.manual_1c_log_text.delete(
            "1.0",
            "end"
        )
        self.manual_1c_log_text.config(
            state="disabled"
        )

        self.manual_send_running = True
        self.manual_send_button.config(
            state="disabled"
        )

        self.append_manual_1c_log(
            (
                f"Начата ручная отправка заказа "
                f"{order_number}. Записей: {len(rows)}"
            )
        )

        worker = threading.Thread(
            target=self._manual_1c_worker,
            args=(
                list(rows),
                dict(order_row)
            ),
            daemon=True
        )
        worker.start()

    def _manual_1c_worker(self, rows, order_row):

        order_number = order_row["order_number"]

        success_count = 0
        error_count = 0

        try:

            for index, board_row in enumerate(
                rows,
                start=1
            ):

                row_id = board_row["id"]

                try:

                    board_dict = self.build_manual_board_dict(
                        board_row,
                        order_row
                    )

                    board_number = (
                        board_dict["good"][0]["board"]["number"]
                        if board_dict["good"]
                        else board_dict["bad"][0]["board"]["number"]
                    )

                    test_result = str(
                        board_row["test_result"]
                    ).strip()

                    self.append_manual_1c_log(
                        (
                            f"{index}/{len(rows)} | "
                            f"ID {row_id} | "
                            f"{board_number} | "
                            f"отправка..."
                        )
                    )

                    if test_result == "1":
                        response = send_success_log(
                            board_dict
                        )
                        result_name = "УСПЕХ"
                    else:
                        response = send_unsuccess_log(
                            board_dict
                        )
                        result_name = "БРАК 404"

                    if response is None:
                        error_count += 1
                        self.append_manual_1c_log(
                            (
                                f"ID {row_id} | "
                                f"{board_number} | "
                                f"ОШИБКА отправки в 1С"
                            )
                        )
                    else:
                        success_count += 1
                        self.append_manual_1c_log(
                            (
                                f"ID {row_id} | "
                                f"{board_number} | "
                                f"отправлена в 1С — {result_name}"
                            )
                        )

                except Exception as exc:

                    error_count += 1

                    self.append_manual_1c_log(
                        (
                            f"ID {row_id} | "
                            f"ОШИБКА: {exc}"
                        )
                    )

                if index < len(rows):
                    time.sleep(1)

        finally:

            if error_count == 0:

                final_text = (
                    f"Лог по заказу {order_number} "
                    f"успешно отправлен в 1С "
                    f"в ручном режиме. "
                    f"Отправлено записей: {success_count}."
                )

            else:

                final_text = (
                    f"Ручная отправка заказа {order_number} завершена. "
                    f"Успешно: {success_count}, ошибок: {error_count}."
                )

            self.append_manual_1c_log(
                final_text
            )

            def _finish():

                self.manual_send_running = False
                self.manual_send_button.config(
                    state="normal"
                )

                if error_count == 0:
                    messagebox.showinfo(
                        "1С",
                        final_text
                    )
                else:
                    messagebox.showwarning(
                        "1С",
                        final_text
                    )

            self.after(
                0,
                _finish
            )


    # ========================================================
    # ВЫБОР БАЗЫ
    # ========================================================

    def choose_database(self):

        path = filedialog.askopenfilename(
            title="Выберите orders.db",
            filetypes=[
                (
                    "SQLite database",
                    "*.db *.sqlite *.sqlite3"
                ),
                (
                    "Все файлы",
                    "*.*"
                )
            ]
        )

        if not path:
            return

        self.db_path.set(path)

        self.refresh_orders()

    # ========================================================
    # ЗАГРУЗКА ЗАКАЗОВ
    # ========================================================

    def refresh_orders(self):

        sql = """
            SELECT id,
                   time_added,
                   order_number,
                   module,
                   Nomenclature,
                   Value,
                   VersionLoadFile,
                   fw_version,
                   marking_templates
            FROM Orders
            ORDER BY id DESC;
        """

        try:

            with self.get_connection() as conn:

                rows = conn.execute(
                    sql
                ).fetchall()

        except Exception as exc:

            messagebox.showerror(
                "Ошибка базы",
                str(exc)
            )

            return

        self.order_by_display.clear()

        values = []

        for row in rows:

            display = (
                f"ID {row['id']} | "
                f"заказ {row['order_number']} | "
                f"{row['module']} | "
                f"{row['Nomenclature']}"
            )

            values.append(display)

            self.order_by_display[
                display
            ] = row

        self.order_combo[
            "values"
        ] = values

        self.manual_order_combo[
            "values"
        ] = values

        if values:

            self.order_combo.current(0)
            self.manual_order_combo.current(0)

            self.on_order_selected()
            self.on_manual_order_selected()

    # ========================================================
    # ВЫБОР ЗАКАЗА
    # ========================================================

    def on_order_selected(
        self,
        event=None
    ):

        display = self.order_combo.get()

        if not display:
            return

        row = self.order_by_display.get(
            display
        )

        if not row:
            return

        info = (
            f"ID: {row['id']}    "
            f"Order: {row['order_number']}    "
            f"Module: {row['module']}    "
            f"Nomenclature: {row['Nomenclature']}"
        )

        self.order_info_label.config(
            text=info
        )

    # ========================================================
    # ПОЛУЧИТЬ ID ЗАКАЗА
    # ========================================================

    def get_selected_order_id(self):

        display = self.order_combo.get()

        if not display:
            return None

        row = self.order_by_display.get(
            display
        )

        if not row:
            return None

        return row["id"]

    # ========================================================
    # НОМЕРА ПЛАТ
    # ========================================================

    def get_serials(self):

        raw = self.serial_text.get(
            "1.0",
            "end"
        )

        result = []

        seen = set()

        for line in raw.splitlines():

            serial = normalize_serial(
                line
            )

            if not serial:
                continue

            if serial in seen:
                continue

            seen.add(serial)

            result.append(serial)

        return result

    # ========================================================
    # СЧЕТЧИК
    # ========================================================

    def on_serial_text_change(
        self,
        event=None
    ):

        serials = self.get_serials()

        self.serial_count_label.config(
            text=f"Уникальных плат: {len(serials)}"
        )

    # ========================================================
    # ОЧИСТКА СПИСКА
    # ========================================================

    def clear_serials(self):

        self.serial_text.delete(
            "1.0",
            "end"
        )

        self.serial_count_label.config(
            text="Уникальных плат: 0"
        )

        self.set_reset_result("")

        self.serial_text.focus_set()

    # ========================================================
    # ВЫВОД РЕЗУЛЬТАТА
    # ========================================================

    def set_reset_result(
        self,
        text
    ):

        self.reset_result_text.config(
            state="normal"
        )

        self.reset_result_text.delete(
            "1.0",
            "end"
        )

        self.reset_result_text.insert(
            "1.0",
            text
        )

        self.reset_result_text.config(
            state="disabled"
        )

    # ========================================================
    # СБРОС ПЛАТ
    # ========================================================

    def reset_selected_boards(self):

        order_id = self.get_selected_order_id()

        if order_id is None:

            messagebox.showwarning(
                "Заказ",
                "Выберите заказ"
            )

            return

        serials = self.get_serials()

        if not serials:

            messagebox.showwarning(
                "Платы",
                "Введите номера плат"
            )

            return

        preview = "\n".join(
            serials[:10]
        )

        if len(serials) > 10:

            preview += (
                f"\n... ещё "
                f"{len(serials) - 10}"
            )

        answer = messagebox.askyesno(
            "Подтверждение",
            f"Заказ ID: {order_id}\n\n"
            f"Плат: {len(serials)}\n\n"
            f"{preview}\n\n"
            f"Выполнить сброс?"
        )

        if not answer:
            return

        placeholders = ",".join(
            "?"
            for _ in serials
        )

        # ----------------------------------------------------
        # Найти платы
        # ----------------------------------------------------

        select_sql = f"""
            SELECT id,
                   serial_number
            FROM order_details
            WHERE order_id = ?
              AND serial_number IN ({placeholders})
        """

        # ----------------------------------------------------
        # Сброс
        # ----------------------------------------------------

        update_sql = f"""
            UPDATE order_details
            SET
                stand_id = NULL,
                data_matrix = NULL,
                date_sent = NULL,
                stand_status = NULL,
                log_path = NULL,
                user = NULL,
                test_result = NULL,
                report_path = NULL,
                error_description = NULL,
                status = NULL,
                started_at = NULL,
                finished_at = NULL,
                serial_number_8 = NULL,
                result_source = NULL  
            WHERE order_id = ?
              AND serial_number IN ({placeholders})
        """

        params = [
            order_id,
            *serials
        ]

        try:

            with self.get_connection() as conn:

                found_rows = conn.execute(
                    select_sql,
                    params
                ).fetchall()

                found_serials = set()

                for row in found_rows:

                    found_serials.add(
                        row["serial_number"]
                    )

                cursor = conn.execute(
                    update_sql,
                    params
                )

                updated_count = cursor.rowcount

                conn.commit()

        except Exception as exc:

            messagebox.showerror(
                "Ошибка SQL",
                str(exc)
            )

            return

        missing = []

        for serial in serials:

            if serial not in found_serials:

                missing.append(
                    serial
                )

        # ----------------------------------------------------
        # Результат
        # ----------------------------------------------------

        result = ""

        result += (
            f"Заказ ID: {order_id}\n"
        )

        result += (
            f"Отсканировано: {len(serials)}\n"
        )

        result += (
            f"Найдено: {len(found_serials)}\n"
        )

        result += (
            f"Обновлено записей: {updated_count}\n"
        )

        result += (
            f"Не найдено: {len(missing)}\n"
        )

        if found_serials:

            result += (
                "\nУСПЕШНО ОБРАБОТАНЫ:\n"
            )

            for serial in sorted(
                found_serials
            ):

                result += (
                    f"{serial}\n"
                )

        if missing:

            result += (
                "\nНЕ НАЙДЕНЫ:\n"
            )

            for serial in missing:

                result += (
                    f"{serial}\n"
                )

        self.set_reset_result(
            result
        )

        messagebox.showinfo(
            "Готово",
            f"Обновлено записей: "
            f"{updated_count}"
        )

        self.serial_text.focus_set()

    # ========================================================
    # СТАТУС ПЛАТЫ
    # ========================================================

    def find_board_status(self):

        raw_serial = (
            self.status_serial_var
            .get()
            .strip()
            .upper()
        )

        if not raw_serial:

            messagebox.showwarning(
                "Номер",
                "Введите номер платы"
            )

            return

        # U00072570B -> U00072570
        serial = normalize_serial(
            raw_serial
        )

        sql = """
            SELECT
                order_id,
                serial_number,
                log_path,
                user,
                test_result,
                report_path
            FROM order_details
            WHERE serial_number = ?
            ORDER BY id DESC
            LIMIT 1;
        """

        try:

            with self.get_connection() as conn:

                row = conn.execute(
                    sql,
                    (serial,)
                ).fetchone()

        except Exception as exc:

            messagebox.showerror(
                "Ошибка базы",
                str(exc)
            )

            return

        if row is None:

            self.clear_status_result()

            self.status_message_label.config(
                text=(
                    f"Плата {serial} "
                    f"не найдена"
                )
            )

            return

        self.status_labels[
            "order_id"
        ].config(
            text=self.show_value(
                row["order_id"]
            )
        )

        self.status_labels[
            "serial_number"
        ].config(
            text=self.show_value(
                row["serial_number"]
            )
        )

        self.status_labels[
            "user"
        ].config(
            text=self.show_value(
                row["user"]
            )
        )

        self.status_labels[
            "test_result"
        ].config(
            text=self.show_value(
                row["test_result"]
            )
        )

        self.status_labels[
            "report_path"
        ].config(
            text=self.show_value(
                row["report_path"]
            )
        )

        self.current_log_path = row[
            "log_path"
        ]

        if self.current_log_path:

            self.log_path_label.config(
                text=str(
                    self.current_log_path
                ),
                fg="blue",
                cursor="hand2"
            )

        else:

            self.log_path_label.config(
                text="-",
                fg="gray",
                cursor=""
            )

        self.status_message_label.config(
            text=(
                f"Плата найдена. "
                f"Запрос выполнен по номеру: "
                f"{serial}"
            )
        )

        # Чтобы следующий скан сразу заменял старый
        self.status_serial_entry.selection_range(
            0,
            "end"
        )

        self.status_serial_entry.focus_set()

    # ========================================================
    # ОЧИСТКА СТАТУСА
    # ========================================================

    def clear_status_result(self):

        for label in self.status_labels.values():

            label.config(
                text="-"
            )

        self.current_log_path = None

        self.log_path_label.config(
            text="-",
            fg="gray",
            cursor=""
        )

    # ========================================================
    # ОТОБРАЖЕНИЕ ЗНАЧЕНИЯ
    # ========================================================

    @staticmethod
    def show_value(value):

        if value is None:
            return "-"

        return str(value)

    # ========================================================
    # ОТКРЫТЬ LOG_PATH
    # ========================================================

    def open_log_path(
        self,
        event=None
    ):

        if not self.current_log_path:
            return

        try:

            open_path(
                str(
                    self.current_log_path
                )
            )

        except Exception as exc:

            messagebox.showerror(
                "Ошибка открытия",
                f"Не удалось открыть:\n"
                f"{self.current_log_path}\n\n"
                f"{exc}"
            )


# ============================================================
# ЗАПУСК
# ============================================================

if __name__ == "__main__":

    app = OrdersApp()

    app.mainloop()