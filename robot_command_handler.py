from typing import List, Optional
import threading

command_toBOt = 0

command_toBOt_lock = threading.Lock()

class RobotCommandHandler:
    def __init__(self):
        self.command_queue: List[int] = []  # Очередь команд
        self.current_command: Optional[int] = None  # Исправлено: инициализируем как None
        self.variable1: Optional[int] = 0  # Переменная, куда пишутся команды

    def add_command(self, command: int) -> None:  # Исправлен тип команды на int
        """Добавляет команду в очередь."""
        self.command_queue.append(command)
        self._try_send_next_command()

    def _try_send_next_command(self) -> None:
        """Отправляет следующую команду, если нет текущей выполняемой."""
        global command_toBOt
        with command_toBOt_lock:  # Защищаем доступ к глобальной переменной
            if self.current_command is None and self.command_queue:
                self.current_command = self.command_queue[0]
                self.variable1 = self.current_command
                print(f"Отправлена команда: {self.current_command}")
                command_toBOt = self.current_command

    def check_response(self, response: int) -> bool:  # Исправлен тип response на int
        """
        Проверяет ответ робота.
        Если ответ соответствует текущей команде - удаляет её из очереди.
        Возвращает True, если команда выполнена, иначе False.
        """
        if self.current_command is None:
            return False

        # Простая проверка равенства (можно адаптировать под вашу логику)
        if response == self.current_command:  # Убраны фигурные скобки
            print(f"Команда выполнена: {self.current_command}")
            self.command_queue.pop(0)  # Удаляем выполненную команду
            self.current_command = None
            self._try_send_next_command()  # Пробуем отправить следующую
            return True
        else:
            print(f"Ожидается ответ для: {self.current_command}, но получен: {response}")
            return False

# robot = RobotCommandHandler()
# robot.add_command("MOVE_TO_X10")
# robot.add_command("GRAB_ITEM")
# robot.add_command("2GRdcdcsITEM")
# robot.add_command("3GRAvdvsdvITEM")
# robot.add_command("4GRABvsdvdsEM")
# print (f"*****{command_toBOt}")

# # Эмуляция ответа робота
# robot.check_response("Done: MOVE_TO_X10")  # Удалит MOVE_TO_X10, отправит GRAB_ITEM
# print (command_toBOt)

# robot.check_response("Done: GRAB_ITEM")    # Очередь пуста
# print (command_toBOt)

# robot.check_response("Done: 2GRdcdcsITEM")    # Очередь пуста
# print (command_toBOt)
