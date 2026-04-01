import uuid
import os
import firebase_admin
import mimetypes
import requests
from firebase_admin import credentials, auth, firestore
from datetime import datetime, timezone
from supabase import create_client, Client

# ---------------------- Firebase Initialization ----------------------
if not firebase_admin._apps:
    cred_path = os.getenv("FIREBASE_CREDENTIALS")
    if cred_path:
        cred = credentials.Certificate(cred_path)
    else:
        # Support inline JSON credentials (Railway / Render env var)
        import json
        cred_json = os.getenv("FIREBASE_CREDENTIALS_JSON")
        if cred_json:
            cred = credentials.Certificate(json.loads(cred_json))
        else:
            raise ValueError("No Firebase credentials found. Set FIREBASE_CREDENTIALS or FIREBASE_CREDENTIALS_JSON.")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------------- Supabase Initialization ----------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET_NAME")
ASSIGNMENTS_BUCKET = os.getenv("SUPABASE_ASSIGNMENTS_BUCKET")
MATERIALS_BUCKET = os.getenv("SUPABASE_MATERIALS_BUCKET")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------- Validation Helpers ----------------------
def validate_user_data(user_data):
    required = ["email", "role"]
    for key in required:
        if key not in user_data or not user_data[key]:
            raise ValueError(f"Missing or empty field: {key}")
    if user_data["role"] not in ["admin", "teacher", "parent"]:
        raise ValueError("Invalid role")

def validate_student_data(student_data):
    required = ["Name", "TeacherUID"]
    for key in required:
        if key not in student_data or not student_data[key]:
            raise ValueError(f"Missing or empty field: {key}")

def validate_parent_data(parent_data):
    required = ["Name", "Email", "TeacherUID", "ChildrenUIDs"]
    for key in required:
        if key not in parent_data:
            raise ValueError(f"Missing field: {key}")

# ---------------------- Auth Helpers ----------------------
def get_user_role(uid):
    user_doc = db.collection("users").document(uid).get()
    if user_doc.exists:
        return user_doc.to_dict().get("role")
    return None

