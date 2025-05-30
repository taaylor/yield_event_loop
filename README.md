# Описание

Реализация цикла событий на основе генераторов (event-loop) код Дэвида Бизли.
Код является модификацией кода Дэвида Бизли & Яндекс Практикума. 

1. **`Task`** – представляет собой задачу, оборачивает корутину (функцию-генератор) и управляет её выполнением.
2. **`Scheduler`** – планировщик задач, управляет их выполнением и обработкой событий ввода-вывода.
3. **`AsyncSocket`** – обертка над `socket`, позволяющая использовать его асинхронно.
4. **`SystemCall`** – базовый класс для системных вызовов (например, `NewTask`, `WriteWait`, `ReadWait`).
5. **`NewTask`** – создаёт новую задачу в планировщике.
6. **`WriteWait` / `ReadWait`** – позволяют приостановить выполнение задачи до готовности сокета к записи/чтению.

## Как работает event loop

1. **Запуск сервера (`server`)**
	- Запускает `socket` и ожидает подключения клиентов.
    - При подключении клиента создает новую задачу `handle_client(client, address)`.
2. **Обработка клиента (`handle_client`)**
    - Читает данные из сокета (`recv`).
    - Если данные есть, отправляет их обратно (`send`).
    - Если данных нет – закрывает соединение.
3. **Планировщик (`Scheduler`)**
	- Умеет:
	- Добавлять задачи (`add_task`).
	- Ожидать событий ввода-вывода (`wait_for_read`, `wait_for_write`).
	- Выполнять задачи (`_run_once`).
	- Работать с `selectors` (следить за готовностью сокетов).
    - Запускает бесконечный цикл обработки задач (`event_loop`).


## Итог: Как это работает?

1. **Запускается `event_loop()`** → добавляется сервер `server()`.
2. **Сервер слушает сокет** и ждет подключения клиентов (`accept`).
3. **При подключении** создается `handle_client()`.
4. **Читаем и отправляем данные асинхронно** (`recv` / `send`).
5. **Если данных нет** → закрываем соединение.
