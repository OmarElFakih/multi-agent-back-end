from typing import TypedDict

class Whatsapp_msg_data(TypedDict):
    business_phone_number: str
    business_number_id: str
    client_number: str
    client_profile_name: str
    message : str
    timestamp: str