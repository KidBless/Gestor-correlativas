import os
import tempfile
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List

from database import engine, get_db, Base
from models import Career, Subject, User, UserSubject, prerequisite_association
from schemas import (
    CareerCreate,
    CareerUpload,
    CareerOut,
    CareerListItem,
    SubjectOut,
    SubjectUpdate,
    SubjectEdit,
    ProgressOut,
    PdfParseOut,
    ParsedSubjectOut,
    AuthRegister,
    AuthLogin,
    AuthOut,
    UserOut,
    AdminUserOut,
    AdminCareerOut,
    ServerStatsOut,
)
from parser import parse_pdf
from auth import hash_password, verify_password, create_token, get_current_user, require_admin

Base.metadata.create_all(bind=engine)

origins_str = os.environ.get("CORS_ORIGINS", "*")

app = FastAPI(title="Gestor de Correlativas")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins_str.split(",") if origins_str != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Auth endpoints ---


@app.post("/api/auth/register")
def register(payload: AuthRegister, db: Session = Depends(get_db)):
    if len(payload.username) < 3:
        raise HTTPException(status_code=400, detail="El usuario debe tener al menos 3 caracteres")
    if len(payload.password) < 4:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 4 caracteres")

    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ese nombre de usuario ya está registrado")

    # First user becomes admin
    is_first = db.query(User).count() == 0
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="admin" if is_first else "user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_token(user.id, user.role)
    return AuthOut(token=token, user_id=user.id, username=user.username, role=user.role)


