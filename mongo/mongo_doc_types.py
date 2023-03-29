from typing import TypedDict, List


class Msg_doc(TypedDict):
    sender: str
    sender_is_business: bool
    sent_on: str
    tag: str

class Txt_msg_doc(Msg_doc):
    body: str

class Img_msg_doc(Msg_doc):
    caption: str
    image_url: str


class Notification_doc(TypedDict):
    type: str
    sent_on: str
    body: str


class Converstaion_doc(TypedDict):
    business_phone_number: str
    business_number_id: str
    client_name: str
    client_number: str
    assigned_agent: str
    status: str
    date: str
    messages: List
