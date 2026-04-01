# English Teaching Platform — FastAPI Backend

REST API that powers the mobile app. Wraps your existing Firebase/Supabase backend.

## Project structure

```
fastapi_backend/
├── main.py                  # App entry point, CORS, router registration
├── requirements.txt
├── Procfile                 # For Railway / Render
├── .env.example
└── api/
    ├── firebase_utils.py    # All Firebase + Supabase functions
    ├── dependencies.py      # Auth middleware (token verification)
    └── routers/
        ├── auth.py          # POST /auth/login, /auth/reset-password
        ├── students.py      # GET/POST/PUT/DELETE /students
        ├── assignments.py   # Full assignment CRUD + submit + grade
        ├── materials.py     # GET /materials, POST /materials/upload
        ├── messages.py      # GET/POST /messages
        ├── parents.py       # GET/POST/PUT/DELETE /parents
        └── admin.py         # Admin-only: stats, user management
```

## Local development

```bash
cd fastapi_backend
pip install -r requirements.txt
cp .env.example .env        # Fill in your values
uvicorn main:app --reload
```

API docs available at: http://localhost:8000/docs

## Deploy to Railway (recommended — free tier)

1. Push this folder to a GitHub repo
2. Go to railway.app → New Project → Deploy from GitHub
3. Set environment variables (copy from .env.example):
   - `FIREBASE_API_KEY`
   - `FIREBASE_CREDENTIALS_JSON` — open your Firebase service account JSON, copy the entire content as a single-line string
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
   - `SUPABASE_BUCKET_NAME`
   - `SUPABASE_ASSIGNMENTS_BUCKET`
   - `SUPABASE_MATERIALS_BUCKET`
4. Railway auto-detects the Procfile and deploys

Your API base URL will be: `https://your-app.up.railway.app`

## Deploy to Render (alternative)

1. New Web Service → connect GitHub repo
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Add same environment variables as above

## Auth flow for mobile app

Every protected endpoint requires:
```
Authorization: Bearer <Firebase_idToken>
```

The mobile app:
1. Calls `POST /auth/login` → gets `idToken` + `role`
2. Stores `idToken` in device secure storage
3. Sends it as Bearer token on every subsequent request
4. Token expires after 1 hour — use `refreshToken` to get a new one via Firebase REST API

## Endpoints summary

| Method | Path | Role |
|--------|------|------|
| POST | /auth/login | Public |
| POST | /auth/reset-password | Public |
| GET | /auth/me | Any |
| POST | /auth/push-token | Any |
| GET | /students/ | Teacher/Parent/Admin |
| POST | /students/ | Teacher/Admin |
| PUT | /students/{id} | Teacher/Admin |
| DELETE | /students/{id} | Teacher/Admin |
| GET | /assignments/ | Teacher/Parent/Admin |
| POST | /assignments/ | Teacher/Admin |
| POST | /assignments/upload-material | Teacher/Admin |
| GET | /assignments/{id}/submissions | Teacher/Admin |
| POST | /assignments/{id}/submit | Parent/Teacher |
| PUT | /assignments/{id}/score | Teacher/Admin |
| GET | /materials/ | Teacher/Parent |
| POST | /materials/upload | Teacher/Admin |
| GET | /messages/ | Any |
| POST | /messages/ | Any |
| GET | /parents/ | Teacher/Admin |
| POST | /parents/ | Teacher/Admin |
| GET | /admin/stats | Admin |
| GET | /admin/users | Admin |
| POST | /admin/users | Admin |
