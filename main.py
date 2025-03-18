import logging
import socket
import sys

from my_asyncio import AsyncSocket, NewTask, Scheduler

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# Создаём обработчик вывода в консоль
handler = logging.StreamHandler(stream=sys.stdout)
handler.setLevel(logging.INFO)

# Добавляем форматтер
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# Добавляем обработчик в логгер
logger.addHandler(handler)


HOST, PORT = "", 8001


def handle_client(client: socket.socket, address: socket.AddressInfo):
    logging.info("Подключение клиента %s", address)

    while True:
        data = yield from client.recv(65536)  # Ждем данные от клиента
        if not data:
            break
        yield from client.send(data)
    logger.info("Закрыто соединение с клиентом")
    client.close()


def server():
    logging.info("Запуск сервера на порту %s", PORT)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((HOST, PORT))
        sock.listen()
        sc = AsyncSocket(sock)

        while True:
            client, address = yield from sc.accept()  # Ждем подключения клиента
            yield NewTask(
                handle_client(client, address)
            )  # Создаем задачу для обработки клиента


def main():
    scheduler = Scheduler()
    scheduler.add_task(server())
    scheduler.event_loop()


if __name__ == "__main__":
    main()
