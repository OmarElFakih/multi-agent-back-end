import os
import aiohttp
from app.whatsapp_client import WhatsAppWrapper
from dotenv import load_dotenv

from aiohttp import web
#from aio.aplication import Application
routes = web.RouteTableDef()

load_dotenv()
all_clients = []
wsClient = WhatsAppWrapper()
nOfAgents = 0


VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")

class Application(web.Application):
    def __init__(self):
        super().__init__()

    def run(self):
        return web.run_app(self, port=8000)


async def send_all(message: str):
    for client in all_clients:
        await client.send_str(message)

@routes.get('/')
async def hello(request):
    return web.Response(text="Hello, world")


@routes.post('/post-all-chats')
async def post(request):
    data = await request.json()
    print(data["message"])
    await send_all(f"HTTP: {data['message']}")
    return web.Response(text=data["message"])

@routes.get('/webhook')
async def verify_webhook(request):
    data = request.query["hub.verify_token"]
    print(request.query)
    
    print(f"request: {data}  enviroment: {VERIFY_TOKEN}")

    if request.query["hub.verify_token"] == VERIFY_TOKEN:
        return web.Response(text=request.query["hub.challenge"])
    return "Authentication failed. Invalid Token."


@routes.post('/webhook')
async def webhook_notification(request):
    data = await request.json()
    
    if "messages" in data["entry"][0]["changes"][0]["value"]:
        message_data = data["entry"][0]["changes"][0]["value"]["messages"][0]
        print(f'{message_data["text"]["body"]}')
        await send_all(f'{message_data["from"]}: {message_data["text"]["body"]}')

    print(data)
    
    return web.Response(text="success")


@routes.get('/ws')
async def websocket_handler(request):

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    global nOfAgents

    id = nOfAgents

    nOfAgents += 1
    

    all_clients.append(ws)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            #if msg.data == 'close':
            #   await ws.close()
            #else:
                #await ws.send_str(f'{id}: {msg.data}')
                await send_all(f'Agent{id}: {msg.data}')
                wsClient.send_message(msg.data, "584123722632")
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                  ws.exception())

    print('websocket connection closed')
    all_clients.remove(ws)
    return ws

application = Application()
application.add_routes(routes)

if __name__ == "__main__":
    application.run()