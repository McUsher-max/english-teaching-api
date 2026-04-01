from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from api.firebase_utils import (
    get_parents_by_teacher, add_parent, update_parent,
    delete_parent, get_parent_by_email, get_all_parents
)
from api.dependencies import get_current_user

router = APIRouter()

class ParentCreate(BaseModel):
    Name: str
    Email: str
    TeacherUID: List[str]
    ChildrenUIDs: List[str] = []

class ParentUpdate(BaseModel):
    Name: Optional[str] = None
    Email: Optional[str] = None
    ChildrenUIDs: Optional[List[str]] = None

@router.get("/")
def list_parents(current_user: dict = Depends(get_current_user)):
    role = current_user["role"]
    if role == "teacher":
        return get_parents_by_teacher(current_user["uid"])
    elif role == "admin":
        return get_all_parents()
    raise HTTPException(status_code=403, detail="Access denied.")

@router.post("/")
def create_parent(body: ParentCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers or admins can create parents.")
    parent_id = add_parent(body.model_dump())
    return {"id": parent_id, "message": "Parent created."}

@router.put("/{parent_id}")
def edit_parent(parent_id: str, body: ParentUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")
    update_parent(parent_id, updates)
    return {"message": "Parent updated."}

@router.delete("/{parent_id}")
def remove_parent(parent_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    delete_parent(parent_id)
    return {"message": "Parent deleted."}
