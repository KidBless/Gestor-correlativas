from pydantic import BaseModel
from typing import List, Optional


# --- Auth ---

class AuthRegister(BaseModel):
    username: str
    password: str


class AuthLogin(BaseModel):
    username: str
    password: str


class AuthOut(BaseModel):
    token: str
    user_id: int
    username: str
    role: str


class UserOut(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True


# --- Subjects ---

class SubjectBase(BaseModel):
    name: str
    year: int
    semester: int
    prerequisites: List[str] = []
    prerequisites_regular_only: List[str] = []


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    status: str


class SubjectEdit(BaseModel):
    name: str
    year: int
    semester: int
    prerequisites: List[str] = []
    prerequisites_regular_only: List[str] = []


class SubjectOut(BaseModel):
    id: int
    name: str
    year: int
    semester: int
    status: str
    prerequisites: List[str] = []
    prerequisites_regular_only: List[str] = []

    class Config:
        from_attributes = True


class CareerCreate(BaseModel):
    name: str
    faculty_name: str = ""


class CareerUpload(BaseModel):
    name: str
    faculty_name: str = ""
    subjects: List[SubjectCreate]


class CareerOut(BaseModel):
    id: int
    name: str
    faculty_name: str = ""
    subjects: List[SubjectOut] = []

    class Config:
        from_attributes = True


class CareerListItem(BaseModel):
    id: int
    name: str
    faculty_name: str = ""
    subject_count: int = 0


class ParsedSubjectOut(BaseModel):
    name: str
    year: int
    semester: int
    prerequisites: List[str] = []
    prerequisites_regular_only: List[str] = []


class PdfParseOut(BaseModel):
    career_name: str
    faculty_name: str = ""
    subjects: List[ParsedSubjectOut]
    raw_text: str = ""


class ProgressOut(BaseModel):
    total_subjects: int
    promocionado: int
    aprobado: int
    regular: int
    cursando: int
    no_cursada: int
    progress_percentage: float
    subjects_by_year: dict


# --- Admin ---

class AdminUserOut(BaseModel):
    id: int
    username: str
    role: str
    created_at: str

    class Config:
        from_attributes = True


class AdminCareerOut(BaseModel):
    id: int
    name: str
    faculty_name: str = ""
    subject_count: int
    created_at: str = ""


class ServerStatsOut(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    uptime_seconds: float
    python_version: str
    platform: str


# --- Profile ---

class PasswordChange(BaseModel):
    old_password: str
    new_password: str


# --- Status History ---

class StatusChangeOut(BaseModel):
    id: int
    subject_id: int
    subject_name: str = ""
    old_status: Optional[str] = None
    new_status: str
    changed_at: str

    class Config:
        from_attributes = True


# --- Admin user management ---

class AdminUserUpdate(BaseModel):
    role: Optional[str] = None
