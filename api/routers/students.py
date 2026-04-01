from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from api.firebase_utils import (
    get_students_by_teacher, get_student_by_id, add_student,
    update_student, delete_student, get_students_for_parent, get_all_students
)
from api.dependencies import get_current_user

router = APIRouter()

class StudentCreate(BaseModel):
    Name: str
    Grade: Optional[str] = None
    ParentUID: Optional[str] = None
    Remarks: Optional[List[dict]] = []

class StudentUpdate(BaseModel):
    Name: Optional[str] = None
    Grade: Optional[str] = None
    ParentUID: Optional[str] = None
    Remarks: Optional[List[dict]] = None

@router.get("/")
def list_students(current_user: dict = Depends(get_current_user)):
    role = current_user["role"]
    uid = current_user["uid"]
    email = current_user.get("email")

    if role == "teacher":
        return get_students_by_teacher(uid)
    elif role == "parent":
        return get_students_for_parent(email)
    elif role == "admin":
        return get_all_students()
    raise HTTPException(status_code=403, detail="Access denied.")

@router.get("/{student_id}")
def get_student(student_id: str, current_user: dict = Depends(get_current_user)):
    student = get_student_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found.")
    return student

@router.post("/")
def create_student(body: StudentCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers or admins can create students.")
    teacher_uid = current_user["uid"]
    student_id = add_student(teacher_uid, body.model_dump(exclude_none=True))
    return {"id": student_id, "message": "Student created."}

@router.put("/{student_id}")
def edit_student(student_id: str, body: StudentUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers or admins can edit students.")
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")
    update_student(student_id, updates)
    return {"message": "Student updated."}

@router.delete("/{student_id}")
def remove_student(student_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers or admins can delete students.")
    delete_student(student_id)
    return {"message": "Student deleted."}
