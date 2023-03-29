import os
import requests
from whatsapp.whatsapp_data_types import Whatsapp_txt_msg, Whatsapp_img_msg
from dotenv import load_dotenv

import json
import boto3



load_dotenv()

class WhatsAppWrapper:

    API_URL = "https://graph.facebook.com/v15.0/"
    API_TOKEN = os.environ.get("WHATSAPP_API_TOKEN")
    NUMBER_ID = os.environ.get("WHATSAPP_NUMBER_ID")
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {self.API_TOKEN}",
            "Content-Type": "application/json",
        }
        
        self.s3Client = boto3.client('s3')

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
        data = "not a message"
        if "messages" in body_data:
            
            if (body_data["messages"][0]["type"] == "text"):
                #data: Whatsapp_txt_msg = {
                data = {
                    "msg_type": "txt",
                    "business_phone_number": body_data["metadata"]["display_phone_number"],
                    "business_number_id": body_data["metadata"]["phone_number_id"],
                    "client_number": body_data["contacts"][0]["wa_id"],
                    "client_profile_name": body_data["contacts"][0]["profile"]["name"],
                    "message" : body_data["messages"][0]["text"]["body"],
                    "timestamp": body_data["messages"][0]["timestamp"]
                }

            if (body_data["messages"][0]["type"] == "image"):
                
                media_id = body_data["messages"][0]["image"]["id"]

                response_i = requests.request("GET", f"{self.API_URL}{media_id}/", headers=self.headers)
                
                req_body = json.loads(response_i.content)

                response_ii = requests.request("GET", f"{req_body['url']}/", headers=self.headers)

                with open(f'{media_id}.jpg', "wb") as f:
                    f.write(response_ii.content)
                
                self.s3Client.upload_file(f"{media_id}.jpg", self.S3_BUCKET_NAME, f"images/{media_id}.jpg")

                image_url = f"https://{self.S3_BUCKET_NAME}.s3.amazonaws.com/images/{media_id}.jpg"

                if os.path.exists(f"{media_id}.jpg"):
                    os.remove(f"{media_id}.jpg")
                
                #data: Whatsapp_img_msg = {
                data = {
                    "msg_type": "img",
                    "business_phone_number": body_data["metadata"]["display_phone_number"],
                    "business_number_id": body_data["metadata"]["phone_number_id"],
                    "client_number": body_data["contacts"][0]["wa_id"],
                    "client_profile_name": body_data["contacts"][0]["profile"]["name"],
                    "caption" : body_data["messages"][0]["image"]["caption"],
                    "image_url": image_url,
                    "timestamp": body_data["messages"][0]["timestamp"]

                }

        
        
        return data
        
        
