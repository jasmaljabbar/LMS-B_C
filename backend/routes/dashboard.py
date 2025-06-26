# backend/routes/dashboard.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, case, cast, Date, Integer # Import necessary SQL functions
from typing import List, Optional, Dict
from datetime import datetime, timedelta, date

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/dashboard/student",
    tags=["Student Dashboard"],
    dependencies=[Depends(get_current_user)] # Apply auth to all endpoints here
)

# --- Helper Function to Get Student ID ---
def _get_student_id_from_user(current_user: models.User, db: Session) -> int:
    """Gets the student ID associated with the logged-in user."""
    if current_user.user_type != "Student":
        # This endpoint is only for students
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to students."
        )
    student = db.query(models.Student.id).filter(models.Student.user_id == current_user.id).first()
    if not student:
        logger.error(f"No student profile found for user_id {current_user.id} ('{current_user.username}')")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found for the logged-in user."
        )
    return student.id

# --- Helper Function to Get Student's Current Grade ID ---
def _get_student_grade_id(student_id: int, db: Session) -> Optional[int]:
    """Gets the current grade ID for a student."""
    current_year = datetime.now().year # Or determine academic year differently
    student_year_info = db.query(models.StudentYear).options(
        joinedload(models.StudentYear.section).joinedload(models.Section.grade)
    ).filter(
        models.StudentYear.studentId == student_id,
        models.StudentYear.year == current_year # Filter by current year
    ).first()
    print(student_year_info,'...........')
    if student_year_info and student_year_info.section and student_year_info.section.grade:
        return student_year_info.section.grade.id
    logger.warning(f"Could not determine current grade for student_id {student_id} in year {current_year}")
    return None # Student might not be assigned for the current year/section/grade


# --- API Endpoints ---

