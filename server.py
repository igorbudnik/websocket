import asyncio
import json
from openai import OpenAI
import websockets
import sqlite3
from websockets.exceptions import ConnectionClosed

import websockets



# Хранилище всех подключенных клиентов
clients = set()

# Подключение к базе данных SQLite
def get_db_connection():
    conn = sqlite3.connect('chat_history.db')
    return conn

# Создание таблицы для хранения сообщений (если она еще не существует)
def create_table():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            isClient BOOLEAN NOT NULL,
            name TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Добавление сообщения в базу данных
def save_message(content: str, isClient: bool):
    conn = get_db_connection()
    conn.execute('INSERT INTO messages (content, isClient) VALUES (?, ?)', (content, isClient))
    conn.commit()
    conn.close()

# Получение всех сообщений из базы данных
def get_all_messages():
    conn = get_db_connection()
    cursor = conn.execute('SELECT content, isClient FROM messages ORDER BY id ASC')
    messages = cursor.fetchall()
    conn.close()
    # print([message for message in messages])
    return [message for message in messages]



# Обработчик подключения клиента
async def handle_connection(websocket, path=""):
    # Отправляем историю сообщений при подключении
    
    history = get_all_messages()
    for msg in history:
        await websocket.send(json.dumps({"text": msg[0], "isClient": str(msg[1])}))

    # Добавляем клиента в список
    clients.add(websocket)
    print(f"Клиент подключился: {websocket.remote_address}")

    try:
        async for message in websocket:
            # client = OpenAI(base_url="http://127.0.0.1:1234/v1", api_key="not_needed")
            print(f"Получено сообщение от {websocket.remote_address}: {message}")
            
            # Сохраняем сообщение от клиента в базе данных
            save_message(message, True)
            
            # Отправляем подтверждение "Сообщение получено" и сохраняем это сообщение в базе данных
            response = "Сообщение получено"
            # response = client.chat.completions.create(
            #     model='meta-llama-3.1-8b-instruct',
            #     messages=[
            #         {'role': 'system', 'content': 'you are a helpful assistant'},
            #         {'role': 'user', 'content': message}
            #     ],
            #     temperature=0.5,
            #     max_tokens=1024
            #     ).choices[0].message.content

            # await websocket.send(json.dumps({"text": response, "isClient": 0}))
            # save_message(response, False)
            

            # Рассылаем сообщение всем клиентам (кроме подтверждения)
            for client in clients:
                # if client != websocket and client.open:
                # server_message = f"Сообщение от {websocket.remote_address}: {message}"
                await client.send(json.dumps({"text": message, "isClient": 0}))
                # save_message(server_message, False)  # Сохраняем сообщение, отправленное от сервера

    except ConnectionClosed:
        print(f"Клиент отключился: {websocket.remote_address}")

    finally:
        # Удаляем клиента из списка при отключении
        clients.remove(websocket)

# Запуск WebSocket-сервера
async def main():
    create_table()  # Создаем таблицу для хранения сообщений
    async with await websockets.serve(handle_connection, '0.0.0.0', 8765):
        print("WebSocket сервер запущен на ws://localhost:8000")
        await asyncio.Future()  # Блокируем выполнение для работы сервера

# Запуск в основном потоке
if __name__ == "__main__":
    asyncio.run(main())
