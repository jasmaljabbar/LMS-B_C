# backend/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Float, DateTime, UniqueConstraint, Text, Time, Table, CheckConstraint, Enum as DBEnum, JSON as DB_JSON # Enum added if using DB enum, JSON added
from sqlalchemy.orm import relationship, backref # Import backref if needed
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func


from .database import Base
# Need the enum for the model if using DB Enum, or just rely on string + validation
# Import Enum from schemas - this might cause circular dependency if schemas imports models first
# It's generally safer to define the enum string values directly or use SQLAlchemy's Enum type if needed at DB level
# from backend.schemas import QuestionTypeEnum

from sqlalchemy import LargeBinary, String
from sqlalchemy.ext.declarative import declarative_base



# --- Association Table for Parent-Student (Many-to-Many) ---
parent_student_association = Table(
    'parent_student_association', Base.metadata,
    Column('parent_id', Integer, ForeignKey('parents.id', ondelete='CASCADE'), primary_key=True),
    Column('student_id', Integer, ForeignKey('students.id', ondelete='CASCADE'), primary_key=True)
)

# --- AuditLog Table ---
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete='SET NULL'), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    target_entity = Column(String(50), nullable=True)
    target_entity_id = Column(Integer, nullable=True, index=True)
    details = Column(Text, nullable=True)

    user = relationship("User", back_populates="audit_logs")


# --- LLMTokenUsage Table ---
class LLMTokenUsage(Base):
    __tablename__ = "llm_token_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    action = Column(String(100), nullable=False, index=True) # E.g., "chat", "generate_teacher_notes"
    model_name = Column(String(100), nullable=True)
    input_tokens = Column(Integer, nullable=False)
    output_tokens = Column(Integer, nullable=False)
    total_tokens = Column(Integer, nullable=False)

    user = relationship("User")


# --- Term Table ---
class Term(Base):
    __tablename__ = "terms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    grade_id = Column(Integer, ForeignKey("grades.id", ondelete='CASCADE'), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    grade = relationship("Grade", back_populates="terms")
    # lessons = relationship("Lesson", back_populates="term")
    assessment_scores = relationship("StudentAssessmentScore", back_populates="term")

    __table_args__ = (UniqueConstraint('name', 'year', 'grade_id', name='uq_term_name_year_grade'),)

class FileStorage(Base):
    __tablename__ = "file_storage"
    
    id = Column(Integer, primary_key=True)
    file_name = Column(String(255))
    file_path = Column(String(512))  # Path to file on disk
    content_type = Column(String(100))
    file_size = Column(Integer)
    https_url = Column(String(512))
    gs_url = Column(String(512))

class UserFile(Base):
    __tablename__ = "user_files"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String(255))
    content_type = Column(String(100))
    data = Column(LargeBinary)  # For storing the file data
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="files")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255))
    user_type = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    photo = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True, onupdate=func.now())

    teacher = relationship("Teacher", back_populates="user", uselist=False, cascade="all, delete-orphan")
    student = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    parent = relationship("Parent", back_populates="user", uselist=False, cascade="all, delete-orphan")
    created_assessments = relationship("Assessment", back_populates="creator")
    audit_logs = relationship("AuditLog", back_populates="user", order_by="desc(AuditLog.timestamp)")
    # Relationship from User to AssignmentFormat (optional)
    created_assignment_formats = relationship("AssignmentFormat", back_populates="creator") # Corrected back_populates
    # Relationship from User to AssignmentDistribution (optional)
    # created_assignment_distributions = relationship("AssignmentDistribution", back_populates="assigned_by_user")
    homeworks = relationship("Homework", back_populates="parent", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user")
    files = relationship("UserFile", back_populates="user")




teacher_grades = Table(
    "teacher_grades",
    Base.metadata,
    Column("teacher_id", Integer, ForeignKey("teachers.id", ondelete="CASCADE")),
    Column("grade_id", Integer, ForeignKey("grades.id", ondelete="CASCADE")),
)



class Teacher(Base):
    __tablename__ = "teachers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    user_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), unique=True)

    user = relationship("User", back_populates="teacher")
    timetable_slots = relationship("Timetable", back_populates="teacher")
    grades = relationship("Grade", secondary=teacher_grades, back_populates="teachers")



class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    user_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), unique=True)

    # Add subjects relationship
    subjects = relationship("Subject", back_populates="student", cascade="all, delete-orphan")

    user = relationship("User", back_populates="student")
    assessment_scores = relationship("StudentAssessmentScore", back_populates="student", cascade="all, delete-orphan")
    parents = relationship(
        "Parent",
        secondary=parent_student_association,
        back_populates="children"
    )
    # --- ADDED RELATIONSHIP ---
    specific_assignments = relationship(
        "AssignmentDistribution",
        secondary='assignment_distribution_students', # Use association table name
        back_populates="specific_students"
    )
    homeworks = relationship("Homework", back_populates="student", cascade="all, delete-orphan")
    homework_scores = relationship("StudentHomeworkScore", back_populates="student", cascade="all, delete-orphan")

    # --- END ADDED RELATIONSHIP ---


