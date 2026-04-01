from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from api.firebase_utils import firebase_login_rest, reset_password, save_push_token
from api.dependencies import get_current_user

router = APIRouter()

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ResetRequest(BaseModel):
    email: EmailStr

class PushTokenRequest(BaseModel):
    push_token: str

@router.post("/login")
def login(body: LoginRequest):
    user = firebase_login_rest(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password, or role not assigned.")
    return user

@router.post("/reset-password")
def reset(body: ResetRequest):
    success = reset_password(body.email)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to send reset email.")
    return {"message": "Password reset email sent."}

@router.post("/push-token")
def register_push_token(body: PushTokenRequest, current_user: dict = Depends(get_current_user)):
    save_push_token(current_user["uid"], body.push_token)
    return {"message": "Push token saved."}

@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return {
        "uid": current_user["uid"],
        "email": current_user.get("email"),
        "role": current_user.get("role"),
    }
