import asyncio

import websockets


all_clients = []

async def send_message(message: str):
    for client in all_clients:
        await client.send(message)

async def new_client_connected(client_socket, path):
    print("new client connected")
    all_clients.append(client_socket)


    while True:
        try:    
            new_message = await client_socket.recv()
            print("Client sent: ", new_message)
            await send_message(new_message)
        except websockets.ConnectionClosedOK:
            all_clients.remove(client_socket)
            break

async def start_server():
    print("Server started")
    await websockets.serve(new_client_connected, "localhost", 12345)


if __name__ == '__main__':
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(start_server())
    event_loop.run_forever()