def verify_firebase_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return the decoded token dict."""
    return auth.verify_id_token(id_token)

def firebase_login_rest(email: str, password: str) -> dict | None:
    """Call Firebase REST API to sign in, returns user dict or None."""
    api_key = os.getenv("FIREBASE_API_KEY")
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    res = requests.post(url, json=payload)
    if res.status_code == 200:
        data = res.json()
        uid = data.get("localId")
        role = get_user_role(uid)
        if not role:
            return None
        return {
            "uid": uid,
            "email": data.get("email"),
            "idToken": data.get("idToken"),
            "refreshToken": data.get("refreshToken"),
            "role": role,
        }
    return None

def reset_password(email: str) -> bool:
    api_key = os.getenv("FIREBASE_API_KEY")
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"
    res = requests.post(url, json={"requestType": "PASSWORD_RESET", "email": email})
    return res.status_code == 200

def create_user_profile(uid, email, role="teacher"):
    validate_user_data({"email": email, "role": role})
    db.collection("users").document(uid).set({
        "email": email,
        "role": role,
        "created_at": datetime.now(timezone.utc),
        "disabled": False
    })

# ---------------------- Students ----------------------
def add_student(teacher_uid, student_data):
    student_data["TeacherUID"] = teacher_uid
    validate_student_data(student_data)
    doc_ref = db.collection("students").document()
    doc_ref.set(student_data)
    parent_uid = student_data.get("ParentUID")
    if parent_uid:
        link_parent_to_student(parent_uid, doc_ref.id)
    return doc_ref.id

def update_student(student_id, updates):
    if "ParentUID" in updates:
        student_doc = db.collection("students").document(student_id).get()
        if student_doc.exists:
            old_parent_uid = student_doc.to_dict().get("ParentUID")
            if old_parent_uid != updates.get("ParentUID"):
                unlink_student_from_all_parents(student_id)
    db.collection("students").document(student_id).update(updates)
    parent_uid = updates.get("ParentUID")
    if parent_uid:
        link_parent_to_student(parent_uid, student_id)

def delete_student(student_id):
    student_ref = db.collection("students").document(student_id)
    if student_ref.get().exists:
        unlink_student_from_all_parents(student_id)
    student_ref.delete()

def get_students_by_teacher(teacher_uid):
    students = db.collection("students").where("TeacherUID", "==", teacher_uid).stream()
    return [{**s.to_dict(), "id": s.id} for s in students]

def get_student_by_id(student_id):
    student = db.collection("students").document(student_id).get()
    return {"id": student.id, **student.to_dict()} if student.exists else None

def get_all_students():
    docs = db.collection("students").stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]

# ---------------------- Parents ----------------------
def add_parent(parent_data):
    validate_parent_data(parent_data)
    doc_ref = db.collection("parents").document()
    doc_ref.set(parent_data)
    return doc_ref.id

def update_parent(parent_id, updates):
    db.collection("parents").document(parent_id).update(updates)

def delete_parent(parent_id):
    db.collection("parents").document(parent_id).delete()

def get_parents_by_teacher(teacher_uid):
    results = db.collection("parents").where("TeacherUID", "array_contains", teacher_uid).stream()
    return [{**d.to_dict(), "id": d.id} for d in results]

def get_parent_by_email(email):
    query = db.collection("parents").where("Email", "==", email).limit(1).stream()
    for doc in query:
        return {**doc.to_dict(), "id": doc.id}
    return None

def get_all_parents():
    docs = db.collection("parents").stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]

def link_parent_to_student(parent_id, student_id):
    parent_ref = db.collection("parents").document(parent_id)
    parent_doc = parent_ref.get()
    if parent_doc.exists:
        children = set(parent_doc.to_dict().get("ChildrenUIDs", []))
        if student_id not in children:
            children.add(student_id)
            parent_ref.update({"ChildrenUIDs": list(children)})

def unlink_student_from_all_parents(student_id):
    parents = db.collection("parents").where("ChildrenUIDs", "array_contains", student_id).stream()
    for p in parents:
        children = p.to_dict().get("ChildrenUIDs", [])
        if student_id in children:
            children.remove(student_id)
            db.collection("parents").document(p.id).update({"ChildrenUIDs": children})

def get_students_for_parent(parent_uid_or_email):
    parent_doc = db.collection("parents").document(parent_uid_or_email).get()
    if not parent_doc.exists:
        query = db.collection("parents").where("Email", "==", parent_uid_or_email).limit(1).stream()
        parent_doc = next(query, None)
        if not parent_doc:
            return []
    pdata = parent_doc.to_dict()
    children_ids = pdata.get("ChildrenUIDs", [])
    students = []
    for sid in children_ids:
        s = db.collection("students").document(sid).get()
        if s.exists:
            students.append({"id": s.id, **s.to_dict()})
    return students

# ---------------------- Materials ----------------------
def upload_material_bytes(file_bytes: bytes, filename: str, teacher_uid: str, content_type: str = "application/octet-stream"):
    path = f"{teacher_uid}/materials/{filename}"
    try:
        supabase.storage.from_(str(SUPABASE_BUCKET)).upload(
            file=file_bytes,
            path=path,
            file_options={"content-type": content_type}
        )
        return generate_signed_url(path)
    except Exception as e:
        print(f"[Upload Error] {e}")
        return None

def list_materials(teacher_uid):
    prefix = f"{teacher_uid}/materials/"
    try:
        result = supabase.storage.from_(str(SUPABASE_BUCKET)).list(path=prefix)
        return [
            {"name": f["name"], "url": generate_signed_url(f"{prefix}{f['name']}")}
            for f in result if f.get("name")
        ]
    except Exception as e:
        print(f"[List Materials Error] {e}")
        return []

def generate_signed_url(file_path, expiry=3600):
    try:
        res = supabase.storage.from_(str(SUPABASE_BUCKET)).create_signed_url(file_path, expiry)
        return res.get("signedURL", "")
    except Exception as e:
        print(f"[Signed URL Error] {e}")
        return ""

# ---------------------- Messages ----------------------
def send_message(recipient_email, sender_email, message):
    db.collection("messages").add({
        "recipient": recipient_email,
        "sender": sender_email,
        "message": message,
        "timestamp": datetime.now(timezone.utc)
    })

def get_messages_for_user(email):
    try:
        sent = db.collection("messages").where("sender", "==", email).stream()
        received = db.collection("messages").where("recipient", "==", email).stream()
        messages = [d.to_dict() for d in sent] + [d.to_dict() for d in received]
        # Convert Firestore timestamps to ISO strings
        for m in messages:
            if hasattr(m.get("timestamp"), "isoformat"):
                m["timestamp"] = m["timestamp"].isoformat()
        return sorted(messages, key=lambda m: m.get("timestamp", ""), reverse=True)
    except Exception as e:
        print(f"[Messages Error] {e}")
        return []

# ---------------------- Assignments ----------------------
def create_assignment(teacher_uid, assignment_data):
    assignment_id = str(uuid.uuid4())
    assignment_data["TeacherUID"] = teacher_uid
    assignment_data["createdAt"] = datetime.now(timezone.utc).isoformat()
    db.collection("assignments").document(assignment_id).set(assignment_data)
    return assignment_id

def assign_to_students(assignment_id, student_ids):
    for student_id in student_ids:
        sa_ref = db.collection("student_assignments").document(f"{student_id}_{assignment_id}")
        sa_ref.set({
            "studentID": student_id,
            "assignmentID": assignment_id,
            "submit_status": False,
            "score": None
        })

def get_assignments_by_teacher(teacher_uid):
    docs = db.collection("assignments").where("TeacherUID", "==", teacher_uid).stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]

def get_assignments_for_student(student_id):
    docs = db.collection("student_assignments").where("studentID", "==", student_id).stream()
    return [d.to_dict() for d in docs]

def get_assignment_detail(assignment_id):
    doc = db.collection("assignments").document(assignment_id).get()
    return {**doc.to_dict(), "id": doc.id} if doc.exists else None

def get_all_assignment_submissions(assignment_id):
    docs = db.collection("student_assignments").where("assignmentID", "==", assignment_id).stream()
    return [d.to_dict() for d in docs]

def submit_assignment_response(assignment_id, student_id, file_url=None, text_response=None):
    doc_id = f"{student_id}_{assignment_id}"
    update_data = {"submit_status": True, "submittedAt": datetime.now(timezone.utc).isoformat()}
    if file_url:
        update_data["submittedFileURL"] = file_url
    if text_response:
        update_data["submissionText"] = text_response
    db.collection("student_assignments").document(doc_id).update(update_data)

def set_student_score(assignment_id, student_id, score):
    doc_id = f"{student_id}_{assignment_id}"
    db.collection("student_assignments").document(doc_id).update({"score": score})

def upload_assignment_bytes(file_bytes: bytes, filename: str, content_type: str = "application/octet-stream"):
    path = f"assignment_materials/{uuid.uuid4()}_{filename}"
    try:
        supabase.storage.from_(str(ASSIGNMENTS_BUCKET)).upload(
            file=file_bytes, path=path,
            file_options={"content-type": content_type}
        )
        res = supabase.storage.from_(str(ASSIGNMENTS_BUCKET)).create_signed_url(path, 3600)
        return res.get("signedURL", "")
    except Exception as e:
        print(f"[Assignment Upload Error] {e}")
        return None

def upload_submission_bytes(file_bytes: bytes, filename: str, content_type: str = "application/octet-stream"):
    path = f"assignment_submissions/{uuid.uuid4()}_{filename}"
    try:
        supabase.storage.from_(str(ASSIGNMENTS_BUCKET)).upload(
            file=file_bytes, path=path,
            file_options={"content-type": content_type}
        )
        res = supabase.storage.from_(str(ASSIGNMENTS_BUCKET)).create_signed_url(path, 3600)
        return res.get("signedURL", "")
    except Exception as e:
        print(f"[Submission Upload Error] {e}")
        return None

# ---------------------- Admin ----------------------
def create_firebase_user(email, password, role="teacher"):
    user_record = auth.create_user(email=email, password=password)
    uid = user_record.uid
    create_user_profile(uid, email, role)
    return uid

def list_users():
    docs = db.collection("users").stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]

def update_user_role(user_id, new_role):
    if new_role not in ["admin", "teacher", "parent"]:
        raise ValueError("Invalid role")
    db.collection("users").document(user_id).update({"role": new_role})

def disable_user_account(user_id, disabled=True):
    db.collection("users").document(user_id).update({"disabled": disabled})

def get_all_teachers():
    docs = db.collection("users").where("role", "==", "teacher").stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]

def get_all_assignments():
    docs = db.collection("assignments").stream()
    return [{**d.to_dict(), "id": d.id} for d in docs]

# ---------------------- Push Notifications ----------------------
def save_push_token(uid: str, push_token: str):
    db.collection("users").document(uid).update({"pushToken": push_token})

def get_push_token(uid: str) -> str | None:
    doc = db.collection("users").document(uid).get()
    return doc.to_dict().get("pushToken") if doc.exists else None