@router.get("/weekly-performance", response_model=List[schemas.WeeklyPerformanceData])
def get_weekly_performance(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Calculates the average homework score percentage for the last 7 days."""
    student_id = _get_student_id_from_user(current_user, db)
    today = datetime.utcnow().date()
    seven_days_ago = today - timedelta(days=6)
    
    # Query homework scores from the last 7 days
    scores_last_7_days = db.query(
        cast(models.StudentHomeworkScore.graded_at, Date).label("graded_date"),
        func.avg(
            (models.StudentHomeworkScore.score_achieved / models.StudentHomeworkScore.max_score) * 100
        ).label("avg_percentage")
    ).filter(
        models.StudentHomeworkScore.student_id == student_id,
        cast(models.StudentHomeworkScore.graded_at, Date) >= seven_days_ago,
        cast(models.StudentHomeworkScore.graded_at, Date) <= today,
        models.StudentHomeworkScore.max_score > 0  # Avoid division by zero
    ).group_by(
        cast(models.StudentHomeworkScore.graded_at, Date)
    ).order_by(
        cast(models.StudentHomeworkScore.graded_at, Date)
    ).all()

    # Create a dictionary for quick lookup
    scores_dict = {result.graded_date: result.avg_percentage for result in scores_last_7_days}

    # Build the response, filling in missing days with None
    weekly_data: List[schemas.WeeklyPerformanceData] = []
    for i in range(7):
        day_date = seven_days_ago + timedelta(days=i)
        day_abbr = day_date.strftime('%a')
        score = scores_dict.get(day_date)
        weekly_data.append(
            schemas.WeeklyPerformanceData(
                day=day_abbr,
                score_percentage=score
            )
        )

    return weekly_data

@router.get("/overall-average-score", response_model=schemas.OverallAverageScoreData)
def get_overall_average_score(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Calculates the overall average score percentage across all assessments."""
    student_id = _get_student_id_from_user(current_user, db)

    # Calculate average of individual assessment percentages
    result = db.query(
        func.avg(
            (models.StudentAssessmentScore.score_achieved / models.StudentAssessmentScore.max_score) * 100
        ).label("overall_avg")
    ).filter(
        models.StudentAssessmentScore.student_id == student_id,
        models.StudentAssessmentScore.max_score > 0
    ).first()

    return schemas.OverallAverageScoreData(average_score=result.overall_avg if result else None)


@router.get("/available-terms", response_model=List[schemas.TermInfoBasic])
def get_available_terms_for_student(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Gets the list of terms available for the student's current grade and year."""
    student_id = _get_student_id_from_user(current_user, db)
    grade_id = _get_student_grade_id(student_id, db)
    current_year = datetime.now().year # Or determine academic year differently

    if not grade_id:
        # Return empty list or raise error if grade cannot be determined
         logger.warning(f"Cannot fetch terms as grade for student {student_id} in year {current_year} is unknown.")
         return []
        # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student grade for current year not found.")


    terms = db.query(
        models.Term.id.label("term_id"),
        models.Term.name.label("term_name"),
        models.Term.year
    ).filter(
        models.Term.grade_id == grade_id,
        models.Term.year == current_year # Assuming terms are defined per year
    ).order_by(
        models.Term.start_date, # Order by start date if available
        models.Term.name        # Then by name
    ).all()

    # Map the result to the Pydantic schema
    return [schemas.TermInfoBasic.from_orm(term) for term in terms]


@router.get("/term-summary/{term_id}", response_model=schemas.TermSummaryData)
def get_term_summary(
    term_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Gets the summary metrics (lessons, average score) for a specific term."""
    student_id = _get_student_id_from_user(current_user, db)
    grade_id = _get_student_grade_id(student_id, db)

    if not grade_id:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student grade for current year not found.")

    # 1. Get Total Lessons for the student's grade in this term
    total_lessons = db.query(func.count(models.Lesson.id)).join(models.Subject).filter(
        models.Lesson.term_id == term_id,
        models.Subject.grade_id == grade_id
    ).scalar() or 0

    # 2. Get Average Score for this term
    term_avg_result = db.query(
        func.avg(
            (models.StudentAssessmentScore.score_achieved / models.StudentAssessmentScore.max_score) * 100
        ).label("term_avg")
    ).filter(
        models.StudentAssessmentScore.student_id == student_id,
        models.StudentAssessmentScore.term_id == term_id,
        models.StudentAssessmentScore.max_score > 0
    ).first()
    term_average_score = term_avg_result.term_avg if term_avg_result else None

    # 3. Study Streak (Placeholder)
    # This requires a separate mechanism to track daily activity (logins, lesson views, assessments taken)
    study_streak = 0 # Placeholder

    return schemas.TermSummaryData(
        total_lessons=total_lessons,
        average_score=term_average_score,
        study_streak=study_streak
    )


@router.get("/subject-performance/{term_id}", response_model=List[schemas.SubjectTermPerformanceData])
def get_subject_performance_by_term(
    term_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Gets the average score for each subject within a specific term."""
    student_id = _get_student_id_from_user(current_user, db)
    grade_id = _get_student_grade_id(student_id, db)

    if not grade_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student grade for current year not found.")

    # Get all subjects for the student's grade
    subjects_in_grade = db.query(
        models.Subject.id,
        models.Subject.name
    ).filter(
        models.Subject.grade_id == grade_id
    ).all()

    if not subjects_in_grade:
        return [] # No subjects defined for this grade

    subject_ids = [s.id for s in subjects_in_grade]
    subject_name_map = {s.id: s.name for s in subjects_in_grade}

    # Query average scores per subject for the given student and term
    # We need Assessment -> Subject link
    subject_scores = db.query(
        models.Assessment.subject_id,
        func.avg(
            (models.StudentAssessmentScore.score_achieved / models.StudentAssessmentScore.max_score) * 100
        ).label("avg_subj_score")
    ).join(
        models.StudentAssessmentScore, models.Assessment.id == models.StudentAssessmentScore.assessment_id
    ).filter(
        models.StudentAssessmentScore.student_id == student_id,
        models.StudentAssessmentScore.term_id == term_id,
        models.Assessment.subject_id.in_(subject_ids), # Filter assessments by subjects in the student's grade
        models.StudentAssessmentScore.max_score > 0
    ).group_by(
        models.Assessment.subject_id
    ).all()

    scores_map = {result.subject_id: result.avg_subj_score for result in subject_scores}

    # Build the final list, including subjects with no scores (average = None)
    performance_data: List[schemas.SubjectTermPerformanceData] = []
    for subj_id in subject_ids:
        performance_data.append(
            schemas.SubjectTermPerformanceData(
                subject_id=subj_id,
                subject_name=subject_name_map.get(subj_id, "Unknown Subject"),
                average_score=scores_map.get(subj_id) # Will be None if no scores found
            )
        )

    return performance_data

# Potential combined endpoint (optional, might be too much data at once)
# @router.get("/all-data", response_model=schemas.StudentDashboardData)
# async def get_all_dashboard_data(
#     db: Session = Depends(get_db),
#     current_user: models.User = Depends(get_current_user)
# ):
#     """Fetches data for multiple dashboard components in one call."""
#     # Note: Be mindful of performance if queries become very complex
#     weekly = get_weekly_performance(db, current_user)
#     overall_avg = get_overall_average_score(db, current_user)
#     terms = get_available_terms_for_student(db, current_user)

#     return schemas.StudentDashboardData(
#         weekly_performance=weekly,
#         overall_average_score=overall_avg,
#         available_terms=terms
#     )


@router.get("/subject-performance", response_model=List[schemas.SubjectTermPerformanceData])
def get_subject_performance(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Gets the average homework score percentage for each subject (all terms)."""
    student_id = _get_student_id_from_user(current_user, db)
    grade_id = _get_student_grade_id(student_id, db)

    if not grade_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student grade not found"
        )

    # Get all subjects for the student's grade
    subjects_in_grade = db.query(
        models.Subject.id,
        models.Subject.name
    ).filter(
        models.Subject.grade_id == grade_id
    ).all()

    if not subjects_in_grade:
        return []  # No subjects defined for this grade

    subject_ids = [s.id for s in subjects_in_grade]
    subject_name_map = {s.id: s.name for s in subjects_in_grade}

    # Query average homework scores per subject
    subject_scores = db.query(
        models.Homework.subject_id,
        func.avg(
            (models.StudentHomeworkScore.score_achieved / models.StudentHomeworkScore.max_score) * 100
        ).label("avg_subj_score")
    ).join(
        models.StudentHomeworkScore,
        models.Homework.id == models.StudentHomeworkScore.homework_id
    ).filter(
        models.StudentHomeworkScore.student_id == student_id,
        models.Homework.subject_id.in_(subject_ids),
        models.StudentHomeworkScore.max_score > 0
    ).group_by(
        models.Homework.subject_id
    ).all()

    scores_map = {result.subject_id: result.avg_subj_score for result in subject_scores}

    # Build response including subjects with no scores
    performance_data = []
    for subj_id in subject_ids:
        performance_data.append(
            schemas.SubjectTermPerformanceData(
                subject_id=subj_id,
                subject_name=subject_name_map[subj_id],
                average_score=scores_map.get(subj_id)  # None if no scores
            )
        )

    return performance_data