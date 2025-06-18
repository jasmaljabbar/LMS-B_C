# backend/schemas.py

from pydantic import BaseModel, Field, validator, ConfigDict, computed_field
from typing import Union, Optional, List, Dict, Any # Import Dict and Any
from datetime import datetime, date, timedelta, time # Ensure time is imported
from enum import Enum

# --- Base Config for ORM ---
orm_config = ConfigDict(from_attributes=True)

# --- GCP Credentials Schema ---
# class GcpCredentialsResponse(BaseModel):
#     access_token: str
#     project_id: str
#     location: str

class StorageConfigResponse(BaseModel):
    """Response model for local storage configuration"""
    storage_type: str = "mysql"  # Default to mysql since that's your storage
    base_url: str  # Base URL for file access (e.g., "http://localhost:8000/files")
    max_file_size: int  # In bytes
    allowed_types: list[str]  # List of allowed MIME types (e.g., ["image/jpeg", "application/pdf"])

# --- User Schemas ---
class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    photo: Union[str, None] = None

class UserUpdate(BaseModel):
    username: str
    email: str
    password: str
    photo: Union[str, None] = None

class UserLogin(BaseModel):
    username: str
    password: str

class TokenData(BaseModel):
    username: Union[str, None] = None

class UserInfo(BaseModel):
    user_id: int
    user_type: str
    entity_id: Optional[int] = None
    access_token: str
    token_type: str
    photo: Union[str, None] = None

class UserDetails(BaseModel):
    model_config = orm_config
    id: int
    username: str
    email: str
    photo: Optional[str] = None


# --- Profile Schemas ---
class TeacherCreate(BaseModel):
    name: str

class StudentCreate(BaseModel):
    name: str

class ParentCreate(BaseModel):
    name: str

class TeacherInfo(BaseModel):
    model_config = orm_config
    id: int
    name: str
    user_id: int
    photo: Union[str, None] = None

class ParentInfo(BaseModel):
    model_config = orm_config
    id: int
    name: str
    user_id: int
    photo: Union[str, None] = None

class StudentInfo(BaseModel):
    model_config = orm_config
    id: int
    name: str
    user_id: int
    photo: Union[str, None] = None

class StudentDetails(BaseModel):
    model_config = orm_config
    id: int
    name: str
    user: UserDetails
    section: 'SectionInfo'
    year: int

class TeacherDetails(BaseModel):
    model_config = orm_config
    id: int
    name: str
    user: UserDetails

