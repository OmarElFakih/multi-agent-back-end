from pymongo import mongo_client
from mongo.mongo_doc_types import Message_doc, Converstaion_doc
from whatsapp.whatsapp_data_types import Whatsapp_msg_data
import re



 

class MongoWrapper:

    def __init__(self, connection_string, database_name):
        self.client = mongo_client.MongoClient(connection_string)
        self.db = self.client.get_database(database_name)
        self.conversations = self.db.conversations
        


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

        #query["status"] = {"$not": re.compile("terminated")} if (agent_role == "admin") else "on hold"

        found_conversations =  self.conversations.find(query)
        
        if agent_role == "admin": 
            return found_conversations
        else:
            filtered_conversations = filter(lambda conversation: conversation["assigned_agent"] == agent_id or conversation["status"] == "on hold" , found_conversations)
            return filtered_conversations


    def insert_conversation(self, data: Whatsapp_msg_data, sender: str):

        

        new_conversation: Converstaion_doc = {
            "business_phone_number": data["business_phone_number"],
            "business_phone_number_id": data["business_number_id"],
            "client_name": data["client_profile_name"],
            "client_number": data["client_number"],
            "assigned_agent": "",
            "status": "on hold",
            "date": data["timestamp"],
            "messages": [{
                            "sender": sender,
                            "body": data["message"],
                            "sent_on": data["timestamp"],
                            "tag": "default"
                        }] 
            
            }
        
        self.conversations.insert_one(new_conversation)


    def insert_message(self, message : Message_doc, client_number: str, business_phone_number_id: str, assigned_agent="", status=""):
        query = {"client_number": client_number,
                 "business_phone_number_id": business_phone_number_id,
                 "status": {"$not": re.compile("terminated")}    
                }
        
        new_values = {"$push": {"messages": message},
                      "$set": {}
                    }

        if(status != ""):
            new_values["$set"]["status"] = status

        if(assigned_agent != ""):
            new_values["$set"]["assigned_agent"] = assigned_agent
            
        self.conversations.update_one(query, new_values)


    def update_status(self, client_number: str, business_phone_number_id: str, status: str):
        query = {"client_number": client_number,
                 "business_phone_number_id": business_phone_number_id,
                 "status": {"$not": re.compile("terminated")}    
                }
        
        self.conversations.update_one(query, {"status": status})
    


    
    
