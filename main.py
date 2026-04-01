from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import auth, students, assignments, materials, messages, parents, admin

app = FastAPI(title="English Teaching Platform API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production to your mobile app domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/auth",        tags=["Auth"])
app.include_router(students.router,    prefix="/students",    tags=["Students"])
app.include_router(assignments.router, prefix="/assignments",  tags=["Assignments"])
app.include_router(materials.router,   prefix="/materials",   tags=["Materials"])
app.include_router(messages.router,    prefix="/messages",    tags=["Messages"])
app.include_router(parents.router,     prefix="/parents",     tags=["Parents"])
app.include_router(admin.router,       prefix="/admin",       tags=["Admin"])

@app.get("/")
def root():
    return {"status": "ok", "message": "English Teaching Platform API"}