@app.post("/api/auth/login")
def login(payload: AuthLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    token = create_token(user.id, user.role)
    return AuthOut(token=token, user_id=user.id, username=user.username, role=user.role)


@app.get("/api/auth/me")
def me(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user["user_id"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return UserOut(id=db_user.id, username=db_user.username, role=db_user.role)


# --- PDF parse endpoint ---


@app.post("/api/parse-pdf", response_model=PdfParseOut)
async def parse_pdf_endpoint(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="El archivo debe tener extensión .pdf")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    try:
        content = await file.read()
        tmp.write(content)
        tmp.close()

        subjects, raw_text = parse_pdf(tmp.name)

        career_name = os.path.splitext(os.path.basename(file.filename))[0]
        career_name = career_name.replace("_", " ").replace("-", " ").title()

        from parser import detect_faculty_name
        faculty = detect_faculty_name(raw_text)

        return PdfParseOut(
            career_name=career_name,
            faculty_name=faculty,
            subjects=subjects,
            raw_text=raw_text[:5000],
        )
    finally:
        os.unlink(tmp.name)


# --- Text parse endpoint ---


class TextParsePayload(BaseModel):
    text: str


@app.post("/api/parse-text", response_model=PdfParseOut)
def parse_text_endpoint(payload: TextParsePayload):
    from parser import parse_study_plan, detect_faculty_name

    faculty = detect_faculty_name(payload.text)
    subjects = parse_study_plan(payload.text)
    return PdfParseOut(
        career_name="Plan de Estudios",
        faculty_name=faculty,
        subjects=subjects,
        raw_text=payload.text[:5000],
    )


# --- Career endpoints ---


@app.get("/api/careers", response_model=List[CareerListItem])
def list_careers(user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    careers = db.query(Career).all()
    return [
        CareerListItem(
            id=c.id,
            name=c.name,
            faculty_name=c.faculty_name or "",
            subject_count=len(c.subjects),
        )
        for c in careers
    ]


@app.post("/api/careers", response_model=CareerOut)
def create_career(payload: CareerCreate, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    career = Career(name=payload.name, faculty_name=payload.faculty_name or None)
    db.add(career)
    db.commit()
    db.refresh(career)
    return _career_to_user_out(career, user["user_id"], db)


@app.post("/api/careers/upload", response_model=CareerOut)
def upload_career(
    payload: CareerUpload,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    career = Career(name=payload.name, faculty_name=payload.faculty_name or None)
    db.add(career)
    db.flush()
    _add_subjects_to_career(db, career, payload.subjects)
    db.commit()
    db.refresh(career)
    return _career_to_user_out(career, user["user_id"], db)


@app.post("/api/careers/{career_id}/subjects", response_model=CareerOut)
def add_subjects(
    career_id: int,
    payload: CareerUpload,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    career = db.query(Career).filter(Career.id == career_id).first()
    if not career:
        raise HTTPException(status_code=404, detail="Carrera no encontrada")
    _add_subjects_to_career(db, career, payload.subjects)
    # If faculty_name provided, update it
    if payload.faculty_name and not career.faculty_name:
        career.faculty_name = payload.faculty_name
    db.commit()
    db.refresh(career)
    return _career_to_user_out(career, user["user_id"], db)


@app.get("/api/careers/{career_id}", response_model=CareerOut)
def get_career(
    career_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    career = db.query(Career).filter(Career.id == career_id).first()
    if not career:
        raise HTTPException(status_code=404, detail="Carrera no encontrada")
    return _career_to_user_out(career, user["user_id"], db)


@app.delete("/api/careers/{career_id}")
def delete_career(career_id: int, admin: dict = Depends(require_admin), db: Session = Depends(get_db)):
    career = db.query(Career).filter(Career.id == career_id).first()
    if not career:
        raise HTTPException(status_code=404, detail="Carrera no encontrada")
    name = career.name
    db.delete(career)
    db.commit()
    return {"ok": True, "detail": f'Carrera "{name}" eliminada'}


# --- Subject endpoints ---


@app.put("/api/subjects/{subject_id}", response_model=SubjectOut)
def update_subject_status(
    subject_id: int,
    payload: SubjectUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    valid_statuses = {"no_cursada", "cursando", "regular", "aprobado", "promocionado"}
    if payload.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Válidos: {', '.join(valid_statuses)}",
        )

    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")

    us = (
        db.query(UserSubject)
        .filter(UserSubject.user_id == user["user_id"], UserSubject.subject_id == subject_id)
        .first()
    )
    if not us:
        us = UserSubject(user_id=user["user_id"], subject_id=subject_id, status="no_cursada")
        db.add(us)
    us.status = payload.status
    db.commit()
    db.refresh(us)
    return _subject_to_user_out(subject, us.status, db)


@app.put("/api/subjects/{subject_id}/edit", response_model=SubjectOut)
def edit_subject(
    subject_id: int,
    payload: SubjectEdit,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")

    old_name = subject.name
    subject.name = payload.name
    subject.year = payload.year
    subject.semester = payload.semester

    # Update prerequisites
    subject.prerequisites = []
    if payload.prerequisites:
        all_map = {
            s.name: s
            for s in db.query(Subject).filter(Subject.career_id == subject.career_id).all()
        }
        for prereq_name in payload.prerequisites:
            prereq = all_map.get(prereq_name)
            if prereq and prereq.id != subject.id:
                subject.prerequisites.append(prereq)

    subject.prerequisites_regular_only = list(payload.prerequisites_regular_only or [])

    db.commit()
    db.refresh(subject)

    us = (
        db.query(UserSubject)
        .filter(UserSubject.user_id == user["user_id"], UserSubject.subject_id == subject_id)
        .first()
    )
    status = us.status if us else "no_cursada"
    return _subject_to_user_out(subject, status, db)


@app.delete("/api/subjects/{subject_id}")
def delete_subject(
    subject_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    name = subject.name
    db.delete(subject)
    db.commit()
    return {"ok": True, "detail": f'"{name}" eliminada'}


# --- Progress endpoint ---


@app.get("/api/careers/{career_id}/progress", response_model=ProgressOut)
def get_progress(
    career_id: int,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    career = db.query(Career).filter(Career.id == career_id).first()
    if not career:
        raise HTTPException(status_code=404, detail="Carrera no encontrada")

    subjects = db.query(Subject).filter(Subject.career_id == career_id).all()
    total = len(subjects)

    user_subjects = {
        us.subject_id: us.status
        for us in db.query(UserSubject).filter(UserSubject.user_id == user["user_id"]).all()
    }

    promocionado = 0
    aprobado = 0
    regular = 0
    cursando = 0
    no_cursada = 0

    for s in subjects:
        status = user_subjects.get(s.id, "no_cursada")
        if status == "promocionado":
            promocionado += 1
        elif status == "aprobado":
            aprobado += 1
        elif status == "regular":
            regular += 1
        elif status == "cursando":
            cursando += 1
        else:
            no_cursada += 1

    advanced = promocionado + aprobado
    progress_percentage = round((advanced / total * 100), 1) if total > 0 else 0

    subjects_by_year = {}
    for s in subjects:
        key = str(s.year)
        if key not in subjects_by_year:
            subjects_by_year[key] = {"total": 0, "aprobadas": 0}
        subjects_by_year[key]["total"] += 1
        status = user_subjects.get(s.id, "no_cursada")
        if status in ("aprobado", "promocionado"):
            subjects_by_year[key]["aprobadas"] += 1

    return ProgressOut(
        total_subjects=total,
        promocionado=promocionado,
        aprobado=aprobado,
        regular=regular,
        cursando=cursando,
        no_cursada=no_cursada,
        progress_percentage=progress_percentage,
        subjects_by_year=subjects_by_year,
    )


# --- Admin endpoints ---


@app.get("/api/admin/users", response_model=List[AdminUserOut])
def admin_list_users(admin: dict = Depends(require_admin), db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        AdminUserOut(
            id=u.id,
            username=u.username,
            role=u.role,
            created_at=u.created_at.isoformat() if u.created_at else "",
        )
        for u in users
    ]


@app.get("/api/admin/careers", response_model=List[AdminCareerOut])
def admin_list_careers(admin: dict = Depends(require_admin), db: Session = Depends(get_db)):
    careers = db.query(Career).all()
    return [
        AdminCareerOut(
            id=c.id,
            name=c.name,
            faculty_name=c.faculty_name or "",
            subject_count=len(c.subjects),
            created_at="",
        )
        for c in careers
    ]


@app.get("/api/admin/server-stats", response_model=ServerStatsOut)
def admin_server_stats(admin: dict = Depends(require_admin)):
    import psutil
    import os
    import platform

    cpu = psutil.cpu_percent(interval=0.3)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage(os.path.abspath(os.sep))
    boot_time = psutil.boot_time()

    import time
    uptime = time.time() - boot_time

    return ServerStatsOut(
        cpu_percent=cpu,
        memory_percent=mem.percent,
        memory_used_mb=round(mem.used / 1024 / 1024, 1),
        memory_total_mb=round(mem.total / 1024 / 1024, 1),
        disk_percent=disk.percent,
        disk_used_gb=round(disk.used / 1024 / 1024 / 1024, 1),
        disk_total_gb=round(disk.total / 1024 / 1024 / 1024, 1),
        uptime_seconds=round(uptime, 0),
        python_version=platform.python_version(),
        platform=platform.system() + " " + platform.release(),
    )


# --- Helpers ---


def _get_user_status(subject_id: int, user_id: int, db: Session) -> str:
    us = (
        db.query(UserSubject)
        .filter(UserSubject.user_id == user_id, UserSubject.subject_id == subject_id)
        .first()
    )
    if us:
        return us.status
    us = UserSubject(user_id=user_id, subject_id=subject_id, status="no_cursada")
    db.add(us)
    db.flush()
    return "no_cursada"


def _add_subjects_to_career(db: Session, career: Career, subjects_data: list):
    existing_names = {
        s.name
        for s in db.query(Subject).filter(Subject.career_id == career.id).all()
    }
    name_to_subject = {}
    for s in subjects_data:
        if s.name in existing_names or s.name in name_to_subject:
            continue
        subj = Subject(
            name=s.name,
            year=s.year,
            semester=s.semester,
            career_id=career.id,
            prerequisites_regular_only=list(getattr(s, 'prerequisites_regular_only', [])),
        )
        db.add(subj)
        db.flush()
        name_to_subject[s.name] = subj

    all_subjects = db.query(Subject).filter(Subject.career_id == career.id).all()
    all_map = {s.name: s for s in all_subjects}

    for s in subjects_data:
        subj = all_map.get(s.name) or name_to_subject.get(s.name)
        if not subj:
            continue
        for prereq_name in s.prerequisites:
            prereq = all_map.get(prereq_name)
            if prereq and prereq not in subj.prerequisites:
                subj.prerequisites.append(prereq)


def _subject_to_user_out(subject: Subject, status: str, db: Session) -> SubjectOut:
    prereq_names = [p.name for p in subject.prerequisites]
    regular_only = list(subject.prerequisites_regular_only or [])
    return SubjectOut(
        id=subject.id,
        name=subject.name,
        year=subject.year,
        semester=subject.semester,
        status=status,
        prerequisites=prereq_names,
        prerequisites_regular_only=regular_only,
    )


def _career_to_user_out(career: Career, user_id: int, db: Session) -> CareerOut:
    subjects = []
    for s in career.subjects:
        status = _get_user_status(s.id, user_id, db)
        prereq_names = [p.name for p in s.prerequisites]
        regular_only = list(s.prerequisites_regular_only or [])
        subjects.append(
            SubjectOut(
                id=s.id,
                name=s.name,
                year=s.year,
                semester=s.semester,
                status=status,
                prerequisites=prereq_names,
                prerequisites_regular_only=regular_only,
            )
        )
    return CareerOut(
        id=career.id,
        name=career.name,
        faculty_name=career.faculty_name or "",
        subjects=subjects,
    )
