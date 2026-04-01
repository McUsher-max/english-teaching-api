from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
from api.firebase_utils import (
    get_assignments_by_teacher, get_assignment_detail, create_assignment,
    assign_to_students, get_assignments_for_student, get_all_assignment_submissions,
    submit_assignment_response, set_student_score,
    upload_assignment_bytes, upload_submission_bytes, get_students_for_parent
)
from api.dependencies import get_current_user

router = APIRouter()

class AssignmentCreate(BaseModel):
    title: str
    description: str
    dueDate: str
    studentIDs: List[str]
    material_url: Optional[str] = None

class ScoreUpdate(BaseModel):
    student_id: str
    score: int

@router.get("/")
def list_assignments(current_user: dict = Depends(get_current_user)):
    role = current_user["role"]
    uid = current_user["uid"]
    email = current_user.get("email")

    if role == "teacher":
        return get_assignments_by_teacher(uid)
    elif role == "parent":
        # Get all children then aggregate their assignments
        children = get_students_for_parent(email)
        result = []
        for child in children:
            for sa in get_assignments_for_student(child["id"]):
                detail = get_assignment_detail(sa["assignmentID"])
                if detail:
                    result.append({**sa, "assignment": detail, "studentName": child.get("Name")})
        return result
    elif role == "admin":
        from api.firebase_utils import get_all_assignments
        return get_all_assignments()
    raise HTTPException(status_code=403, detail="Access denied.")

@router.get("/{assignment_id}")
def get_assignment(assignment_id: str, current_user: dict = Depends(get_current_user)):
    detail = get_assignment_detail(assignment_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Assignment not found.")
    return detail

@router.post("/")
def create(body: AssignmentCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can create assignments.")
    data = body.model_dump(exclude={"studentIDs"})
    assignment_id = create_assignment(current_user["uid"], data)
    assign_to_students(assignment_id, body.studentIDs)
    return {"id": assignment_id, "message": "Assignment created."}

@router.post("/upload-material")
async def upload_material(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can upload materials.")
    content = await file.read()
    url = upload_assignment_bytes(content, file.filename, file.content_type or "application/octet-stream")
    if not url:
        raise HTTPException(status_code=500, detail="File upload failed.")
    return {"url": url, "filename": file.filename}

@router.get("/{assignment_id}/submissions")
def get_submissions(assignment_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    return get_all_assignment_submissions(assignment_id)

@router.post("/{assignment_id}/submit")
async def submit(
    assignment_id: str,
    student_id: str = Form(...),
    text_response: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    if current_user["role"] not in ["parent", "teacher"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    file_url = None
    if file:
        content = await file.read()
        file_url = upload_submission_bytes(content, file.filename, file.content_type or "application/octet-stream")
        if not file_url:
            raise HTTPException(status_code=500, detail="File upload failed.")
    submit_assignment_response(assignment_id, student_id, file_url, text_response)
    return {"message": "Assignment submitted."}

@router.put("/{assignment_id}/score")
def grade(assignment_id: str, body: ScoreUpdate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can grade assignments.")
    set_student_score(assignment_id, body.student_id, body.score)
    return {"message": "Score saved."}
