from typing import TypedDict, List


class Message_doc(TypedDict):
    sender: str
    body: str
    sent_on: str
    tag: str


class Converstaion_doc(TypedDict):
    business_phone_number: str
    business_number_id: str
    client_name: str
    client_number: str
    assigned_agent: str
    status: str
    date: str
    messages: List[Message_doc]
