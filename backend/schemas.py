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


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    status: str


class SubjectOut(BaseModel):
    id: int
    name: str
    year: int
    semester: int
    status: str
    prerequisites: List[str] = []

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


class ParsedSubjectOut(BaseModel):
    name: str
    year: int
    semester: int
    prerequisites: List[str] = []


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