class Parent(Base):
    __tablename__ = "parents"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    user_id = Column(Integer, ForeignKey("users.id", ondelete='CASCADE'), unique=True)

    user = relationship("User", back_populates="parent")
    children = relationship(
        "Student",
        secondary=parent_student_association,
        back_populates="parents"
    )


class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(255))
    url_type = Column(String(5), nullable=False) # 'https', 'gs'

    pdfs = relationship("PDFUrl", back_populates="url", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="url")
    images = relationship("Image", back_populates="url")
    # Association with AssignmentSample - relationship defined there
    # assignment_samples = relationship("AssignmentSample", secondary="assignment_sample_url_association", back_populates="urls")

    __table_args__ = (
        CheckConstraint(url_type.in_(['https', 'gs']), name='chk_url_type_values'),
    )


class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))

    sections = relationship("Section", back_populates="grade", cascade="all, delete-orphan")
    terms = relationship("Term", back_populates="grade", cascade="all, delete-orphan")
    teachers = relationship("Teacher", secondary=teacher_grades, back_populates="grades")



class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    grade_id = Column(Integer, ForeignKey("grades.id", ondelete='CASCADE'))

    grade = relationship("Grade", back_populates="sections")
    student_years = relationship("StudentYear", back_populates="section", cascade="all, delete-orphan")
    timetable_slots = relationship("Timetable", back_populates="section")
    # Optional: relationship to distributions targeting this section
    # assignment_distributions = relationship("AssignmentDistribution", back_populates="section")


class StudentYear(Base):
    __tablename__ = "student_years"

    studentId = Column(Integer, ForeignKey("students.id", ondelete='CASCADE'), primary_key=True)
    year = Column(Integer, primary_key=True)
    sectionId = Column(Integer, ForeignKey("sections.id", ondelete='CASCADE'))

    student = relationship("Student")
    section = relationship("Section", back_populates="student_years")


class Subject(Base):
    __tablename__ = "subjects"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete='CASCADE'), nullable=False)
    
    student = relationship("Student", back_populates="subjects")
    lessons = relationship("Lesson", back_populates="subject", cascade="all, delete-orphan")
    assessments = relationship("Assessment", back_populates="subject", cascade="all, delete-orphan")
    # Remove this line:
    # timetable_slots = relationship("Timetable", back_populates="subject")
    assignment_samples = relationship("AssignmentSample", back_populates="subject", cascade="all, delete-orphan")
    assignment_formats = relationship("AssignmentFormat", back_populates="subject", cascade="all, delete-orphan")

# --- NEW: Association Table for Assessment-Lesson (Many-to-Many) ---
assessment_lesson_association = Table(
    'assessment_lesson_association', Base.metadata,
    Column('assessment_id', Integer, ForeignKey('assessments.id', ondelete='CASCADE'), primary_key=True),
    Column('lesson_id', Integer, ForeignKey('lessons.id', ondelete='CASCADE'), primary_key=True)
)
# --- END NEW ASSOCIATION TABLE ---

class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete='CASCADE'), nullable=False)
    # term_id = Column(Integer, ForeignKey("terms.id", ondelete='CASCADE'), nullable=False)

    subject = relationship("Subject", back_populates="lessons")
    # term = relationship("Term", back_populates="lessons")
    pdfs = relationship("PDF", back_populates="lesson", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="lesson", cascade="all, delete-orphan")
    # --- MODIFIED: Use association table for assessments ---
    assessments = relationship(
        "Assessment",
        secondary=assessment_lesson_association,
        back_populates="lessons",
        lazy="selectin" # Example loading strategy
    )
    # --- END MODIFICATION ---


# --- PDF Table ---
class PDF(Base):
    __tablename__ = "pdfs"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete='CASCADE'))
    size = Column(Integer, nullable=True)
    lesson = relationship("Lesson", back_populates="pdfs")
    images = relationship("Image", back_populates="pdf", cascade="all, delete-orphan")
    urls = relationship("PDFUrl", back_populates="pdf", cascade="all, delete-orphan")

