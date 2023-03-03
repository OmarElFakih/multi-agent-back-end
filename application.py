import os
import aiohttp
from whatsapp.whatsapp_client import WhatsAppWrapper
from whatsapp.whatsapp_data_types import Whatsapp_msg_data
from mongo.mongo_client import MongoWrapper
from mongo.mongo_doc_types import Message_doc
from dotenv import load_dotenv
import json

from aiohttp import web
#from aio.aplication import Application
routes = web.RouteTableDef()

load_dotenv()
all_agents = []
nOfAgents = 0




VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")
MONGODB_ATLAS_CONNECTION_STRING = os.environ.get("MONGODB_ATLAS_CONNECTION_STRING")
MONGODB_ATLAS_DATABASE_NAME = os.environ.get("MONGODB_ATLAS_DATABASE_NAME")

wsClient = WhatsAppWrapper()
mgClient = MongoWrapper(MONGODB_ATLAS_CONNECTION_STRING, MONGODB_ATLAS_DATABASE_NAME)

class Application(web.Application):
    def __init__(self):
        super().__init__()

    def run(self):
        return web.run_app(self, port=8000)


async def send_agents(message, agent_id=""):
    for agent in all_agents:
        if agent["business_number_id"] == message["business_number_id"]:
            if((agent["role"] == "admin") or (agent["id"] == agent_id) or (agent_id == "")):
                await agent["connection"].send_str(json.dumps(message))

@routes.get('/')
async def hello(request):
    return web.Response(text="Hello, world")


@routes.post('/post-all-chats')
async def post(request):
    data = await request.json()
    print(data["message"])
    await send_agents(f"HTTP: {data['message']}")
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
        converstaion = mgClient.find_conversation(message_data["client_number"], message_data["business_number_id"])

        if converstaion == None:
            
            await send_agents(message_data)
            mgClient.insert_conversation(message_data, message_data["client_profile_name"])

        else: 
            await send_agents(message_data, converstaion["assigned_agent"])
            

            doc_msg: Message_doc = {
                "sender": message_data["client_profile_name"],
                "body": message_data["message"],
                "sent_on": message_data["timestamp"],
                "tag": "default"
            }

            mgClient.insert_message(doc_msg, message_data["client_number"], message_data["business_number_id"])


    
    return web.Response(text="success")


@routes.get('/ws')
async def websocket_handler(request):

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    global nOfAgents
    
    agent = {
        "id": f"Agent {nOfAgents}",
        "connection": ws,
        "business_number_id": "",
        "role": "agent"
    }

    all_agents.append(agent)
    print("client connected")

    nOfAgents += 1

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                
                
                print(data)
                
                if data["type"] == "connection": 
                    print("connection")
                    agent["business_number_id"] = data["business_number_id"] #get business number from first message

                    #look for active conversations and send messages to recently logged agent
                    active_conversations = mgClient.find_active_conversations(data["business_number_id"], agent["role"], agent["id"])
                    print(active_conversations)

                    #send each message from active conversations to recently logged in agent
                    for conversation in active_conversations:
                        for message in conversation["messages"]:
                            stored_message: Whatsapp_msg_data = {
                                "business_phone_number": conversation["business_phone_number"],
                                "business_number_id": conversation["business_phone_number_id"],
                                "client_number": conversation["client_number"],
                                "client_profile_name": conversation["client_name"],
                                "message": message["body"],
                                "timestamp": message["sent_on"]
                            }

                            print(stored_message)
                            await agent["connection"].send_str(json.dumps(stored_message))



                if data["type"] == "message":
                    #search for the target conversation in mongo database
                    target_conversation = mgClient.find_conversation(data["client_number"], agent["business_number_id"])

                    #create message dictionary for storage
                    doc_msg: Message_doc = {
                        "sender": agent["id"],
                        "body": data["message"],
                        "sent_on": data["timestamp"],
                        "tag": "default"
                    }

                    #check if there is no agent assigned to the target conversation
                    if(target_conversation["assigned_agent"] == ""):
                        print(f"no assigned agent in conversation, {agent['id']} will be assigned")
                        wsClient.send_message(data["message"], data["client_number"], agent["business_number_id"])
                        mgClient.insert_message(doc_msg, data["client_number"], agent["business_number_id"], assigned_agent=agent["id"], status="ongoing")

                    #if there is an agent assigned to the target conversation, check if said agent is the one sending the message
                    if(target_conversation["assigned_agent"] == agent["id"]):
                        print(f" {agent['id']} is the assigned agent to this conversation")
                        wsClient.send_message(data["message"], data["client_number"], agent["business_number_id"])
                        mgClient.insert_message(doc_msg, data["client_number"], agent["business_number_id"])

                    #prevent message from being delivered if the assigned agent is different to the one trying to send the message
                    if(target_conversation["assigned_agent"] != "" and target_conversation["assigned_agent"] != agent["id"]):
                        print(f"{agent['id']} has no permission to answer this conversation")


        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' %
                  ws.exception())

    print('websocket connection closed')
    all_agents.remove(agent)
    return ws

application = Application()
application.add_routes(routes)

if __name__ == "__main__":
    application.run()