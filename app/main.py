import aiohttp
from whatsapp_client import WhatsAppWrapper

from aiohttp import web
routes = web.RouteTableDef()

all_clients = []
wsClient = WhatsAppWrapper()

async def send_all(message: str):
    for client in all_clients:
        await client.send_str(message)



@routes.post('/post-all-chats')
async def post(request):
    data = await request.json()
    print(data["message"])
    await send_all(f"HTTP: {data['message']}")
    return web.Response(text=data["message"])

@routes.get('/')
async def hello(request):
    return web.Response(text="Hello, world")

@routes.get('/ws')
async def websocket_handler(request):

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    id = ""

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            id = msg.data
            break

    all_clients.append(ws)

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
            else:
                #await ws.send_str(f'{id}: {msg.data}')
                await send_all(f'{id}: {msg.data}')
                wsClient.send_message(msg.data, "584123722632")
        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                  ws.exception())

    print('websocket connection closed')
    all_clients.remove(ws)
    return ws


app = web.Application()
app.add_routes(routes)
web.run_app(app)