# --- PDFUrl Table ---
class PDFUrl(Base):
    __tablename__ = "pdf_urls"
    pdf_id = Column(Integer, ForeignKey("pdfs.id", ondelete='CASCADE'), primary_key=True)
    url_id = Column(Integer, ForeignKey("urls.id", ondelete='CASCADE'), primary_key=True)
    pdf = relationship("PDF", back_populates="urls")
    url = relationship("URL", back_populates="pdfs")

# --- Video Table ---
class Video(Base):
    __tablename__ = "videos"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete='CASCADE'))
    url_id = Column(Integer, ForeignKey("urls.id", ondelete='SET NULL'), nullable=True)
    size = Column(Integer, nullable=True)
    lesson = relationship("Lesson", back_populates="videos")
    url = relationship("URL", foreign_keys=[url_id], back_populates="videos")

# --- Image Table ---
class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    pdf_id = Column(Integer, ForeignKey("pdfs.id", ondelete='CASCADE'))
    image_number = Column(Integer, nullable=True)
    page_number = Column(Integer, nullable=True)
    chapter_number = Column(Integer, nullable=True)
    url_id = Column(Integer, ForeignKey("urls.id", ondelete='SET NULL'), nullable=True)
    pdf = relationship("PDF", back_populates="images")
    url = relationship("URL", back_populates="images")


class Assessment(Base):
    __tablename__ = "assessments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    # --- REMOVED lesson_id column ---
    # lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete='SET NULL'), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete='SET NULL'), nullable=True, index=True)
    creation_date = Column(DateTime(timezone=True), server_default=func.now())
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete='SET NULL'), nullable=True, index=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    content = Column(DB_JSON, nullable=True)
    assignment_format_id = Column(Integer, ForeignKey("assignment_formats.id", ondelete='SET NULL'), nullable=True, index=True)

    # --- REMOVED direct lesson relationship ---
    # lesson = relationship("Lesson", back_populates="assessments")
    subject = relationship("Subject", back_populates="assessments")
    creator = relationship("User", back_populates="created_assessments")
    scores = relationship("StudentAssessmentScore", back_populates="assessment", cascade="all, delete-orphan")
    assignment_format = relationship("AssignmentFormat") # No back_populates needed unless Format needs to list Assessments
    # --- ADDED lessons relationship (many-to-many) ---
    lessons = relationship(
        "Lesson",
        secondary=assessment_lesson_association,
        back_populates="assessments",
        lazy="selectin" # Example loading strategy
    )
    # --- END ADDED ---
    # Optional: relationship to distributions using this assessment
    # distributions = relationship("AssignmentDistribution", back_populates="assessment")


# --- StudentAssessmentScore Table ---
class StudentAssessmentScore(Base):
    __tablename__ = "student_assessment_scores"
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete='CASCADE'), nullable=False)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete='CASCADE'), nullable=False)
    term_id = Column(Integer, ForeignKey("terms.id", ondelete='RESTRICT'), nullable=False)
    score_achieved = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    attempt_timestamp = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    comments = Column(String(500), nullable=True)
    student = relationship("Student", back_populates="assessment_scores")
    assessment = relationship("Assessment", back_populates="scores")
    term = relationship("Term", back_populates="assessment_scores")


# In your models.py (Homework model)
class Homework(Base):
    __tablename__ = "homeworks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    image_path = Column(String(255), nullable=False)
    completed = Column(Boolean, default=False)  # New field to track completion status
    completed_at = Column(DateTime, nullable=True)  # When it was marked as completed

    parent_id = Column(Integer, ForeignKey("users.id"))
    student_id = Column(Integer, ForeignKey("students.id"))
    grade_id = Column(Integer, ForeignKey("grades.id"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"))
    lesson_id = Column(Integer, ForeignKey("lessons.id"))

    created_at = Column(DateTime, default=datetime.utcnow)

    parent = relationship("User", back_populates="homeworks")
    student = relationship("Student", back_populates="homeworks")
    subject = relationship("Subject")
    lesson = relationship("Lesson")
    scores = relationship("StudentHomeworkScore", back_populates="homework", cascade="all, delete-orphan")


class StudentHomeworkScore(Base):
    __tablename__ = "student_homework_scores"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete='CASCADE'), nullable=False)
    homework_id = Column(Integer, ForeignKey("homeworks.id", ondelete='CASCADE'), nullable=False)
    score_achieved = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    graded_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Teacher who graded it
    graded_at = Column(DateTime(timezone=True), server_default=func.now())
    comments = Column(String(500), nullable=True)

    # Relationships
    student = relationship("Student", back_populates="homework_scores")
    homework = relationship("Homework", back_populates="scores")
    grader = relationship("User")



