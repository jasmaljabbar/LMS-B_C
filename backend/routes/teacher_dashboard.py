# backend/routes/teacher_dashboard.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload, selectinload, aliased
from sqlalchemy import func, case, cast, Date, Integer, distinct, desc, and_
from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/dashboard/teacher",
    tags=["Teacher Dashboard"],
    dependencies=[Depends(get_current_user)] # Apply auth to all endpoints here
)

# --- Helper: Check if Teacher ---
def _get_teacher_id_from_user(current_user: models.User, db: Session) -> int:
    """Gets the teacher ID associated with the logged-in user."""
    if current_user.user_type != "Teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to teachers."
        )
    teacher = db.query(models.Teacher.id).filter(models.Teacher.user_id == current_user.id).first()
    if not teacher:
        logger.error(f"No teacher profile found for user_id {current_user.id} ('{current_user.username}')")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Teacher profile not found for the logged-in user."
        )
    return teacher.id

# --- Helper: Get Student IDs in a specific Section for the current year ---
def _get_students_in_section(grade_id: int, section_id: int, db: Session) -> List[int]:
    """Returns a list of student IDs currently assigned to the given section/grade for the current year."""
    current_year = datetime.now().year # Or determine academic year differently

    # First check if grade and section are valid and related
    section = db.query(models.Section.id).filter(
        models.Section.id == section_id,
        models.Section.grade_id == grade_id # Check relationship
    ).first()
    if not section:
        # Provide more specific error messages
        grade_exists = db.query(models.Grade.id).filter(models.Grade.id == grade_id).first()
        section_exists = db.query(models.Section.id).filter(models.Section.id == section_id).first()
        if not grade_exists:
             raise HTTPException(status_code=404, detail=f"Grade with ID {grade_id} not found.")
        if not section_exists:
            raise HTTPException(status_code=404, detail=f"Section with ID {section_id} not found.")
        # If both exist but aren't related
        raise HTTPException(status_code=404, detail=f"Section ID {section_id} does not belong to Grade ID {grade_id}.")


    student_ids_query = db.query(models.StudentYear.studentId).filter(
        models.StudentYear.sectionId == section_id,
        models.StudentYear.year == current_year
    ).distinct() # Ensure distinct student IDs

    student_ids = [s_id[0] for s_id in student_ids_query.all()]
    logger.info(f"Found {len(student_ids)} students for Grade {grade_id}, Section {section_id}, Year {current_year}.")
    return student_ids


# --- API Endpoints ---

