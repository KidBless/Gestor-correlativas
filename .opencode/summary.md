<template>
## Goal
- Build a multi‑user university course prerequisite manager with JWT auth, plan parsing (PDF/text/UNAM table), per‑user status tracking, progress visualization, inline editing, admin dashboard, and support for prerequisites that only require "regular" status.

## Constraints & Preferences
- Backend and frontend in separate folders (`backend/`, `frontend/`)
- PDF/text upload must detect subjects, year/semester, prerequisites, and faculty/university name
- Each user has their own subject status (promocionado, aprobado, regular, cursando, no_cursada)
- First registered user becomes admin; everyone else is regular user
- Any authenticated user can create careers and upload plans; admin only for delete career
- Some subjects only require "regular" status in prerequisites, not "aprobado"/"promocionado"
- Parser must handle multiple formats: "Año 1 – Semestre 2", UNAM/FCEQyN tabular with Roman codes
- Frontend must show proper error/loading states, login/register, user role badge, career search, status filter, and dark‑theme UI
- Session ends when tab is closed (sessionStorage, not localStorage)
- `pip install --break-system-packages -r requirements.txt`

## Progress
### Done
- Project structure: `backend/` (FastAPI + SQLAlchemy + SQLite) + `frontend/` (HTML/CSS/JS)
- Models: `User`, `Career`, `Subject`, `UserSubject`, `prerequisite_association`, `StatusChangeLog`, `JSONList` type decorator
- Auth system: JWT (PyJWT, HS256), pbkdf2, dependencies `get_current_user` / `require_admin`
- Auth endpoints: register (first user = admin), login, me, password change, token refresh
- Career endpoints: CRUD, upload with subjects, auto‑create UserSubject rows, circular dependency validation
- Subject endpoints: list by career, status update with history logging, edit (name/year/semester/prerequisites/regular_only), delete
- Progress endpoint: overall + by‑year breakdown
- Parser (`parser.py`): faculty table parser (year words, Roman codes, regimen, continuation lines, code‑to‑name resolution), legacy fallback, `detect_faculty_name()`, `_is_table_header()`, header filter in continuation path, `_is_continuation_line` threshold `<= 12`, `looks_like_faculty_table` regex fix, `_FACULTY_STOP_KEYWORDS`
- Admin endpoints: `GET /api/admin/users`, `GET /api/admin/careers`, `GET /api/admin/server-stats` (CPU/RAM/disk/uptime), `DELETE /api/admin/users/{id}`, `PUT /api/admin/users/{id}` (role change), `GET /api/admin/backup` (SQLite backup download)
- `prerequisites_regular_only` column on Subject (JSON list) — prerequisites that only need "regular" status
- Backend config via env vars: `DATABASE_URL`, `CORS_ORIGINS`, `JWT_SECRET`
- Dependencies: `psutil` added to `requirements.txt`
- Frontend redesign: amber dark theme, auth tabs, role badges, career search with subject count, status filter, inline edit, delete career/subject, step flow (Carrera → Cargar plan → Mis materias → Avance), PDF/text/manual tabs, editable preview, subject cards with status borders and availability locks, progress bar overlay
- Admin dashboard toggleable panel (outside step flow): users table (with delete/role change buttons), careers table, server stats with cards + bars + refresh button
- Edit mode: per‑prerequisite checkbox for "solo regular" / "aprobado"
- Preview table: "Solo regular" column for marking regular‑only prerequisites
- Profile/password section: change password from within the app
- Subject search filter: filter subjects by name
- Subject history: view status change log per subject
- Reset progress: reset all subjects to "no_cursada"
- Export progress: download progress as JSON
- Export PDF: server-side PDF generation via fpdf2 (landscape A4, color-coded, by year/semester, with prerequisites and progress stats)
- Plan semanal: detailed progress view listing all subjects by year/semester with status badges and prerequisites
- Theme toggle: light/dark mode (persisted in localStorage)
- Auto token refresh: refresh JWT every 30 minutes
- beforeunload confirmation: warn before leaving
- Responsive admin tables: wrap action buttons on small screens
- `changelog.md` updated with all changes
- `README.md` created; `ejemplo_plan.json` sample plan
- Git repo at `git@github.com:KidBless/Gestor-correlativas.git`, all commits pushed
- DB cleaned multiple times to match schema changes
- All API endpoints verified working via curl tests

### In Progress
- (none)

### Blocked
- (none)

## Key Decisions
- JWT over session‑based auth for simplicity
- Password hashing with `hashlib.pbkdf2_hmac` (built‑in, no extra deps) due to missing wheels on Python 3.14
- First‑user‑is‑admin so deployment doesn't need separate admin creation step
- `prerequisites_regular_only` stored as JSON list on Subject (simple, no extra table)
- Circular dependency validation via DFS (added to both edit and bulk‑add paths)
- Status changes logged to `status_change_log` table for history display
- Admin dashboard as toggleable panel (not step 5) to keep main flow clean
- `sessionStorage` over `localStorage` so token expires on tab close
- Inline edit for subjects (no modal) to keep interaction fast

## Next Steps
- Test end‑to‑end with a real PDF from the user's faculty
- Any remaining polish or bug fixes

## Critical Context
- Python 3.14.5 (very new, some wheels unavailable)
- Server: `uvicorn main:app --host 0.0.0.0 --port 8000` from `backend/`
- Database file: `correlativas.db` (SQLite, created in `backend/` directory at startup)
- Frontend defaults to `http://localhost:8000/api`; override via `window.__API_URL`
- `normalize_text()` must NOT be called before faculty table parser (collapses column spacing)
- Git remote: `origin git@github.com:KidBless/Gestor-correlativas.git` (SSH)
- DB must be deleted/recreated when schema changes (SQLAlchemy `create_all` does not alter existing tables)
- `CareerUpload` schema requires `name` + `faculty_name` + `subjects` (not just `subjects`)

## Relevant Files
- `backend/main.py`: FastAPI app with all REST endpoints (auth, careers, subjects, admin, progress, history); circular dependency check in edit/add; status change logging
- `backend/models.py`: `User`, `Career`, `Subject` (with `prerequisites_regular_only` JSONList), `UserSubject`, `StatusChangeLog`, `JSONList` type decorator
- `backend/schemas.py`: Auth, Subject/SubjectEdit/SubjectOut (with `prerequisites_regular_only`), Career, Progress, ParsedSubject, Admin, PasswordChange, StatusChangeOut, AdminUserUpdate schemas
- `backend/auth.py`: JWT create/decode, pbkdf2 hashing, `get_current_user` / `require_admin`
- `backend/parser.py`: Faculty table parser, legacy fallback, PDF text extraction, faculty name detection
- `backend/database.py`: SQLite (or configurable via `DATABASE_URL` env var), session, declarative Base
- `backend/requirements.txt`: fastapi, uvicorn, sqlalchemy, pydantic, pdfminer.six, python-multipart, pyjwt, psutil
- `frontend/index.html`: Auth screen + main app (step flow + admin toggleable panel + profile section + weekly schedule)
- `frontend/js/app.js`: API calls with bearer token, auth flow, career search, subject grid (inline edit, status filter, availability, history, search), progress (reset, export), admin dashboard, password change, theme toggle, token refresh, beforeunload confirm, weekly schedule
- `frontend/css/style.css`: Dark/light theme (amber primary), responsive layout, admin dashboard, server stats cards, prereq tags, theme variables, schedule grid, search wrapper
- `changelog.md`: Full project changelog with all dated entries
- `ejemplo_plan.json`: Sample study plan JSON for testing
</template>
