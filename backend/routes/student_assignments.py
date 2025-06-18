# backend/routes/student_assignments.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload, selectinload, aliased, contains_eager
from sqlalchemy import func, case, cast, Date, Integer, distinct, desc, and_, or_
from typing import List, Optional
from datetime import datetime

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/student/assignments", # Clearer prefix for student-specific endpoints
    tags=["Student Assignments"],
    dependencies=[Depends(get_current_user)] # Apply auth to all endpoints here
)

# --- Helper Function to Get Student ID ---
# (Copied from dashboard.py for simplicity, could be moved to a common utils/helpers)
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

@router.get("/", response_model=List[schemas.StudentAssignmentItem])
def get_student_assignments(
    status_filter: Optional[schemas.AssessmentStatusEnum] = Query(None, description="Filter by status: Upcoming, Completed, Pending"),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Retrieves a list of assessments assigned to the logged-in student,
    optionally filtered by status.
    """
    student_id = _get_student_id_from_user(current_user, db)
    now = datetime.utcnow()

    # Find the student's current section ID
    current_year = datetime.now().year
    student_year_info = db.query(models.StudentYear.sectionId).filter(
        models.StudentYear.studentId == student_id,
        models.StudentYear.year == current_year
    ).first()

    if not student_year_info:
        logger.info(f"Student {student_id} is not assigned to a section for the current year {current_year}.")
        return [] # Return empty list if not assigned to a section

    current_section_id = student_year_info.sectionId

    # Alias for StudentAssessmentScore to filter specifically for the current student's score
    ScoreAlias = aliased(models.StudentAssessmentScore)

    # Query distributions relevant to the student
    distributions_query = db.query(
        models.AssignmentDistribution
    ).filter(
        or_(
            # Assigned to the student's section AND for everyone in the section
            and_(
                models.AssignmentDistribution.section_id == current_section_id,
                models.AssignmentDistribution.assign_to_all_students == True
            ),
            # Assigned specifically to this student
            models.AssignmentDistribution.specific_students.any(models.Student.id == student_id)
        )
    )
    # Select the assessment IDs from these relevant distributions
    relevant_assessment_ids = [d.assessment_id for d in distributions_query.all()]

    if not relevant_assessment_ids:
        return [] # No assignments distributed to this student/section

    # Now query the Assessments based on the relevant IDs and join necessary info
    # Determine status based on score existence and due date
    status_logic = case(
        (ScoreAlias.id != None, schemas.AssessmentStatusEnum.COMPLETED),
        (and_(ScoreAlias.id == None, or_(models.Assessment.due_date == None, models.Assessment.due_date > now)), schemas.AssessmentStatusEnum.UPCOMING),
        (and_(ScoreAlias.id == None, models.Assessment.due_date != None, models.Assessment.due_date <= now), schemas.AssessmentStatusEnum.PENDING),
        else_=schemas.AssessmentStatusEnum.PENDING # Default fallback if needed
    ).label("status")

    final_query = db.query(
        models.Assessment,
        models.Subject.name.label("subject_name"),
        ScoreAlias.score_achieved,
        ScoreAlias.max_score,
        ScoreAlias.attempt_timestamp,
        status_logic
    ).select_from(models.Assessment).join(
        models.Subject, models.Assessment.subject_id == models.Subject.id
    ).outerjoin( # Outer join to include assessments the student hasn't taken yet
        ScoreAlias,
        and_(
            models.Assessment.id == ScoreAlias.assessment_id,
            ScoreAlias.student_id == student_id # Filter scores *only* for the current student
        )
    ).filter(
        models.Assessment.id.in_(relevant_assessment_ids) # Only include assessments distributed to the student
    )

    # Apply status filter if provided
    if status_filter:
        final_query = final_query.filter(status_logic == status_filter)

    # Apply Ordering (Upcoming first, then Pending, then Completed)
    final_query = final_query.order_by(
        case( # Order by status enum value
            (status_logic == schemas.AssessmentStatusEnum.UPCOMING, 1),
            (status_logic == schemas.AssessmentStatusEnum.PENDING, 2),
            (status_logic == schemas.AssessmentStatusEnum.COMPLETED, 3),
            else_=4
        ),
        models.Assessment.due_date.is_(None).desc(), # NULLs first for due date
        models.Assessment.due_date.asc(),            # Then ascending due date
        desc(ScoreAlias.attempt_timestamp)           # Then by attempt time for completed
    )

    # Apply pagination
    results = final_query.offset(skip).limit(limit).all()

    # Map results to the response schema
    assignment_items = []
    for row in results:
        assignment_items.append(schemas.StudentAssignmentItem(
            assessment_id=row.Assessment.id,
            assessment_name=row.Assessment.name,
            subject_name=row.subject_name,
            status=row.status, # Status comes directly from the query result
            due_date=row.Assessment.due_date,
            score_achieved=row.score_achieved,
            max_score=row.max_score
        ))

    return assignment_items

