import os
import aiohttp
from app.whatsapp_client import WhatsAppWrapper
from dotenv import load_dotenv
import json

from aiohttp import web
#from aio.aplication import Application
routes = web.RouteTableDef()

load_dotenv()
all_clients = []
wsClient = WhatsAppWrapper()


VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")

class Application(web.Application):
    def __init__(self):
        super().__init__()

    def run(self):
        return web.run_app(self, port=8000)


async def send_all(message):
    for client in all_clients:
        if client["business_number_id"] == message["business_number_id"]:
            await client["connection"].send_str(json.dumps(message))

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
    message_data = wsClient.request_data(data)

    if(message_data != "not a message"):
        print(message_data)
        await send_all(message_data)

    #print(data)
    
    return web.Response(text="success")


@routes.get('/ws')
async def websocket_handler(request):

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    client = {
        "connection": ws,
        "business_number_id": ""
    }

    all_clients.append(client)
    print("client connected")

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                
                #await send_all()
                print(data)
                
                if data["type"] == "connection":
                    print("connection")
                    client["business_number_id"] = data["business_number_id"]

                if data["type"] == "message":
                    wsClient.send_message(data["message"], data["client_number"], client["business_number_id"])

        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                  ws.exception())

    print('websocket connection closed')
    all_clients.remove(client)
    return ws

application = Application()
application.add_routes(routes)

if __name__ == "__main__":
    application.run()