@router.get("/teaching-assignments", response_model=List[schemas.TeacherClassInfo])
def get_teacher_assignments(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Lists potential Grade/Section assignments for the teacher.
    WORKAROUND: Determines assignments based on Assessments created by the teacher's user ID.
    A dedicated linking table (teacher_sections) is highly recommended for accuracy.
    """
    teacher_user_id = current_user.id # Use the user ID directly
    _get_teacher_id_from_user(current_user, db) # Verify it's a teacher

    # Query based on Assessments created by the user
    # We find the distinct Grades/Sections associated with the Subjects of the Assessments they created
    assignments_query = db.query(
        distinct(models.Grade.id).label("grade_id"),
        models.Grade.name.label("grade_name"),
        models.Section.id.label("section_id"),
        models.Section.name.label("section_name")
    ).select_from(models.Assessment).join(
        models.Subject, models.Assessment.subject_id == models.Subject.id
    ).join(
        models.Grade, models.Subject.grade_id == models.Grade.id
    ).join(
        models.Section, models.Grade.id == models.Section.grade_id # Join all sections in that grade
    ).filter(
        models.Assessment.created_by_user_id == teacher_user_id
    ).order_by( # Add ordering for consistency
        models.Grade.name, models.Section.name
    ).distinct() # Apply distinct across all selected columns

    results = assignments_query.all()

    if not results:
         logger.warning(f"Could not determine teaching assignments for teacher user ID {teacher_user_id} based on created assessments.")
         return []

    # Map results to the schema
    return [schemas.TeacherClassInfo.from_orm(row) for row in results]


@router.get("/student-profiles/{grade_id}/{section_id}", response_model=List[schemas.TeacherStudentProfileItem])
def get_student_profiles_for_class(
    grade_id: int,
    section_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Gets the list of students in the specified class with their overall average score."""
    _get_teacher_id_from_user(current_user, db) # Verify teacher access
    student_ids = _get_students_in_section(grade_id, section_id, db)

    if not student_ids:
        return [] # No students in this section for the current year

    # Fetch student details (name, username, photo)
    students_info_query = db.query(
        models.Student.id,
        models.Student.name,
        models.User.username,
        models.User.photo
    ).join(models.User, models.Student.user_id == models.User.id).filter(
        models.Student.id.in_(student_ids)
    ).order_by(models.Student.name) # Order students by name

    students_info = students_info_query.all()

    if not students_info:
        # This case should ideally not happen if student_ids were found
        logger.warning(f"Found student IDs {student_ids} but could not fetch student/user details for Grade {grade_id}, Section {section_id}.")
        return []

    # Fetch average scores for these students (across all their assessments)
    avg_scores_query = db.query(
        models.StudentAssessmentScore.student_id,
        func.avg(
            # Ensure division by zero is handled if max_score could be 0 (though schema prevents it)
            # --- CORRECTED case() SYNTAX ---
            case((models.StudentAssessmentScore.max_score > 0, (models.StudentAssessmentScore.score_achieved / models.StudentAssessmentScore.max_score) * 100), else_=0)
            # --- END CORRECTION ---
            # (models.StudentAssessmentScore.score_achieved / models.StudentAssessmentScore.max_score) * 100
        ).label("avg_score_percent")
    ).filter(
        models.StudentAssessmentScore.student_id.in_(student_ids)
        # models.StudentAssessmentScore.max_score > 0 # Schema enforces gt=0
    ).group_by(
        models.StudentAssessmentScore.student_id
    )

    avg_scores = avg_scores_query.all()

    # Create a dictionary for quick score lookup
    score_map = {score.student_id: round(score.avg_score_percent, 2) if score.avg_score_percent is not None else None for score in avg_scores} # Round scores

    # Build response
    student_profiles: List[schemas.TeacherStudentProfileItem] = []
    for student in students_info:
        student_profiles.append(schemas.TeacherStudentProfileItem(
            student_id=student.id,
            student_name=student.name,
            student_username=student.username, # Use username as the ID shown in mock
            user_photo=student.photo,
            overall_average_score=score_map.get(student.id) # Will be None if student has no scores
        ))

    return student_profiles


@router.get("/class-performance-overview/{grade_id}/{section_id}", response_model=schemas.ClassPerformanceOverview)
def get_class_performance_overview(
    grade_id: int,
    section_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Calculates the overall class average score."""
    _get_teacher_id_from_user(current_user, db)
    student_ids = _get_students_in_section(grade_id, section_id, db)

    if not student_ids:
        logger.info(f"No students found for Grade {grade_id}, Section {section_id}. Returning empty performance overview.")
        return schemas.ClassPerformanceOverview(class_average_score=None)

    # Calculate the average score across all assessments taken by students in this section
    class_avg_result = db.query(
        func.avg(
            # --- CORRECTED case() SYNTAX ---
             case((models.StudentAssessmentScore.max_score > 0, (models.StudentAssessmentScore.score_achieved / models.StudentAssessmentScore.max_score) * 100), else_=0)
            # --- END CORRECTION ---
            # (models.StudentAssessmentScore.score_achieved / models.StudentAssessmentScore.max_score) * 100
        ).label("class_avg")
    ).filter(
        models.StudentAssessmentScore.student_id.in_(student_ids)
        # models.StudentAssessmentScore.max_score > 0 # Schema enforces gt=0
    ).first()

    class_average = round(class_avg_result.class_avg, 2) if class_avg_result and class_avg_result.class_avg is not None else None

    return schemas.ClassPerformanceOverview(
        class_average_score=class_average
    )

@router.get("/class-subject-performance/{grade_id}/{section_id}", response_model=List[schemas.ClassSubjectPerformanceItem])
def get_class_subject_performance(
    grade_id: int,
    section_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Calculates the average score for each subject for the students in the specified class."""
    _get_teacher_id_from_user(current_user, db)
    student_ids = _get_students_in_section(grade_id, section_id, db)

    if not student_ids:
        return []

    # Get subjects relevant to this grade
    subjects_query = db.query(models.Subject.id, models.Subject.name).filter(
        models.Subject.grade_id == grade_id
    ).order_by(models.Subject.name) # Order subjects by name

    subjects = subjects_query.all()

    if not subjects:
        logger.warning(f"No subjects found for Grade ID {grade_id}.")
        return []

    subject_map = {s.id: s.name for s in subjects}
    subject_ids = list(subject_map.keys())

    # Calculate average score per subject for students in this section
    subject_avg_scores_query = db.query(
        models.Assessment.subject_id,
        func.avg(
            # --- CORRECTED case() SYNTAX ---
            case((models.StudentAssessmentScore.max_score > 0, (models.StudentAssessmentScore.score_achieved / models.StudentAssessmentScore.max_score) * 100), else_=0)
            # --- END CORRECTION ---
            # (models.StudentAssessmentScore.score_achieved / models.StudentAssessmentScore.max_score) * 100
        ).label("avg_subj_score_percent")
    ).join(
        models.StudentAssessmentScore, models.Assessment.id == models.StudentAssessmentScore.assessment_id
    ).filter(
        models.StudentAssessmentScore.student_id.in_(student_ids),
        models.Assessment.subject_id.in_(subject_ids), # Ensure assessment belongs to relevant subjects
        # models.StudentAssessmentScore.max_score > 0 # Schema enforces gt=0
    ).group_by(
        models.Assessment.subject_id
    )

    subject_avg_scores = subject_avg_scores_query.all()

    # Create a dictionary for quick score lookup
    subj_score_map = {score.subject_id: round(score.avg_subj_score_percent, 2) if score.avg_subj_score_percent is not None else None for score in subject_avg_scores} # Round scores

    # Build response, including subjects with no scores yet for this class
    subject_performance: List[schemas.ClassSubjectPerformanceItem] = []
    for subj_id, subj_name in subject_map.items():
        subject_performance.append(schemas.ClassSubjectPerformanceItem(
            subject_id=subj_id,
            subject_name=subj_name,
            class_average_score=subj_score_map.get(subj_id) # Will be None if no scores
        ))

    return subject_performance

@router.get("/lessons/{grade_id}", response_model=List[schemas.TeacherLessonItem])
def get_lessons_for_grade(
    grade_id: int,
    # section_id: Optional[int] = None, # Add if lessons become section-specific
    subject_id: Optional[int] = None, # Add filter by subject if needed
    term_id: Optional[int] = None, # Add filter by term if needed
    limit: int = Query(20, ge=1, le=100), # Limit results with validation
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Gets lessons associated with the subjects of a given grade, optionally filtered."""
    _get_teacher_id_from_user(current_user, db)

    # Base query
    lessons_query = db.query(
        models.Lesson.id.label("lesson_id"),
        models.Lesson.name.label("lesson_name"),
        models.Subject.name.label("subject_name"),
        models.Term.name.label("term_name")
        # Add models.Lesson.created_at if you add that column
    ).join(
        models.Subject, models.Lesson.subject_id == models.Subject.id
    ).join(
        models.Term, models.Lesson.term_id == models.Term.id
    ).filter(
        models.Subject.grade_id == grade_id # Filter by grade via the Subject table
    )

    # Apply optional filters
    if subject_id:
        lessons_query = lessons_query.filter(models.Lesson.subject_id == subject_id)
    if term_id:
        lessons_query = lessons_query.filter(models.Lesson.term_id == term_id)

    # Apply ordering and limit
    lessons = lessons_query.order_by(
        # models.Lesson.created_at.desc() # Order by creation date if available
        models.Term.year.desc(), # Order by term year/name first maybe?
        models.Term.name,
        models.Subject.name,
        models.Lesson.name
    ).limit(limit).all()

    # Map results to schema
    return [schemas.TeacherLessonItem.from_orm(lesson) for lesson in lessons]
