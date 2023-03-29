from typing import TypedDict

class Whatsapp_msg(TypedDict):
    msg_type: str
    business_phone_number: str
    business_number_id: str
    client_number: str
    client_profile_name: str
    timestamp: str


class Whatsapp_txt_msg(Whatsapp_msg):
    message: str

class Whatsapp_img_msg(Whatsapp_msg):
    caption: str
    image_url: str
   

