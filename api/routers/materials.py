from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from api.firebase_utils import list_materials, upload_material_bytes
from api.dependencies import get_current_user

router = APIRouter()

@router.get("/")
def get_materials(current_user: dict = Depends(get_current_user)):
    uid = current_user["uid"]
    role = current_user["role"]
    # Teachers see their own; parents see teacher's materials (requires teacher_uid param ideally)
    # For now teachers see their own materials
    if role not in ["teacher", "parent", "admin"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    return list_materials(uid)

@router.post("/upload")
async def upload(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can upload materials.")
    content = await file.read()
    url = upload_material_bytes(content, file.filename, current_user["uid"], file.content_type or "application/octet-stream")
    if not url:
        raise HTTPException(status_code=500, detail="Upload failed.")
    return {"url": url, "name": file.filename}
