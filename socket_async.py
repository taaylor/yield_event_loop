from socket import socket
from typing import Generator

from api_task import SystemCall


class WriteWait(SystemCall):
    """Ожидание записи"""

    def __init__(self, f: socket):
        self.f = f

    def handle(self, sched, task):
        fd = self.f.fileno()  # возвращает целочисленный файл дескриптор
        sched.wait_for_write(task, fd)


class ReadWait(SystemCall):
    """Ожидание чтения"""

    def __init__(self, f: socket):
        self.f = f

    def handle(self, sched, task):
        fd = self.f.fileno()  # возвращает целочисленный файл дескриптор
        sched.wait_for_read(task, fd)


class AsyncSocket:
    """Предоставляет асинхронные методы для работы с socket"""

    def __init__(self, sock: socket):
        self.sock = sock

    def accept(self) -> Generator:
        yield ReadWait(self.sock)
        client, addr = self.sock.accept()
        return self.__class__(client), addr

    def send(self, buffer: bytes):
        while buffer:
            yield WriteWait(self.sock)
            len = self.sock.send(buffer)
            buffer = buffer[len:]

    def recv(self, maxbytes: int) -> Generator:
        yield ReadWait(self.sock)
        return self.sock.recv(maxbytes)

    def close(self):
        yield self.sock.close()
