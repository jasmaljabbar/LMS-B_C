# backend/routes/student_assessment_scores.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
from typing import List
from datetime import datetime

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.logger_utils import log_activity # Import log_activity

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/student-assessment-scores",
    tags=["Student Assessment Scores"],
    dependencies=[Depends(get_current_user)]
)

# --- Helper Function to Get Student ID ---
# (Copied from student_assignments.py/dashboard.py for simplicity)
def _get_student_id_from_user(current_user: models.User, db: Session) -> int:
    """Gets the student ID associated with the logged-in user."""
    if current_user.user_type != "Student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access restricted to students.")
    student = db.query(models.Student.id).filter(models.Student.user_id == current_user.id).first()
    if not student:
        logger.error(f"No student profile found for user_id {current_user.id} ('{current_user.username}')")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found for the logged-in user.")
    return student.id

# --- Helper to check if assessment was assigned to student ---
def _verify_assessment_assigned_to_student(student_id: int, assessment_id: int, db: Session):
    """Checks if the assessment was distributed to the student."""
    # Find the student's current section ID
    current_year = datetime.now().year
    student_year_info = db.query(models.StudentYear.sectionId).filter(
        models.StudentYear.studentId == student_id,
        models.StudentYear.year == current_year
    ).first()

    if not student_year_info:
        raise HTTPException(status_code=400, detail="Cannot submit score: Student not currently assigned to a section.")

    current_section_id = student_year_info.sectionId

    # Check if a distribution exists for this assessment targeting this student
    distribution_exists = db.query(models.AssignmentDistribution.id).filter(
        models.AssignmentDistribution.assessment_id == assessment_id,
        or_(
            # Assigned to the student's section AND for everyone
            and_(
                models.AssignmentDistribution.section_id == current_section_id,
                models.AssignmentDistribution.assign_to_all_students == True
            ),
            # Assigned specifically to this student
            models.AssignmentDistribution.specific_students.any(models.Student.id == student_id)
        )
    ).limit(1).first() # Just need to know if at least one exists

    if not distribution_exists:
        logger.warning(f"Student {student_id} attempted to submit score for unassigned assessment {assessment_id}.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This assessment was not assigned to you.")

@router.post("/", response_model=schemas.StudentAssessmentScoreInfo, status_code=status.HTTP_201_CREATED)
def submit_assessment_score(
    score_data: schemas.StudentAssessmentScoreCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Allows a logged-in student to submit their score for an assigned assessment.
    """
    student_id = _get_student_id_from_user(current_user, db)

    # --- Validation ---
    # 1. Check if assessment exists
    assessment = db.query(models.Assessment.id, models.Assessment.name).filter(models.Assessment.id == score_data.assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail=f"Assessment with ID {score_data.assessment_id} not found.")

    # 2. Check if term exists
    term_exists = db.query(models.Term.id).filter(models.Term.id == score_data.term_id).first()
    if not term_exists:
        raise HTTPException(status_code=404, detail=f"Term with ID {score_data.term_id} not found.")

    # 3. Verify the assessment was assigned to this student
    _verify_assessment_assigned_to_student(student_id, score_data.assessment_id, db)

    # --- Create Score Record ---
    db_score = models.StudentAssessmentScore(
        student_id=student_id, # Derived from logged-in user
        assessment_id=score_data.assessment_id,
        term_id=score_data.term_id,
        score_achieved=score_data.score_achieved,
        max_score=score_data.max_score,
        comments=score_data.comments
        # attempt_timestamp is handled by server_default in the model
    )

    try:
        db.add(db_score)
        db.commit()
        db.refresh(db_score)

        # Log activity
        log_activity(
            db=db,
            user_id=current_user.id,
            action='ASSESSMENT_SCORE_SUBMITTED',
            details=f"Student '{current_user.username}' (ID: {student_id}) submitted score {db_score.score_achieved}/{db_score.max_score} for assessment '{assessment.name}' (ID: {db_score.assessment_id}).",
            target_entity='StudentAssessmentScore',
            target_entity_id=db_score.id
        )

        return db_score # Pydantic will map this to StudentAssessmentScoreInfo

    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting assessment score for student {student_id}, assessment {score_data.assessment_id}: {e}", exc_info=True)
        # Consider more specific error handling (e.g., IntegrityError) if needed
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to submit assessment score.")


def get_or_create_score_record(
    db: Session,
    student_id: int,
    homework_id: int,
    score_data: dict
) -> models.StudentHomeworkScore:
    """Handles automatic score recording"""
    score_record = db.query(models.StudentHomeworkScore).filter(
        models.StudentHomeworkScore.student_id == student_id,
        models.StudentHomeworkScore.homework_id == homework_id
    ).first()

    if score_record:
        # Update existing record
        score_record.score_achieved = score_data['score_achieved']
        score_record.max_score = score_data['max_score']
        score_record.comments = score_data['comments']
        score_record.graded_at = datetime.utcnow()
    else:
        # Create new auto-score record
        score_record = models.StudentHomeworkScore(
            student_id=student_id,
            homework_id=homework_id,
            score_achieved=score_data['score_achieved'],
            max_score=score_data['max_score'],
            comments=score_data['comments'],
            graded_by=None  # Auto-scored by system
        )
        db.add(score_record)
    
    return score_record