class GradeOut(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True



class ParentDetails(BaseModel):
    model_config = orm_config
    id: int
    name: str
    user: UserDetails


# --- Academic Structure Schemas ---

class UrlTypeEnum(str, Enum):
    HTTPS = "https"
    GS = "gs"

class URLCreate(BaseModel):
    url: str
    url_type: UrlTypeEnum

class URLInfo(BaseModel):
    model_config = orm_config
    id: int
    url: str
    url_type: UrlTypeEnum

class GradeCreate(BaseModel):
    name: str

class GradeInfo(BaseModel):
    model_config = orm_config
    id: int
    name: str

class SectionCreate(BaseModel):
    name: str
    grade_id: int

class SectionInfo(BaseModel):
    model_config = orm_config
    id: int
    name: str
    grade_id: int

class StudentYearCreate(BaseModel):
    model_config = orm_config
    studentId: int
    year: int
    sectionId: int

class StudentYearInfo(StudentYearCreate):
     model_config = orm_config

class SubjectCreate(BaseModel):
    name: str
    grade_id: int

class SubjectInfo(BaseModel):
    model_config = orm_config
    id: int
    name: str
    grade_id: int

class TermBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    year: int = Field(..., ge=2000, le=2100)
    grade_id: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @validator('end_date', pre=True, always=True)
    def end_date_after_start_date_v1(cls, v, values):
        start_date = values.get('start_date')
        if isinstance(start_date, date) and isinstance(v, date) and v < start_date:
            raise ValueError('End date must be on or after start date')
        return v

class TermCreate(TermBase):
    pass

class TermUpdate(TermBase):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    year: Optional[int] = Field(None, ge=2000, le=2100)
    grade_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class TermInfo(TermBase):
    model_config = orm_config
    id: int

class SubjectGradeSectionDetails(BaseModel):
    """Schema to return grade and associated section details for a subject."""
    model_config = orm_config # Add this for Pydantic v2 ORM mode
    grade: GradeInfo          # Reuse the existing GradeInfo schema
    sections: List[SectionInfo] # Reuse the existing SectionInfo schema

# --- Content Schemas ---

class LessonBasicInfo(BaseModel):
    model_config = orm_config
    id: int
    name: str

class LessonCreate(BaseModel):
    name: str
    subject_id: int
    term_id: int

class LessonInfo(BaseModel):
    model_config = orm_config
    id: int
    name: str
    subject_id: int
    term_id: int
    # Example if Lesson needs to show linked Assessments
    # assessments: List['AssessmentBasicInfo'] = [] # Use forward reference

class PDFCreate(BaseModel):
    name: str
    lesson_id: int

class PDFUrlInfo(BaseModel):
    model_config = orm_config
    url: URLInfo

class PDFInfo(BaseModel):
    model_config = orm_config
    id: int
    name: str
    lesson_id: int
    size: Optional[int] = None
    urls: list[PDFUrlInfo] = []

class ImageCreate(BaseModel):
    name: str
    pdf_id: int
    image_number: Union[int, None] = None
    page_number: Union[int, None] = None
    chapter_number: Union[int, None] = None

class ImageInfo(BaseModel):
    model_config = orm_config
    id: int
    name: str
    pdf_id: int
    image_number: Union[int, None] = None
    page_number: Union[int, None] = None
    chapter_number: Union[int, None] = None
    url_id: Optional[int] = None

class VideoCreate(BaseModel):
    name: str
    lesson_id: int

class VideoInfo(BaseModel):
    model_config = orm_config
    id: int
    name: str
    lesson_id: int
    url_id: Optional[int] = None
    size: Optional[int] = None

    url_obj: Optional[URLInfo] = Field(None, validation_alias='url', exclude=True)

    @computed_field
    @property
    def url(self) -> Optional[str]:
        if self.url_obj:
            return self.url_obj.url
        return None


# --- Gemini Analysis / Question Generation Schemas ---
class QuestionTypeEnum(str, Enum):
    FILL_IN_BLANKS = "fill_in_blanks"
    MATCH_FOLLOWING = "match_following"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    SHORT_ANSWER = "short_answer"

class QuestionCount(BaseModel):
    type: QuestionTypeEnum
    count: int = Field(..., ge=0)

class QuestionAnalysisResponse(BaseModel):
    question_counts: List[QuestionCount]

class GeneratedQuestion(BaseModel):
    question_number: Optional[int] = None
    question_type: QuestionTypeEnum
    question_text: str
    options: Optional[List[str]] = None
    correct_answer: Optional[Union[str, List[str]]] = None
    explanation: Optional[str] = None
    reference_page: Optional[int] = None
    reference_section: Optional[str] = None
    image_svg: Optional[str] = None

class GenerateAssignmentResponse(BaseModel):
    generated_questions: List[GeneratedQuestion]
    raw_llm_output: Optional[str] = None

class ModifyAssignmentResponse(GenerateAssignmentResponse):
    pass


# --- Assessment Schemas ---

# Assessment Status Enum (re-declared or ensure it's imported/available)
class AssessmentStatusEnum(str, Enum):
    UPCOMING = "Upcoming"
    COMPLETED = "Completed"
    # GRADED = "Graded" # Consider if Graded is a separate status from Completed
    PENDING = "Pending" # For overdue and not completed

class AssessmentBase(BaseModel):
    # Fields common to Create and Info, *excluding* lesson_ids
    name: str
    description: Optional[str] = None
    subject_id: Optional[int] = None
    due_date: Optional[datetime] = None
    content: Optional[List[GeneratedQuestion]] = None
    assignment_format_id: Optional[int] = None

# Schema for creating an assessment, linking to multiple lessons
class AssessmentCreate(AssessmentBase):
    lesson_ids: Optional[List[int]] = None # List of Lesson IDs to associate

# Optional: Basic info schema if needed for lists
class AssessmentBasicInfo(BaseModel):
    model_config = orm_config
    id: int
    name: str
    subject_id: Optional[int] = None

class AssessmentInfo(AssessmentBase):
    model_config = orm_config
    id: int
    creation_date: datetime
    created_by_user_id: Optional[int] = None

    lessons: List[LessonBasicInfo] = [] # Expects a list of Lesson objects from the ORM
    assignment_format_obj: Optional['AssignmentFormatInfo'] = Field(None, validation_alias='assignment_format', exclude=True)

    @computed_field
    @property
    def assignment_format_name(self) -> Optional[str]:
        if self.assignment_format_obj:
            return self.assignment_format_obj.name
        return None

# --- Student Assignment Schema ---
class StudentAssignmentItem(BaseModel):
    """Schema for an assignment item as seen by a student."""
    model_config = orm_config
    assessment_id: int
    assessment_name: str
    subject_name: Optional[str] = None
    status: AssessmentStatusEnum
    due_date: Optional[datetime] = None
    score_achieved: Optional[float] = None
    max_score: Optional[float] = None

# --- Assignment Request/Response Schemas ---
class AssignAssessmentRequest(BaseModel):
    student_ids: Optional[List[int]] = None

class AssignmentResponse(BaseModel):
    message: str
    assessment_id: int
    section_id: int
    assigned_student_count: int
    assigned_student_ids: List[int]

# --- Student Assessment Score Schemas ---
class StudentAssessmentScoreBase(BaseModel):
    # Removed student_id as it's derived from the logged-in user
    assessment_id: int
    term_id: int
    score_achieved: float = Field(..., ge=0)
    max_score: float = Field(..., gt=0) # Must be greater than 0
    comments: Optional[str] = None

class StudentAssessmentScoreCreate(StudentAssessmentScoreBase):
    # Inherits fields from Base
    pass

class StudentAssessmentScoreUpdate(BaseModel): # If teachers update scores
    term_id: int
    score_achieved: float = Field(..., ge=0)
    max_score: float = Field(..., gt=0)
    comments: Optional[str] = None

class StudentAssessmentScoreInfo(StudentAssessmentScoreBase): # Response schema
    model_config = orm_config
    id: int
    student_id: int # Include student_id in the response
    attempt_timestamp: datetime # Automatically generated


# --- Dashboard Schemas (Student) ---
class WeeklyPerformanceData(BaseModel):
    model_config = orm_config
    day: str
    score_percentage: Optional[float] = None

class OverallAverageScoreData(BaseModel):
    model_config = orm_config
    average_score: Optional[float] = None

class TermSummaryData(BaseModel):
    model_config = orm_config
    total_lessons: int
    average_score: Optional[float] = None
    study_streak: int = 0

class SubjectTermPerformanceData(BaseModel):
    model_config = orm_config
    subject_id: int
    subject_name: str
    average_score: Optional[float] = None

class TermInfoBasic(BaseModel):
    model_config = orm_config
    term_id: int
    term_name: str
    year: int

class StudentDashboardData(BaseModel):
    model_config = orm_config
    weekly_performance: List[WeeklyPerformanceData]
    overall_average_score: OverallAverageScoreData
    available_terms: List[TermInfoBasic]


# --- Admin Dashboard Schemas ---
class StatCardData(BaseModel):
    model_config = orm_config
    title: str
    count: int

class DailyActivityData(BaseModel):
    model_config = orm_config
    day: str
    count: int

class RecentActivityItem(BaseModel):
    model_config = orm_config
    id: int
    timestamp: datetime
    action: str
    details: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    target_entity: Optional[str] = None
    target_entity_id: Optional[int] = None

class RecentUserItem(BaseModel):
    model_config = orm_config
    id: int
    username: str
    email: str
    role: str
    status: bool
    last_login: Optional[datetime] = None
    created_at: datetime


# --- Parent Dashboard Schemas ---
class ParentChildInfo(BaseModel):
    model_config = orm_config
    student_id: int
    student_name: str
    user_photo: Optional[str] = None
    grade_name: Optional[str] = None
    section_name: Optional[str] = None

class ParentSubjectPerformance(BaseModel):
    model_config = orm_config
    subject_id: int
    subject_name: str
    average_score: Optional[float] = None # Percentage

class ParentAssessmentStatus(BaseModel):
    model_config = orm_config
    assessment_id: int
    assessment_name: str
    subject_name: Optional[str] = None
    status: AssessmentStatusEnum
    due_date: Optional[datetime] = None
    score_achieved: Optional[float] = None
    max_score: Optional[float] = None

class ParentTimetableEntry(BaseModel):
    model_config = orm_config
    day_of_week: int
    start_time: time
    end_time: time
    subject_name: str
    teacher_name: Optional[str] = None


# --- Teacher Dashboard Schemas ---
class TeacherClassInfo(BaseModel):
    model_config = orm_config
    grade_id: int
    grade_name: str
    section_id: int
    section_name: str

class TeacherStudentProfileItem(BaseModel):
    model_config = orm_config
    student_id: int
    student_name: str
    student_username: str
    overall_average_score: Optional[float] = None
    user_photo: Optional[str] = None

class ClassPerformanceOverview(BaseModel):
    model_config = orm_config
    class_average_score: Optional[float] = None

class ClassSubjectPerformanceItem(BaseModel):
    model_config = orm_config
    subject_id: int
    subject_name: str
    class_average_score: Optional[float] = None

class TeacherLessonItem(BaseModel):
    model_config = orm_config
    lesson_id: int
    lesson_name: str
    subject_name: str
    term_name: str

# --- Timetable Schemas ---
class TimetableBase(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    start_time: time
    end_time: time
    section_id: int
    subject_id: int
    teacher_id: Optional[int] = None

    @validator('end_time')
    def end_time_must_be_after_start_time(cls, v, values):
        start_time = values.get('start_time')
        if start_time and v <= start_time:
            raise ValueError('End time must be after start time')
        return v

class TimetableCreate(TimetableBase):
    pass

class TimetableUpdate(TimetableBase):
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    section_id: Optional[int] = None
    subject_id: Optional[int] = None
    teacher_id: Optional[int] = None

    @validator('end_time')
    def end_time_must_be_after_start_time_update(cls, v, values):
        start_time = values.get('start_time')
        if start_time and v is not None and v <= start_time:
             raise ValueError('End time must be after start time')
        return v

class TimetableInfo(TimetableBase):
    model_config = orm_config
    id: int
    section_name: Optional[str] = None
    subject_name: Optional[str] = None
    teacher_name: Optional[str] = None

# --- Assignment Sample Schemas ---

class AssignmentSampleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    subject_id: int

class AssignmentSampleCreate(AssignmentSampleBase):
    pass

class AssignmentSampleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    subject_id: Optional[int] = None


class AssignmentSampleInfo(AssignmentSampleBase):
    model_config = orm_config
    id: int
    created_by_user_id: Optional[int] = None
    file_size: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    urls: List[URLInfo] = []

    creator_obj: Optional[UserDetails] = Field(None, validation_alias='creator', exclude=True)

    @computed_field
    @property
    def creator_username(self) -> Optional[str]:
        if self.creator_obj:
            return self.creator_obj.username
        return None

# --- Assignment Format Schemas ---

class AssignmentFormatQuestionInfo(BaseModel):
    model_config = orm_config
    id: int
    question_type: QuestionTypeEnum
    count: int
    assignment_format_id: int

class AssignmentFormatBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    subject_id: int

class AssignmentFormatCreate(AssignmentFormatBase):
    questions: List[QuestionCount]

    @validator('questions')
    def questions_must_have_unique_types(cls, v):
        types_seen = set()
        for q_count in v:
            if q_count.type in types_seen:
                raise ValueError(f"Duplicate question type '{q_count.type.value}' found in input.")
            types_seen.add(q_count.type)
        return v

class AssignmentFormatUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    subject_id: Optional[int] = None
    questions: Optional[List[QuestionCount]] = None

    @validator('questions')
    def questions_must_have_unique_types_update(cls, v):
        if v is None:
            return v
        types_seen = set()
        for q_count in v:
            if q_count.type in types_seen:
                raise ValueError(f"Duplicate question type '{q_count.type.value}' found in input.")
            types_seen.add(q_count.type)
        return v

class AssignmentFormatInfo(AssignmentFormatBase):
    model_config = orm_config
    id: int
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    questions: List[AssignmentFormatQuestionInfo] = []

    creator_obj: Optional[UserDetails] = Field(None, validation_alias='creator', exclude=True)
    subject_obj: Optional[SubjectInfo] = Field(None, validation_alias='subject', exclude=True)

    @computed_field
    @property
    def creator_username(self) -> Optional[str]:
        if self.creator_obj:
            return self.creator_obj.username
        return None

    @computed_field
    @property
    def subject_name(self) -> Optional[str]:
        if self.subject_obj:
            return self.subject_obj.name
        return None

# --- Assignment Distribution Schemas ---

class AssignmentDistributionStudentInfo(BaseModel):
    model_config = orm_config
    id: int
    name: str

class AssignmentDistributionBase(BaseModel):
    assessment_id: int
    section_id: int
    assign_to_all_students: bool = True

class AssignmentDistributionCreate(AssignmentDistributionBase):
    student_ids: Optional[List[int]] = None

    @validator('student_ids', pre=True, always=True)
    def check_student_ids_required(cls, v, values):
        assign_all = values.get('assign_to_all_students')
        if assign_all is False and (v is None or not v):
            raise ValueError('student_ids must be provided when assign_to_all_students is False')
        if assign_all is True and v is not None:
             return None
        return v

class AssignmentDistributionInfo(AssignmentDistributionBase):
    model_config = orm_config
    id: int
    assigned_at: datetime
    assigned_by_user_id: Optional[int] = None

    assessment: AssessmentBasicInfo
    section: SectionInfo
    assigned_by_user: Optional[UserDetails] = None
    specific_students: List[AssignmentDistributionStudentInfo] = []


# --- LLM Token Usage Schemas ---
class LLMTokenUsageBase(BaseModel):
    user_id: Optional[int] = None
    session_id: Optional[str] = None
    action: str
    model_name: Optional[str] = None
    input_tokens: int
    output_tokens: int
    total_tokens: int

class LLMTokenUsageCreate(BaseModel):
    session_id: Optional[str] = None
    action: str
    model_name: Optional[str] = None
    input_tokens: int
    output_tokens: int
    total_tokens: int

class LLMTokenUsageInfo(LLMTokenUsageBase):
    id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


# --- Forward Reference Resolution / Model Rebuild (Pydantic v2) ---
StudentDetails.model_rebuild()
TeacherDetails.model_rebuild()
ParentDetails.model_rebuild()
PDFInfo.model_rebuild()
VideoInfo.model_rebuild()
AssignmentSampleInfo.model_rebuild()
AssignmentFormatInfo.model_rebuild()
AssessmentInfo.model_rebuild()
TimetableInfo.model_rebuild()
SectionInfo.model_rebuild()
AssignmentDistributionInfo.model_rebuild()
AssignmentResponse.model_rebuild()
AssignAssessmentRequest.model_rebuild()
SubjectInfo.model_rebuild()
SubjectGradeSectionDetails.model_rebuild()
StudentAssignmentItem.model_rebuild()
StudentAssessmentScoreInfo.model_rebuild() # Added
# LessonInfo.model_rebuild() # Only needed if LessonInfo uses forward refs