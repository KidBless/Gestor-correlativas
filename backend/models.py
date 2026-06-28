from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, ForeignKey, Table, DateTime
from sqlalchemy.orm import relationship
from database import Base


prerequisite_association = Table(
    "prerequisites",
    Base.metadata,
    Column("subject_id", Integer, ForeignKey("subjects.id"), primary_key=True),
    Column("prerequisite_id", Integer, ForeignKey("subjects.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")  # "admin" or "user"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    subjects = relationship("UserSubject", back_populates="user", cascade="all, delete-orphan")


class Career(Base):
    __tablename__ = "careers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    faculty_name = Column(String, nullable=True)
    subjects = relationship(
        "Subject", back_populates="career", cascade="all, delete-orphan"
    )


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    semester = Column(Integer, nullable=False)
    career_id = Column(Integer, ForeignKey("careers.id"), nullable=False)

    career = relationship("Career", back_populates="subjects")
    user_statuses = relationship("UserSubject", back_populates="subject", cascade="all, delete-orphan")
    prerequisites = relationship(
        "Subject",
        secondary=prerequisite_association,
        primaryjoin=id == prerequisite_association.c.subject_id,
        secondaryjoin=id == prerequisite_association.c.prerequisite_id,
        backref="required_by",
    )


class UserSubject(Base):
    __tablename__ = "user_subjects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    status = Column(String, default="no_cursada")

    user = relationship("User", back_populates="subjects")
    subject = relationship("Subject", back_populates="user_statuses")
