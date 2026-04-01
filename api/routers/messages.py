from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from api.firebase_utils import send_message, get_messages_for_user
from api.dependencies import get_current_user

router = APIRouter()

class MessageCreate(BaseModel):
    recipient_email: EmailStr
    message: str

@router.get("/")
def get_messages(current_user: dict = Depends(get_current_user)):
    email = current_user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email not found in token.")
    return get_messages_for_user(email)

@router.post("/")
def create_message(body: MessageCreate, current_user: dict = Depends(get_current_user)):
    sender_email = current_user.get("email")
    if not sender_email:
        raise HTTPException(status_code=400, detail="Sender email not found.")
    send_message(body.recipient_email, sender_email, body.message)
    return {"message": "Message sent."}
