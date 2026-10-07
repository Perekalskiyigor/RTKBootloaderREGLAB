# python -m PyInstaller --onefile BDRedactor.py
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog 
from pathlib import Path

# simpledialog — маленькое окно ввода при редактировании поля.


DB_PATH = "orders.db" 


# Cписок полей, которые программа показывает. ORDER_FIELDS — поля из таблицы Orders.
ORDER_FIELDS = [
    "id",
    "time_added",
    "order_number",
    "module",
    "Nomenclature",
    "Value",
    "VersionLoadFile",
    "fw_version",
    "marking_templates",
]


# Cписок полей, которые программа показывает. BOARD_FIELDS — поля из таблицы order_details.
BOARD_FIELDS = [
    "id",
    "date_added",
    "order_id",
    "stand_id",
    "data_matrix",
    "date_sent",
    "log_path",
    "user",
    "test_result",
    "report_path",
    "error_description",
    "serial_number",
]


class DatabaseEditor(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Редактор БД РТК тестирования и прошивки v1")
        self.geometry("1450x850")

        self.conn = sqlite3.connect(DB_PATH) # Открываем соединение с базой.
        self.conn.row_factory = sqlite3.Row # Позволяет делать выбор не только по заказу но и по выпадющему списку, метод

        # программа запоминает выбранный заказ.
        self.selected_order_id = None
        self.selected_order_number = None
        self.orders_map = {} # Выпадающий список 70 | ЗНП-29961.1.1 | ModuleName

        self.create_ui()
        self.load_orders_to_combo()

    # =========================================================
    # UI
    # =========================================================

    def create_ui(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self.orders_tab = ttk.Frame(notebook)
        self.boards_tab = ttk.Frame(notebook)
        self.defect_tab = ttk.Frame(notebook)

        notebook.add(self.orders_tab, text="Заказы")
        notebook.add(self.boards_tab, text="Платы")
        notebook.add(self.defect_tab, text="Брак")

        self.create_orders_tab()
        self.create_boards_tab()
        self.create_defect_tab()

    #  метод рисует верхнюю вкладку заказов
    def create_orders_tab(self):
        top = ttk.Frame(self.orders_tab)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Заказ:").pack(side="left")

        self.order_entry = ttk.Entry(top, width=35)
        self.order_entry.pack(side="left", padx=5)

        ttk.Button(
            top,
            text="Найти",
            command=self.find_order_from_entry
        ).pack(side="left", padx=5)

        ttk.Label(top, text="или выбрать:").pack(side="left", padx=15)

        self.orders_combo = ttk.Combobox(top, width=65, state="readonly")
        self.orders_combo.pack(side="left", padx=5)
        self.orders_combo.bind("<<ComboboxSelected>>", self.on_order_selected)

        self.order_fields_frame = ttk.LabelFrame(self.orders_tab, text="Поля заказа")
        self.order_fields_frame.pack(fill="both", expand=True, padx=10, pady=10)

    #  метод рисует верхнюю вкладку плат
    def create_boards_tab(self):
        """
        создаётся:
        Заголовок выбранного заказа
        Панель массового редактирования
        Таблица плат
        """
        top = ttk.Frame(self.boards_tab)
        top.pack(fill="x", padx=10, pady=10)

        self.boards_title = ttk.Label(top, text="Заказ не выбран")
        self.boards_title.pack(side="left")

        edit_panel = ttk.LabelFrame(
            self.boards_tab,
            text="Массовое редактирование выделенных плат"
        )
        edit_panel.pack(fill="x", padx=10, pady=5)

        ttk.Label(edit_panel, text="Колонка:").pack(side="left", padx=5, pady=5)

        # выпадающий список колонок
        self.mass_field_combo = ttk.Combobox(
            edit_panel,
            values=[f for f in BOARD_FIELDS if f != "id"],
            state="readonly",
            width=25
        )
        self.mass_field_combo.pack(side="left", padx=5, pady=5)

        ttk.Label(edit_panel, text="Значение:").pack(side="left", padx=(15, 0), pady=5) 

        self.mass_value_entry = ttk.Entry(edit_panel, width=45) # поле значения которые присвоятся выбранным колонкам
        self.mass_value_entry.pack(side="left", padx=5, pady=5)

        ttk.Button(
            edit_panel,
            text="Проставить выделенным",
            command=self.mass_update_boards
        ).pack(side="left", padx=5, pady=5)

        ttk.Button(
            edit_panel,
            text="Обнулить выделенным",
            command=self.mass_clear_boards
        ).pack(side="left", padx=5, pady=5)

        ttk.Button(
            edit_panel,
            text="Обновить список",
            command=self.reload_boards
        ).pack(side="left", padx=5, pady=5)

        table_frame = ttk.Frame(self.boards_tab)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.boards_tree = ttk.Treeview(
            table_frame,
            columns=BOARD_FIELDS,
            show="headings",
            selectmode="extended" # можно выделять много строк через Ctrl или Shift
        )

        self.setup_tree_columns(self.boards_tree)

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.boards_tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.boards_tree.xview)

        self.boards_tree.configure(
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )

        self.boards_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        self.boards_tree.bind("<Double-1>", self.edit_board_cell) # Двойной клик по ячейке — редактирование одной ячейки.

    # Вкладка «Брак»
    def create_defect_tab(self):
        top = ttk.Frame(self.defect_tab)
        top.pack(fill="x", padx=10, pady=10)

        self.defect_title = ttk.Label(top, text="Заказ не выбран")
        self.defect_title.pack(side="left")

        ttk.Button(
            top,
            text="Обновить брак",
            command=self.reload_defects
        ).pack(side="left", padx=10)

        main_frame = ttk.Frame(self.defect_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.defect_tree = ttk.Treeview(
            main_frame,
            columns=BOARD_FIELDS,
            show="headings",
            selectmode="browse"
        )

        self.setup_tree_columns(self.defect_tree)

        y_scroll = ttk.Scrollbar(main_frame, orient="vertical", command=self.defect_tree.yview)
        x_scroll = ttk.Scrollbar(main_frame, orient="horizontal", command=self.defect_tree.xview)

        self.defect_tree.configure(
            yscrollcommand=y_scroll.set,
            xscrollcommand=x_scroll.set
        )

        self.defect_tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        main_frame.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        self.defect_tree.bind("<Double-1>", self.open_defect_file_from_cell)

        text_frame = ttk.LabelFrame(
            self.defect_tab,
            text="Просмотр файла из log_path / report_path"
        )
        text_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.defect_text = tk.Text(text_frame, wrap="word", height=15)
        self.defect_text.pack(side="left", fill="both", expand=True)

        text_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.defect_text.yview)
        text_scroll.pack(side="right", fill="y")

        self.defect_text.configure(yscrollcommand=text_scroll.set)

    # общий метод для таблицы плат и таблицы брака.
    # Он задаёт название колонки и ширину
    def setup_tree_columns(self, tree):
        for field in BOARD_FIELDS:
            tree.heading(field, text=field)

            if field == "id":
                width = 70
            elif field in ("error_description", "report_path", "log_path"):
                width = 260
            elif field == "serial_number":
                width = 160
            else:
                width = 130

            tree.column(field, width=width, anchor="w")

    # =========================================================
    # Заказы
    # =========================================================

    def load_orders_to_combo(self):
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
            rows = self.conn.execute(sql).fetchall()
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))
            return

        self.orders_map.clear()
        values = []

        for row in rows:
            text = f"{row['id']} | {row['order_number']} | {row['module']}"
            values.append(text)
            self.orders_map[text] = row["id"]

        self.orders_combo["values"] = values

    def find_order_from_entry(self):
        order_number = self.order_entry.get().strip()

        if not order_number:
            messagebox.showwarning("Нет заказа", "Введите номер заказа")
            return

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
        WHERE order_number = ?;
        """

        try:
            row = self.conn.execute(sql, (order_number,)).fetchone()
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))
            return

        if not row:
            messagebox.showerror("Не найдено", f"Заказ {order_number} не найден")
            return

        self.show_order(row)
        self.load_boards(row["id"])
        self.load_defects(row["id"])

    def on_order_selected(self, event=None):
        selected = self.orders_combo.get()
        order_id = self.orders_map.get(selected)

        if not order_id:
            return

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
        WHERE id = ?;
        """

        try:
            row = self.conn.execute(sql, (order_id,)).fetchone()
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))
            return

        if row:
            self.show_order(row)
            self.load_boards(row["id"])
            self.load_defects(row["id"])

    # Показ заказа
    def show_order(self, row):
        for widget in self.order_fields_frame.winfo_children():
            widget.destroy()

        self.selected_order_id = row["id"]
        self.selected_order_number = row["order_number"]

        for i, field in enumerate(ORDER_FIELDS):
            ttk.Label(
                self.order_fields_frame,
                text=field,
                width=25
            ).grid(row=i, column=0, sticky="w", padx=5, pady=4)

            value_var = tk.StringVar(
                value="" if row[field] is None else str(row[field])
            )

            entry = ttk.Entry(
                self.order_fields_frame,
                textvariable=value_var,
                width=100,
                state="readonly"
            )
            entry.grid(row=i, column=1, sticky="we", padx=5, pady=4)

            btn = ttk.Button(
                self.order_fields_frame,
                text="✎",
                width=3,
                command=lambda f=field, v=value_var: self.edit_order_field(f, v)
            )
            btn.grid(row=i, column=2, padx=5, pady=4)

        self.order_fields_frame.columnconfigure(1, weight=1)

    # Метод редактирует поля заказа
    def edit_order_field(self, field, value_var):
        if field == "id":
            messagebox.showinfo("Нельзя редактировать", "Поле id лучше не менять")
            return

        old_value = value_var.get()

        new_value = simpledialog.askstring(
            "Редактирование заказа",
            f"{field}:",
            initialvalue=old_value
        )

        if new_value is None:
            return

        sql = f"UPDATE Orders SET {field} = ? WHERE id = ?;"

        try:
            self.conn.execute(sql, (new_value, self.selected_order_id))
            self.conn.commit()

            value_var.set(new_value)
            self.load_orders_to_combo()

            messagebox.showinfo("Готово", "Поле заказа обновлено")

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Ошибка БД", str(e))

    # =========================================================
    # Платы
    # =========================================================

    def load_boards(self, order_id):
        """Загрузка плат"""
        self.selected_order_id = order_id

        self.boards_title.config(
            text=f"Платы по заказу ID={order_id}, заказ={self.selected_order_number}"
        )

        # Сначала очищает таблицу
        for item in self.boards_tree.get_children():
            self.boards_tree.delete(item)

        sql = """
        SELECT id,
               date_added,
               order_id,
               stand_id,
               data_matrix,
               date_sent,
               log_path,
               user,
               test_result,
               report_path,
               error_description,
               serial_number
        FROM order_details
        WHERE order_id = ?
        ORDER BY id;
        """

        try:
            rows = self.conn.execute(sql, (order_id,)).fetchall()
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))
            return

        # каждую строку добавляет в таблицу
        for row in rows:
            values = [row[field] for field in BOARD_FIELDS]
            self.boards_tree.insert("", "end", values=values)

    def reload_boards(self):
        if not self.selected_order_id:
            messagebox.showwarning("Нет заказа", "Сначала выберите заказ")
            return

        self.load_boards(self.selected_order_id)
        self.load_defects(self.selected_order_id)

    def edit_board_cell(self, event):
        """
        Редактирование одной ячейки платы
        Метод определяет:
        какая строка
        какая колонка
        """
        region = self.boards_tree.identify("region", event.x, event.y)

        if region != "cell":
            return

        item_id = self.boards_tree.identify_row(event.y)
        column_id = self.boards_tree.identify_column(event.x)

        if not item_id or not column_id:
            return

        col_index = int(column_id.replace("#", "")) - 1
        field = BOARD_FIELDS[col_index]

        if field == "id":
            messagebox.showinfo("Нельзя редактировать", "Поле id лучше не менять")
            return

        values = list(self.boards_tree.item(item_id, "values"))
        board_id = values[0]
        old_value = values[col_index]

        new_value = simpledialog.askstring(
            "Редактирование платы",
            f"{field}:",
            initialvalue=old_value
        )

        if new_value is None:
            return

        sql = f"UPDATE order_details SET {field} = ? WHERE id = ?;"

        try:
            self.conn.execute(sql, (new_value, board_id))
            self.conn.commit()

            values[col_index] = new_value
            self.boards_tree.item(item_id, values=values)

            self.load_defects(self.selected_order_id)

            messagebox.showinfo("Готово", "Поле платы обновлено")

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Ошибка БД", str(e))

    def mass_update_boards(self):
        field = self.mass_field_combo.get()
        value = self.mass_value_entry.get()

        if not field:
            messagebox.showwarning("Нет колонки", "Выберите колонку")
            return

        selected_items = self.boards_tree.selection()

        if not selected_items:
            messagebox.showwarning("Нет строк", "Выделите одну или несколько плат")
            return

        if not messagebox.askyesno(
            "Подтверждение",
            f"Проставить значение '{value}' в колонку '{field}' "
            f"для {len(selected_items)} записей?"
        ):
            return

        try:
            for item_id in selected_items:
                values = list(self.boards_tree.item(item_id, "values"))
                board_id = values[0]

                self.conn.execute(
                    f"UPDATE order_details SET {field} = ? WHERE id = ?;",
                    (value, board_id)
                )

                col_index = BOARD_FIELDS.index(field)
                values[col_index] = value
                self.boards_tree.item(item_id, values=values)

            self.conn.commit()
            self.load_defects(self.selected_order_id)

            messagebox.showinfo("Готово", "Выделенные записи обновлены")

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Ошибка БД", str(e))

    def mass_clear_boards(self):
        field = self.mass_field_combo.get()

        if not field:
            messagebox.showwarning("Нет колонки", "Выберите колонку")
            return

        selected_items = self.boards_tree.selection()

        if not selected_items:
            messagebox.showwarning("Нет строк", "Выделите одну или несколько плат")
            return

        if not messagebox.askyesno(
            "Подтверждение",
            f"Обнулить колонку '{field}' для {len(selected_items)} записей?"
        ):
            return

        try:
            for item_id in selected_items:
                values = list(self.boards_tree.item(item_id, "values"))
                board_id = values[0]

                self.conn.execute(
                    f"UPDATE order_details SET {field} = NULL WHERE id = ?;",
                    (board_id,)
                )

                col_index = BOARD_FIELDS.index(field)
                values[col_index] = ""
                self.boards_tree.item(item_id, values=values)

            self.conn.commit()
            self.load_defects(self.selected_order_id)

            messagebox.showinfo("Готово", "Выделенные записи обнулены")

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("Ошибка БД", str(e))

    # =========================================================
    # Брак
    # =========================================================

    def load_defects(self, order_id):
        """показывает только платы выбранного заказа, где ошибка 404"""
        self.defect_title.config(
            text=f"Брак по заказу ID={order_id}, заказ={self.selected_order_number}"
        )

        for item in self.defect_tree.get_children():
            self.defect_tree.delete(item)

        self.defect_text.delete("1.0", tk.END)

        sql = """
        SELECT id,
               date_added,
               order_id,
               stand_id,
               data_matrix,
               date_sent,
               log_path,
               user,
               test_result,
               report_path,
               error_description,
               serial_number
        FROM order_details
        WHERE order_id = ?
          AND test_result = 404
        ORDER BY id;
        """

        try:
            rows = self.conn.execute(sql, (order_id,)).fetchall()
        except Exception as e:
            messagebox.showerror("Ошибка БД", str(e))
            return

        for row in rows:
            values = [row[field] for field in BOARD_FIELDS]
            self.defect_tree.insert("", "end", values=values)

    def reload_defects(self):
        if not self.selected_order_id:
            messagebox.showwarning("Нет заказa", "Сначала выберите заказ")
            return

        self.load_defects(self.selected_order_id)

    def open_defect_file_from_cell(self, event):
        """Метод срабатывает по двойному клику на вкладке Брак. Он проверяет, что  кликнул именно по колонке: """
        region = self.defect_tree.identify("region", event.x, event.y)

        if region != "cell":
            return

        item_id = self.defect_tree.identify_row(event.y)
        column_id = self.defect_tree.identify_column(event.x)

        if not item_id or not column_id:
            return

        col_index = int(column_id.replace("#", "")) - 1
        field = BOARD_FIELDS[col_index]

        if field not in ("log_path", "report_path"):
            return

        values = list(self.defect_tree.item(item_id, "values"))
        file_path = values[col_index]

        if not file_path:
            messagebox.showwarning("Нет пути", f"Поле {field} пустое")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, "r", encoding="cp1251") as file:
                    content = file.read()
            except Exception as e:
                messagebox.showerror("Ошибка чтения файла", str(e))
                return
        except Exception as e:
            messagebox.showerror("Ошибка чтения файла", str(e))
            return

        self.defect_text.delete("1.0", tk.END)
        self.defect_text.insert(tk.END, f"Файл: {file_path}\n")
        self.defect_text.insert(tk.END, "=" * 120 + "\n\n")
        self.defect_text.insert(tk.END, content)

    # =========================================================
    # Закрытие
    # =========================================================

    def destroy(self):
        try:
            self.conn.close()
        except Exception:
            pass

        super().destroy()


if __name__ == "__main__":
    app = DatabaseEditor()
    app.mainloop()


"""
Старт программы
↓
Открываем orders.db
↓
Создаём 3 вкладки
↓
Загружаем список заказов
↓
Пользователь выбирает заказ
↓
Показываем поля заказа
↓
Показываем платы этого заказа
↓
Показываем брак test_result = 404
↓
Можно редактировать заказ
↓
Можно редактировать платы
↓
Можно массово менять платы
↓
Можно открыть лог брака
"""