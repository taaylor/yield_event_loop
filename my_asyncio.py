import logging
from queue import Queue
from selectors import EVENT_READ, EVENT_WRITE, DefaultSelector
from typing import Generator, Union


class Task:
    """
    Реализация класса Task который создает задачу на основе корутины
    """

    task_id = 0  # количество созданных задач

    def __init__(self, coroutine: Generator):
        self.__class__.task_id += 1
        self.tid = self.__class__.task_id  # id задачи
        self.target = coroutine  # переданная корутина
        self.sendval = None
        self.stack = []  # вызываемые задачи

    def run(self):
        """Метод выполнения задачи"""
        while True:
            try:
                # Отправляем значение в корутину
                result = self.target.send(self.sendval)
                if isinstance(result, SystemCall):
                    return result

                # Если result — это новая корутина (Generator), значит, мы вошли в вложенный вызов
                if isinstance(result, Generator):

                    self.stack.append(self.target)  # Текущую корутину кладём в стек
                    self.sendval = None  # Обнуляем значение
                    self.target = result  # Переключаемся на новую корутину
                else:
                    # Если стек пуст, значит, это верхний уровень и выполнение завершается
                    if not self.stack:
                        return
                    self.sendval = result  # Устанавливаем полученное значение
                    self.target = self.stack.pop()  # Возвращаемся к прошлой корутине
            except StopIteration:
                # Если стек пуст - выполнение задачи полностью завершается
                if not self.stack:
                    raise
                # Иначе возвращемся на уровень выше к корутине
                self.sendval = None
                self.target = self.stack.pop()


class Scheduler:
    """Планировщик задач"""

    def __init__(self):
        self.ready = Queue()  # Очередь готовых к выполнению задач
        self.task_map = {}  # Словарь, содержащий все задачи
        self.selector = DefaultSelector()  # Селектор для работы с I/O

    def schedule(self, task: Task):
        """Добавляет задачу в очередь выполнения"""
        self.ready.put(task)

    def exit(self, task: Task):
        """Удаляет завершенную задачу из списка активных задач"""
        logging.info("Задача %s завершена", task.tid)
        del self.task_map[task.tid]

    def add_task(self, coroutine: Generator) -> int:
        """Создает задачу и добавляет её в планировщик"""
        task = Task(coroutine)
        self.task_map[task.tid] = task
        self.schedule(task)
        return task.tid

    def wait_for_read(self, task: Task, fd: int):
        """Регистрирует задачу на ожидание события чтения"""
        self._wait_for_abstract(task, fd, EVENT_READ)

    def wait_for_write(self, task: Task, fd: int):
        """Регистрирует задачу на ожидание события записи"""
        self._wait_for_abstract(task, fd, EVENT_WRITE)

    def _wait_for_abstract(self, task: Task, fd: int, event: EVENT_READ | EVENT_WRITE):
        """Регистрирует задачу в селекторе на ожидание события"""
        try:
            key = self.selector.get_key(fd)
        except KeyError:
            data = (task, None) if event == EVENT_READ else (None, task)
            self.selector.register(fd, event, data)
        else:
            mask, (reader, writer) = key.events, key.data
            data = (task, writer) if event == EVENT_READ else (reader, task)
            self.selector.modify(fd, mask | event, (task, writer))

    def _abstract_remove(self, fd: int, event: EVENT_READ | EVENT_WRITE):
        """Удаляет задачу из селектора"""
        try:
            key = self.selector.get_key(fd)
        except KeyError:
            pass
        else:
            mask, (reader, writer) = key.events, key.data
            mask &= ~event
            if not mask:
                self.selector.unregister(fd)
            else:
                if event == EVENT_WRITE:
                    self.selector.modify(fd, mask, (None, writer))
                elif event == EVENT_READ:
                    self.selector.modify(fd, mask, (reader, None))

    def _remove_reader(self, fd: int):
        """Удаляет задачу чтения из селектора"""
        self._abstract_remove(fd, EVENT_READ)

    def _remove_writer(self, fd: int):
        """Удаляет задачу записи из селектора"""
        self._abstract_remove(fd, EVENT_WRITE)

    def io_poll(self, timeout: Union[None, float]):
        """Ожидает события ввода-вывода и добавляет соответствующие задачи в очередь"""
        events = self.selector.select(timeout)
        for key, mask in events:
            fileobj, (reader, writer) = key.fileobj, key.data

            if mask & EVENT_READ and reader is not None:
                self.schedule(reader)
                self._remove_reader(fileobj)

            if mask & EVENT_WRITE and writer is not None:
                self.schedule(writer)
                self._remove_writer(fileobj)

    def io_task(self) -> Generator:
        """Бесконечная корутина, которая обрабатывает I/O события"""
        while True:
            if self.ready.empty():
                self.io_poll(None)  # Если нет готовых задач, ждем события
            else:
                self.io_poll(0)  # Если есть задачи, сразу проверяем селектор
            yield

    def _run_once(self):
        """Выполняет одну задачу из очереди"""
        task = self.ready.get()
        try:
            result = task.run()
            if isinstance(result, SystemCall):
                result.handle(self, task)
                return
        except StopIteration:
            self.exit(task)  # Если задача завершилась, удаляем её
            return
        self.schedule(task)  # Если нет, добавляем обратно в очередь

    def event_loop(self):
        """Запускает основной цикл событий"""
        self.add_task(self.io_task())  # Добавляем обработку ввода-вывода
        while self.task_map:
            self._run_once()  # Выполняем задачи по очереди


class SystemCall:
    def handle(self, sched: Scheduler, task: Task):
        pass
