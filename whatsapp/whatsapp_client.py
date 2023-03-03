import os
import requests
from whatsapp.whatsapp_data_types import Whatsapp_msg_data
from dotenv import load_dotenv

import json

load_dotenv()

class WhatsAppWrapper:

    API_URL = "https://graph.facebook.com/v15.0/"
    API_TOKEN = os.environ.get("WHATSAPP_API_TOKEN")
    NUMBER_ID = os.environ.get("WHATSAPP_NUMBER_ID")

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {self.API_TOKEN}",
            "Content-Type": "application/json",
        }
        #self.API_URL = self.API_URL + self.NUMBER_ID

    def send_template_message(self, template_name, language_code, phone_number):
        payload = json.dumps({
            "messaging_product": "whatsapp",
            "to": phone_number,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        })

        response = requests.request("POST", f"{self.API_URL}/messages", headers=self.headers, data=payload)

        assert response.status_code == 200, "Error sending message"

        return response.status_code

    def send_message(self, body, phone_number, business_number_id):
        payload = json.dumps({
            "messaging_product": "whatsapp",    
            "recipient_type": "individual",
            "to": phone_number,
            "type": "text",
            "text": {
            "preview_url": False,
            "body": body
            }
        })

        response = requests.request("POST", f"{self.API_URL}{business_number_id}/messages", headers=self.headers, data=payload)

        assert response.status_code == 200, "Error sending message"

        return response.status_code
    
    def request_data(self, body):
        body_data = body["entry"][0]["changes"][0]["value"]

        if "messages" in body_data:
            data: Whatsapp_msg_data = {
                "business_phone_number": body_data["metadata"]["display_phone_number"],
                "business_number_id": body_data["metadata"]["phone_number_id"],
                "client_number": body_data["contacts"][0]["wa_id"],
                "client_profile_name": body_data["contacts"][0]["profile"]["name"],
                "message" : body_data["messages"][0]["text"]["body"],
                "timestamp": body_data["messages"][0]["timestamp"]
            }

            return data
        
        else:
            return "not a message"
