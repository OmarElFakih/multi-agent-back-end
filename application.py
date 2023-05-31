import os
import time
import aiohttp
import aiohttp_cors
from whatsapp.whatsapp_client import WhatsAppWrapper
# from whatsapp.whatsapp_data_types import Whatsapp_msg_data
from mongo.mongo_client import MongoWrapper
from s3.s3Client import S3Wrapper
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

s3Client = S3Wrapper()
wsClient = WhatsAppWrapper(s3Client)
mgClient = MongoWrapper(MONGODB_ATLAS_CONNECTION_STRING, MONGODB_ATLAS_DATABASE_NAME)

class Application(web.Application):
    def __init__(self):
        super().__init__()

    def run(self):
        cors_defaults = {
            '*': aiohttp_cors.ResourceOptions(
                max_age = 3600,
                allow_methods = '*',
                allow_headers = '*',
                expose_headers = '*',
                allow_credentials = True,
            )
        }
        cors = aiohttp_cors.setup(self, defaults=cors_defaults)

        for route in self.router.routes():
            cors.add(route)
        return web.run_app(self, port=8000)


async def send_agents(message, target_agent="", sender_agent=""):
    for agent in all_agents:
        if agent["business_number_id"] == message["business_number_id"]:
            if(((agent["role"] == "admin") or (agent["id"] == target_agent) or (target_agent == "")) and (agent["id"] != sender_agent)):
                print(f"sender_agent: {sender_agent}")
                print(f"agent_id: {agent['id']}")
                await agent["connection"].send_str(json.dumps(message))

@routes.get('/')
async def hello(request):
    return web.Response(text="visualizacion de agente asignado desde el front end")


@routes.get('/webhook')
async def verify_webhook(request):

    if request.query["hub.verify_token"] == VERIFY_TOKEN:
        return web.Response(text=request.query["hub.challenge"])
    
    return "Authentication failed. Invalid Token."


@routes.post('/webhook')
async def webhook_notification(request):
    data = await request.json()

    print(f"data is {data}")
    
    message_data = wsClient.request_data(data)

    if(message_data != "not a message"):
        print(f"message data is: {message_data}")

        converstaion = mgClient.find_conversation(message_data["client_number"], message_data["business_number_id"])

        if converstaion == None:
            message_data["assigned_agent"] = "none"
            print(f"sending {message_data}")
            await send_agents(message_data)
            mgClient.insert_conversation(message_data, message_data["client_profile_name"], sender_is_business=False)

        else: 
            message_data["assigned_agent"] = converstaion["assigned_agent"]

            await send_agents(message_data, converstaion["assigned_agent"])
            mgClient.insert_message(message_data, message_data["client_profile_name"], sender_is_business=False, conversation_id=converstaion["_id"])
    
    return web.Response(text="success")

@routes.get('/metrics')
async def get_metrics(request):
    req_data = await request.json()
    metrics_data = mgClient.get_metrics(req_data["business_phone_number_id"])

    return web.Response(text=json.dumps(metrics_data))
    #return web.Response(text=req_data["business_phone_number_id"])

@routes.get('/history')
async def get_history(request):
    # req_data = await request.json()
    # print(req_data)
    params = {
        "business_phone_number_id": request.rel_url.query["business_phone_number_id"],
        "assigned_agent": request.rel_url.query["assigned_agent"],
        "client_name": request.rel_url.query["client_name"],
        "date": request.rel_url.query["date"]
    }


    
    print(params)

    history = mgClient.get_history(params["business_phone_number_id"], params["assigned_agent"], params["client_name"], params["date"])

    #history = params
    # print(history)
    #jhistory = json.dumps(history)
    return web.Response(text=history)


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
                
                
                # print(data)
                
                if data["msg_type"] == "connection": 
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
                                "msg_type": message["msg_type"],
                                "business_phone_number": conversation["business_phone_number"],
                                "business_number_id": conversation["business_phone_number_id"],
                                "client_number": conversation["client_number"],
                                "client_profile_name": conversation["client_name"],
                                "assigned_agent": conversation["assigned_agent"],
                                "timestamp": message["sent_on"],
                                "sender_is_business": message["sender_is_business"]
                                
                            }

                            if("body" in message):
                                stored_message["body"] = message["body"]
                            
                            if("image_url" in message):
                                stored_message["caption"] = message["caption"]
                                stored_message["image_url"] = message["image_url"]

                            print(stored_message)
                            await agent["connection"].send_str(json.dumps(stored_message))
                            time.sleep(.3)



                if data["msg_type"] == "msg":
                    #search for the target conversation in mongo database
                    target_conversation = mgClient.find_conversation(data["client_number"], agent["business_number_id"])

                    data["msg_type"] = "txt"

                    #create message dictionary for storage
                    msg_data = {
                        "msg_type": "txt",
                        "body": data["body"],
                        "timestamp": data["timestamp"],
                    }

                    #check if there is no agent assigned to the target conversation
                    if(target_conversation["assigned_agent"] == "none"):
                        print(f"no assigned agent in conversation, {agent['id']} will be assigned")
                        wsClient.send_message(data["body"], data["client_number"], agent["business_number_id"])
                        mgClient.insert_message(msg_data, agent["id"], sender_is_business=True, conversation_id=target_conversation["_id"])
                        mgClient.update_values(data["client_number"], agent["business_number_id"], {"status": "ongoing", "assigned_agent": agent["id"]})

                        noti_data = {
                            "type": "assignment",
                            "body": f"Conversation assigned to {agent['id']}",
                            "assigned_agent": agent["id"],
                            "client_number": data["client_number"],
                            "business_number_id": agent["business_number_id"],
                            "isNoti": True
                        }

                        await send_agents(noti_data)
                        await send_agents(data, target_agent="admins_only", sender_agent=agent["id"])
                        
                        
                    

                    #if there is an agent assigned to the target conversation, check if said agent is the one sending the message
                    if(target_conversation["assigned_agent"] == agent["id"]):
                        print(f" {agent['id']} is the assigned agent to this conversation")
                        wsClient.send_message(data["body"], data["client_number"], agent["business_number_id"])
                        await send_agents(data, target_agent="admins_only", sender_agent=agent["id"])
                        mgClient.insert_message(msg_data, agent["id"], sender_is_business=True, conversation_id=target_conversation["_id"])

                    #prevent message from being delivered if the assigned agent is different to the one trying to send the message
                    if(target_conversation["assigned_agent"] != "none" and target_conversation["assigned_agent"] != agent["id"]):
                        print(f"{agent['id']} has no permission to answer this conversation")


                if data["msg_type"] == "notification":
                    noti_conversation = mgClient.find_conversation(data["client_number"], agent["business_number_id"])
                    if (noti_conversation["assigned_agent"] == agent["id"]):
                        # noti_doc: Notification_doc = {
                        #     "type": data["noti_type"],
                        #     "sent_on": data["timestamp"],
                        #     "body": data["body"]
                        # }

                        # mgClient.insert_message(noti_doc, data["client_number"], agent["business_number_id"])

                        if(data["noti_type"] == "termination"):
                            mgClient.update_values(data["client_number"], agent["business_number_id"], {"status": "terminated"})
                            
                            noti_data = {
                                "type": "termination",
                                "body": "Conversation Terminated",
                                "client_number": data["client_number"],
                                "isNoti": True
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