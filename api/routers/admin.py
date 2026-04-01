from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from api.firebase_utils import (
    create_firebase_user, list_users, update_user_role,
    disable_user_account, get_all_teachers, get_all_students,
    get_all_parents, get_all_assignments
)
from api.dependencies import get_current_user

router = APIRouter()

def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user

class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = "teacher"

class UpdateRoleRequest(BaseModel):
    role: str

class DisableRequest(BaseModel):
    disabled: bool = True

@router.get("/stats")
def stats(current_user: dict = Depends(require_admin)):
    teachers = get_all_teachers()
    students = get_all_students()
    parents = get_all_parents()
    assignments = get_all_assignments()
    return {
        "teachers": len(teachers),
        "students": len(students),
        "parents": len(parents),
        "assignments": len(assignments),
    }

@router.get("/users")
def get_users(current_user: dict = Depends(require_admin)):
    return list_users()

@router.post("/users")
def create_user(body: CreateUserRequest, current_user: dict = Depends(require_admin)):
    uid = create_firebase_user(body.email, body.password, body.role)
    return {"uid": uid, "message": f"User created with role '{body.role}'."}

@router.put("/users/{user_id}/role")
def change_role(user_id: str, body: UpdateRoleRequest, current_user: dict = Depends(require_admin)):
    update_user_role(user_id, body.role)
    return {"message": "Role updated."}

@router.put("/users/{user_id}/disable")
def toggle_disable(user_id: str, body: DisableRequest, current_user: dict = Depends(require_admin)):
    disable_user_account(user_id, body.disabled)
    return {"message": f"User {'disabled' if body.disabled else 'enabled'}."}
