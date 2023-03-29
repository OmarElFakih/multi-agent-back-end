import os
import time
import aiohttp
from whatsapp.whatsapp_client import WhatsAppWrapper
# from whatsapp.whatsapp_data_types import Whatsapp_msg_data
from mongo.mongo_client import MongoWrapper
from mongo.mongo_doc_types import Txt_msg_doc, Img_msg_doc, Notification_doc
from dotenv import load_dotenv
import json

from aiohttp import web
#from aio.aplication import Application
routes = web.RouteTableDef()

load_dotenv()
all_agents = []




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

    print(f"data is {data}")
    
    message_data = wsClient.request_data(data)

    doc_msg = {}

    if(message_data != "not a message"):
        print(f"message data is: {message_data}")
        converstaion = mgClient.find_conversation(message_data["client_number"], message_data["business_number_id"])

        if converstaion == None:
            
            await send_agents(message_data)
            mgClient.insert_conversation(message_data, message_data["client_profile_name"], sender_is_business=False)

        else: 
            await send_agents(message_data, converstaion["assigned_agent"])
            
            if(message_data["msg_type"] == "txt"):

                doc_msg: Txt_msg_doc = {
                    "sender": message_data["client_profile_name"],
                    "sender_is_business": False,
                    "body": message_data["message"],
                    "sent_on": message_data["timestamp"],
                    "tag": "default"
                }
            
            if(message_data["msg_type"] == "img"):
                
                doc_msg: Img_msg_doc = {
                    "sender": message_data["client_profile_name"],
                    "sender_is_business": False,
                    "caption": message_data["caption"],
                    "image_url": message_data["image_url"],
                    "sent_on": message_data["timestamp"],
                    "tag": "default"
                }

            mgClient.insert_message(doc_msg, message_data["client_number"], message_data["business_number_id"])


    
    return web.Response(text="success")


@routes.get('/ws')
async def websocket_handler(request):

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    
    agent = {
        "id": "",
        "connection": ws,
        "role": "",
        "business_number_id": ""    
    }

    all_agents.append(agent)
    print("client connected")

    

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                
                
                print(data)
                
                if data["type"] == "connection": 
                    print("connection")
                    agent["id"] = data["id"]
                    agent["role"] = data["role"]
                    agent["business_number_id"] = data["business_number_id"] #get user data from first message

                    print(agent)

                    #look for active conversations and send messages to recently logged agent
                    active_conversations = mgClient.find_active_conversations(data["business_number_id"], agent["role"], agent["id"])
                    

                    #send each message from active conversations to recently logged in agent
                    for conversation in active_conversations:
                        for message in conversation["messages"]:
                            stored_message = {
                                "business_phone_number": conversation["business_phone_number"],
                                "business_number_id": conversation["business_phone_number_id"],
                                "client_number": conversation["client_number"],
                                "client_profile_name": conversation["client_name"],
                                #"message": message["body"],
                                "timestamp": message["sent_on"],
                                "sender_is_business": message["sender_is_business"]
                            }

                            if("body" in message):
                                stored_message["message"] = message["body"]
                            
                            if("image_url" in message):
                                stored_message["caption"] = message["caption"]
                                stored_message["image_url"] = message["image_url"]

                            print(stored_message)
                            await agent["connection"].send_str(json.dumps(stored_message))
                            time.sleep(.2)



                if data["type"] == "message":
                    #search for the target conversation in mongo database
                    target_conversation = mgClient.find_conversation(data["client_number"], agent["business_number_id"])

                    #create message dictionary for storage
                    doc_msg: Txt_msg_doc = {
                        "sender": agent["id"],
                        "sender_is_business": True,
                        "body": data["message"],
                        "sent_on": data["timestamp"],
                        "tag": "default"
                    }

                    #check if there is no agent assigned to the target conversation
                    if(target_conversation["assigned_agent"] == ""):
                        print(f"no assigned agent in conversation, {agent['id']} will be assigned")
                        wsClient.send_message(data["message"], data["client_number"], agent["business_number_id"])
                        mgClient.insert_message(doc_msg, data["client_number"], agent["business_number_id"])
                        mgClient.update_values(data["client_number"], agent["business_number_id"], {"status": "ongoing", "assigned_agent": agent["id"]})

                    #if there is an agent assigned to the target conversation, check if said agent is the one sending the message
                    if(target_conversation["assigned_agent"] == agent["id"]):
                        print(f" {agent['id']} is the assigned agent to this conversation")
                        wsClient.send_message(data["message"], data["client_number"], agent["business_number_id"])
                        mgClient.insert_message(doc_msg, data["client_number"], agent["business_number_id"])

                    #prevent message from being delivered if the assigned agent is different to the one trying to send the message
                    if(target_conversation["assigned_agent"] != "" and target_conversation["assigned_agent"] != agent["id"]):
                        print(f"{agent['id']} has no permission to answer this conversation")


                if data["type"] == "notification":
                    noti_conversation = mgClient.find_conversation(data["client_number"], agent["business_number_id"])
                    if (noti_conversation["assigned_agent"] == agent["id"]):
                        noti_doc: Notification_doc = {
                            "type": data["noti_type"],
                            "sent_on": data["timestamp"],
                            "body": data["body"]
                        }

                        mgClient.insert_message(noti_doc, data["client_number"], agent["business_number_id"])

                        if(data["noti_type"] == "termination"):
                            mgClient.update_values(data["client_number"], agent["business_number_id"], {"status": "terminated"})
                            
                            noti_data = {
                                "type": "notification",
                                "body": "Conversation Terminated",
                                "client_number": data["client_number"]
                            }

                            await agent["connection"].send_str(json.dumps(noti_data))



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