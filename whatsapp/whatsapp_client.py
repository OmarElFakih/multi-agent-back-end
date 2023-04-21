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

    ACCESS_KEY= os.environ.get("ACCESS_KEY")
    SECRET_KEY= os.environ.get("SECRET_KEY")
    S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")

    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {self.API_TOKEN}",
            "Content-Type": "application/json",
        }
        
        self.s3Client = boto3.client('s3', 
                                    aws_access_key_id=self.ACCESS_KEY,
                                    aws_secret_access_key=self.SECRET_KEY
                                     )

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
            data = {
                    "msg_type": "",
                    "business_phone_number": body_data["metadata"]["display_phone_number"],
                    "business_number_id": body_data["metadata"]["phone_number_id"],
                    "client_number": body_data["contacts"][0]["wa_id"],
                    "client_profile_name": body_data["contacts"][0]["profile"]["name"],
                    "assigned_agent": "", 
                    "timestamp": body_data["messages"][0]["timestamp"],
                    "sender_is_business": False
                }


            
            if (body_data["messages"][0]["type"] == "text"):
                data["msg_type"] = "txt"
                data["message"] = body_data["messages"][0]["text"]["body"]
                #data: Whatsapp_txt_msg = {
                # data = {
                #     "msg_type": "txt",
                #     "business_phone_number": body_data["metadata"]["display_phone_number"],
                #     "business_number_id": body_data["metadata"]["phone_number_id"],
                #     "client_number": body_data["contacts"][0]["wa_id"],
                #     "client_profile_name": body_data["contacts"][0]["profile"]["name"], 
                #     "timestamp": body_data["messages"][0]["timestamp"],
                #     "message" : body_data["messages"][0]["text"]["body"],
                # }

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

                caption = ""
                
                if("caption" in body_data["messages"][0]["image"]):
                    caption = body_data["messages"][0]["image"]["caption"]

                data["msg_type"] = "img"
                data["caption"] = caption
                data["image_url"] = image_url

                # data = {
                #     "msg_type": "img",
                #     "business_phone_number": body_data["metadata"]["display_phone_number"],
                #     "business_number_id": body_data["metadata"]["phone_number_id"],
                #     "client_number": body_data["contacts"][0]["wa_id"],
                #     "client_profile_name": body_data["contacts"][0]["profile"]["name"],
                #     "timestamp": body_data["messages"][0]["timestamp"],
                #     "caption" : caption,
                #     "image_url": image_url,
                    

                # }

        
        
        return data
        
        