class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String(255))
    message = Column(Text)
    is_read = Column(Boolean, default=False)
    related_entity_type = Column(String(50))  # "homework", etc.
    related_entity_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notifications")

# --- Timetable Table ---
class Timetable(Base):
    __tablename__ = "timetables"
    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(Integer, nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete='CASCADE'), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete='CASCADE'), nullable=False, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id", ondelete='SET NULL'), nullable=True)
    
    section = relationship("Section", back_populates="timetable_slots")
    subject = relationship("Subject")
    teacher = relationship("Teacher", back_populates="timetable_slots")

# --- AssignmentSample/URL Association Table ---
assignment_sample_url_association = Table(
    'assignment_sample_url_association', Base.metadata,
    Column('assignment_sample_id', Integer, ForeignKey('assignment_samples.id', ondelete='CASCADE'), primary_key=True),
    Column('url_id', Integer, ForeignKey('urls.id', ondelete='CASCADE'), primary_key=True)
)

# --- AssignmentSample Table ---
class AssignmentSample(Base):
    __tablename__ = "assignment_samples"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete='CASCADE'), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete='SET NULL'), nullable=True, index=True)
    file_size = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    subject = relationship("Subject", back_populates="assignment_samples")
    creator = relationship("User") # Assuming User doesn't need a back-populates for created samples
    urls = relationship("URL", secondary=assignment_sample_url_association, cascade="all, delete", lazy="selectin") # No back_populates needed on URL

# --- AssignmentFormat Table ---
class AssignmentFormat(Base):
    __tablename__ = "assignment_formats"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    # --- ADDED subject_id column ---
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete='CASCADE'), nullable=False, index=True)
    # --- END ADDED ---
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete='SET NULL'), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    questions = relationship("AssignmentFormatQuestion", back_populates="format", cascade="all, delete-orphan", lazy="selectin")
    creator = relationship("User", back_populates="created_assignment_formats") # Match User back_populates
    # --- ADDED subject relationship ---
    subject = relationship("Subject", back_populates="assignment_formats")
    # --- END ADDED ---

# --- AssignmentFormatQuestion Table ---
class AssignmentFormatQuestion(Base):
    __tablename__ = "assignment_format_questions"
    id = Column(Integer, primary_key=True, index=True)
    assignment_format_id = Column(Integer, ForeignKey("assignment_formats.id", ondelete='CASCADE'), nullable=False, index=True)
    question_type = Column(String(50), nullable=False)
    count = Column(Integer, nullable=False)
    format = relationship("AssignmentFormat", back_populates="questions")
    __table_args__ = (UniqueConstraint('assignment_format_id', 'question_type', name='uq_assignment_format_question_type'),
                      CheckConstraint('count >= 0', name='chk_assignment_format_question_count_non_negative'))


# --- NEW: Assignment Distribution Table ---
class AssignmentDistribution(Base):
    __tablename__ = "assignment_distributions"

    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id", ondelete='CASCADE'), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("sections.id", ondelete='CASCADE'), nullable=False, index=True)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id", ondelete='SET NULL'), nullable=True, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    # assign_to_all: If True, assigned to all students in the section at the time of assignment.
    # If False, specific students are listed in the association table.
    assign_to_all_students = Column(Boolean, nullable=False, default=True)

    # --- Relationships ---
    assessment = relationship("Assessment") # No back_populates needed unless Assessment needs to list distributions
    section = relationship("Section") # No back_populates needed unless Section needs to list distributions
    assigned_by_user = relationship("User") # No back_populates needed unless User needs to list distributions created

    # Relationship to specific students (only relevant if assign_to_all_students is False)
    specific_students = relationship(
        "Student",
        secondary='assignment_distribution_students', # Use the association table name
        back_populates="specific_assignments", # Add back-population to Student model
        lazy="selectin" # Eager load students when accessing this relationship
    )

    # Optional: Add unique constraint if an assessment can only be assigned once per section
    # __table_args__ = (UniqueConstraint('assessment_id', 'section_id', name='uq_assessment_distribution_section'),)


# --- NEW: Association Table for Distribution-Student (Many-to-Many) ---
# This table links a distribution to specific students *only* when assign_to_all_students is False
assignment_distribution_students_association = Table(
    'assignment_distribution_students', Base.metadata,
    Column('assignment_distribution_id', Integer, ForeignKey('assignment_distributions.id', ondelete='CASCADE'), primary_key=True),
    Column('student_id', Integer, ForeignKey('students.id', ondelete='CASCADE'), primary_key=True)
)
