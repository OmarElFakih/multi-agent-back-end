from pymongo import mongo_client
from mongo.mongo_doc_types import Converstaion_doc
from whatsapp.whatsapp_data_types import Whatsapp_msg
from bson import json_util
import re
import datetime



 

class MongoWrapper:

    def __init__(self, connection_string, database_name):
        self.client = mongo_client.MongoClient(connection_string)
        self.db = self.client.get_database(database_name)
        #self.conversations = self.db.conversations
        self.conversations = self.db.testing_conversations
        
    def string_date(self, datetime_obj: datetime.datetime):
        date_string = datetime_obj.strftime("%d-%m-%Y")
        print(date_string)
        return date_string

    def get_metrics(self, business_phone_number_id: str):
        tomorrow = datetime.datetime.today() + datetime.timedelta(days=1)
        docs = self.conversations.find({"business_phone_number_id" : business_phone_number_id, "status": "terminated"})
        #doc_arr = []

        # for document in docs:
        #     date = datetime.datetime.fromtimestamp(int(document["date"]))
        #     doc_arr.append(date)

        date_pointer = datetime.datetime.fromtimestamp(int(docs[0]["date"]))
        total_conv_data = []
        total_agent_data = []


        # print(self.string_date(date_pointer))
        # print(self.string_date(tomorrow))

        while self.string_date(date_pointer) != self.string_date(tomorrow):
            conv_data = {
                "id": self.string_date(date_pointer),
                "conversations": 0
            }

            #current agent names are for Demo pourposes, Agent names must be aquired from external DB onn future iterations
            agent_data = {
                "id": self.string_date(date_pointer),
                "agents": {
                    "Agent01": 0,
                    "Agent02": 0,
                    "Admin01": 0,
                    "Admin02": 0
                }
            }

            for document in docs:
                
                
                
                doc_date = datetime.datetime.fromtimestamp(int(document["date"]))

                if self.string_date(doc_date) == self.string_date(date_pointer):
                    conv_data["conversations"] += 1

                    agent_data["agents"][document["assigned_agent"]] += 1

                

            total_conv_data.append(conv_data)
            total_agent_data.append(agent_data)

            date_pointer += datetime.timedelta(days = 1)

        metrics = {
            "num_of_conversations": total_conv_data,
            "agent_performance": total_agent_data
        }

        return metrics
    

    def get_history(self, business_phone_number_id: str, assigned_agent="", client_name="", date=""):
        query = {"business_phone_number_id": business_phone_number_id}

        if(assigned_agent != ""):
            query["assigned_agent"] = assigned_agent

        if(client_name != ""):
            query["client_name"] = client_name

        docs = self.conversations.find(query)

        filter_docs = []

    

        for document in docs:
            doc_date = datetime.datetime.fromtimestamp(int(document["date"]))

            if (self.string_date(doc_date) == date or date == ""):
                filter_docs.append(document)
        
        
        return json_util.dumps(filter_docs)
        
        
                


    def find_conversation(self, client_number: str, business_phone_number_id: str):
        query = {"client_number": client_number,
                 "business_phone_number_id": business_phone_number_id,
                 "status": {"$not": re.compile("terminated")}    
                }
        
        return self.conversations.find_one(query)
    
    
    def find_active_conversations(self, business_phone_number_id: str, agent_role, agent_id):
        query = {
                 "business_phone_number_id": business_phone_number_id,
                 "status": {"$not": re.compile("terminated")}   
                }


        found_conversations =  self.conversations.find(query)
        
        if agent_role == "admin": 
            return found_conversations
        else:
            filtered_conversations = filter(lambda conversation: conversation["assigned_agent"] == agent_id or conversation["status"] == "on hold" , found_conversations)
            return filtered_conversations


    def insert_conversation(self, data: dict, sender: str, sender_is_business: bool):

        message = self.build_msg_doc(data, sender, sender_is_business)


        new_conversation: Converstaion_doc = {
            "business_phone_number": data["business_phone_number"],
            "business_phone_number_id": data["business_number_id"],
            "client_name": data["client_profile_name"],
            "client_number": data["client_number"],
            "assigned_agent": "none",
            "status": "on hold",
            "date": data["timestamp"],
            "messages": [message] 
            
            }
        
        self.conversations.insert_one(new_conversation)


    def insert_message(self, data: dict, sender: str, sender_is_business: bool, conversation_id):
        # query = {"client_number": client_number,
        #          "business_phone_number_id": business_phone_number_id,
        #          "status": {"$not": re.compile("terminated")}    
        #         }

        query = {"_id": conversation_id,
                 "status": {"$not": re.compile("terminated")}
                }
        
        message = self.build_msg_doc(data, sender, sender_is_business)
        
        new_values = {"$push": {"messages": message}}

        # if(status != ""):
        #     new_values["$set"]["status"] = status

        # if(assigned_agent != ""):
        #     new_values["$set"]["assigned_agent"] = assigned_agent
            
        self.conversations.update_one(query, new_values)


    def update_values(self, client_number: str, business_phone_number_id: str, value_dict: dict):
        query = {"client_number": client_number,
                 "business_phone_number_id": business_phone_number_id,
                 "status": {"$not": re.compile("terminated")}    
                }
        
        new_values = {"$set" : value_dict}
        
        self.conversations.update_one(query, new_values)


    def build_msg_doc(self, message_data: dict, sender: str, sender_is_business: bool):
        msg_doc = {
            "sender": sender,
            "sender_is_business": sender_is_business,
            "sent_on": message_data["timestamp"],
            "tag": "default"
        }

        if (message_data["msg_type"] == "txt"):
            msg_doc["body"] = message_data["message"]
            msg_doc["msg_type"] = "txt"

        if (message_data["msg_type"] == "img"):
            msg_doc["caption"] = message_data["caption"]
            msg_doc["image_url"] = message_data["image_url"]
            msg_doc["msg_type"] = "img"

        return msg_doc
    


    
    
