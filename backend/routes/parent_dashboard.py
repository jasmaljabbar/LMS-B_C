# backend/routes/parent_dashboard.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
# --- CORRECTED IMPORT ---
from sqlalchemy.orm import Session, joinedload, selectinload, contains_eager, aliased # Added selectinload here
# --- END CORRECTION ---
from sqlalchemy import func, case, cast, Date, Integer, distinct, desc, and_, or_
from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta, date

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/dashboard/parent",
    tags=["Parent Dashboard"],
    dependencies=[Depends(get_current_user)] # Apply auth to all endpoints here
)

# --- Helper: Get Parent ID ---
def _get_parent_id_from_user(current_user: models.User, db: Session) -> int:
    """Gets the parent ID associated with the logged-in user."""
    if current_user.user_type != "Parent":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to parents."
        )
    parent = db.query(models.Parent.id).filter(models.Parent.user_id == current_user.id).first()
    if not parent:
        logger.error(f"No parent profile found for user_id {current_user.id} ('{current_user.username}')")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent profile not found for the logged-in user."
        )
    return parent.id

# --- Helper: Get Child IDs for Parent ---
def _get_child_ids_for_parent(parent_id: int, db: Session) -> List[int]:
    """Gets a list of student IDs associated with the parent."""
    # Use selectinload for efficient loading of the many-to-many 'children' relationship
    parent = db.query(models.Parent).options(
        selectinload(models.Parent.children)
    ).filter(models.Parent.id == parent_id).first()

    if not parent:
        # This case should ideally not happen if parent_id came from _get_parent_id_from_user
        logger.error(f"Parent with ID {parent_id} not found when fetching children.")
        return []
    return [child.id for child in parent.children]

# --- Helper: Verify Parent Access to Child ---
def _verify_parent_access_to_child(parent_id: int, student_id: int, db: Session):
    """Checks if the parent is linked to the specified student."""
    # Query the association table directly or check the relationship
    # Checking the relationship might be slightly less efficient if not loaded,
    # but querying the association table is explicit and clear.
    is_linked = db.query(models.parent_student_association).filter(
        models.parent_student_association.c.parent_id == parent_id,
        models.parent_student_association.c.student_id == student_id
    ).first()

    if not is_linked:
        logger.warning(f"Parent ID {parent_id} attempted to access data for unauthorized student ID {student_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this student's data."
        )

# --- Helper: Get Child's Current Grade/Section ---
def _get_child_grade_section(student_id: int, db: Session) -> Optional[tuple[int, str, int, str]]:
    """Gets the current grade ID/Name and section ID/Name for a student."""
    current_year = datetime.now().year
    student_year_info = db.query(models.StudentYear).options(
        # Eager load necessary relationships for accessing names
        joinedload(models.StudentYear.section).joinedload(models.Section.grade)
    ).filter(
        models.StudentYear.studentId == student_id,
        models.StudentYear.year == current_year
    ).first() # Assuming only one entry per year

    if student_year_info and student_year_info.section and student_year_info.section.grade:
        return (
            student_year_info.section.grade.id,
            student_year_info.section.grade.name,
            student_year_info.section.id,
            student_year_info.section.name
        )
    logger.warning(f"Could not determine current grade/section for student_id {student_id} in year {current_year}")
    return None


# --- API Endpoints ---

@router.get("/children", response_model=List[schemas.ParentChildInfo])
def get_parent_children(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Lists the children associated with the logged-in parent."""
    parent_id = _get_parent_id_from_user(current_user, db)

    # Fetch children with necessary details using the relationship
    parent = db.query(models.Parent).options(
        selectinload(models.Parent.children).joinedload(models.Student.user) # Load children and their user details efficiently
    ).filter(models.Parent.id == parent_id).first()

    if not parent:
        # This case should ideally not happen if parent_id is valid
        logger.error(f"Parent {parent_id} somehow not found after ID check.")
        return []

    children_info: List[schemas.ParentChildInfo] = []
    # Fetch grade/section info efficiently if possible, or loop as before
    # For simplicity, looping for grade/section info here:
    for child in parent.children:
        if not child.user: # Skip if user data is missing
            logger.warning(f"Child student {child.id} linked to parent {parent_id} is missing user data.")
            continue
        grade_info = _get_child_grade_section(child.id, db)
        children_info.append(schemas.ParentChildInfo(
            student_id=child.id,
            student_name=child.name,
            user_photo=child.user.photo,
            grade_name=grade_info[1] if grade_info else None,
            section_name=grade_info[3] if grade_info else None
        ))
    return children_info


@router.get("/subject-performance/{student_id}", response_model=List[schemas.ParentSubjectPerformance])
def get_child_subject_performance(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Gets the average score per subject for the specified child."""
    parent_id = _get_parent_id_from_user(current_user, db)
    _verify_parent_access_to_child(parent_id, student_id, db) # Authorize access

    # Get child's grade ID
    grade_section_info = _get_child_grade_section(student_id, db)
    if not grade_section_info:
        logger.warning(f"Cannot fetch subject performance for student {student_id} as grade is unknown.")
        return []
    grade_id = grade_section_info[0]

    # Get subjects for that grade
    subjects_query = db.query(models.Subject.id, models.Subject.name).filter(
        models.Subject.grade_id == grade_id
    ).order_by(models.Subject.name)
    subjects = subjects_query.all()

    if not subjects:
        logger.warning(f"No subjects found for grade {grade_id}.")
        return []

    subject_map = {s.id: s.name for s in subjects}
    subject_ids = list(subject_map.keys())

    # Fetch average scores for this student per subject
    avg_scores_query = db.query(
        models.Assessment.subject_id,
        func.avg(
            case((models.StudentAssessmentScore.max_score > 0, (models.StudentAssessmentScore.score_achieved / models.StudentAssessmentScore.max_score) * 100), else_=0)
        ).label("avg_score_percent")
    ).join(
        models.StudentAssessmentScore, models.Assessment.id == models.StudentAssessmentScore.assessment_id
    ).filter(
        models.StudentAssessmentScore.student_id == student_id,
        models.Assessment.subject_id.in_(subject_ids) # Filter assessments by subjects in the student's grade
    ).group_by(
        models.Assessment.subject_id
    )
    avg_scores = avg_scores_query.all()
    score_map = {score.subject_id: round(score.avg_score_percent, 2) if score.avg_score_percent is not None else None for score in avg_scores}

    # Build response
    performance_list: List[schemas.ParentSubjectPerformance] = []
    for subj_id, subj_name in subject_map.items():
        performance_list.append(schemas.ParentSubjectPerformance(
            subject_id=subj_id,
            subject_name=subj_name,
            average_score=score_map.get(subj_id)
        ))
    return performance_list


@router.get("/assessments/{student_id}", response_model=List[schemas.ParentAssessmentStatus])
def get_child_assessment_status(
    student_id: int,
    status_filter: Optional[str] = Query(None, description="Filter by status: Upcoming, Completed, Pending"),
    limit: int = Query(10, ge=1, le=50), # Limit results
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Gets the status of assessments (Upcoming, Completed, Pending) for the specified child."""
    parent_id = _get_parent_id_from_user(current_user, db)
    _verify_parent_access_to_child(parent_id, student_id, db) # Authorize access

    # Get child's grade ID to filter relevant assessments
    grade_section_info = _get_child_grade_section(student_id, db)
    if not grade_section_info:
        logger.warning(f"Cannot fetch assessments for student {student_id} as grade is unknown.")
        return []
    grade_id = grade_section_info[0]

    now = datetime.utcnow() # Use UTC for comparisons

    # Alias StudentAssessmentScore to allow outer join filtering
    ScoreAlias = aliased(models.StudentAssessmentScore)

    # Base query for assessments linked to the student's grade via subject
    assessments_query = db.query(
        models.Assessment.id.label("assessment_id"),
        models.Assessment.name.label("assessment_name"),
        models.Assessment.due_date,
        models.Subject.name.label("subject_name"),
        ScoreAlias.score_achieved,
        ScoreAlias.max_score
        # We need the status logic added as a column
    ).select_from(models.Assessment).join(
        models.Subject, models.Assessment.subject_id == models.Subject.id
    ).outerjoin( # Use outer join to include assessments the student hasn't taken yet
        ScoreAlias,
        and_(
            models.Assessment.id == ScoreAlias.assessment_id,
            ScoreAlias.student_id == student_id # Filter scores for the specific student
        )
    ).filter(
        models.Subject.grade_id == grade_id # Filter assessments relevant to the student's grade
    )

    # Determine status based on score existence and due date
    status_logic = case(
        (ScoreAlias.id != None, schemas.AssessmentStatusEnum.COMPLETED),
        (and_(ScoreAlias.id == None, or_(models.Assessment.due_date == None, models.Assessment.due_date > now)), schemas.AssessmentStatusEnum.UPCOMING),
        (and_(ScoreAlias.id == None, models.Assessment.due_date != None, models.Assessment.due_date <= now), schemas.AssessmentStatusEnum.PENDING),
        else_=schemas.AssessmentStatusEnum.PENDING # Default fallback if needed
    ).label("status")

    # Add the status logic column to the query
    assessments_query = assessments_query.add_columns(status_logic)

    # Apply status filter if provided
    if status_filter:
        try:
            filter_enum = schemas.AssessmentStatusEnum(status_filter)
            # Filter on the calculated status_logic column
            assessments_query = assessments_query.filter(status_logic == filter_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status filter. Use one of: {', '.join([s.value for s in schemas.AssessmentStatusEnum])}")

    # --- CORRECTED ORDER BY for MySQL/MariaDB ---
    # Ordering: prioritize Upcoming by due date, then Pending by due date, then Completed
    assessments_query = assessments_query.order_by(
        case( # Order by status enum value
            (status_logic == schemas.AssessmentStatusEnum.UPCOMING, 1),
            (status_logic == schemas.AssessmentStatusEnum.PENDING, 2),
            (status_logic == schemas.AssessmentStatusEnum.COMPLETED, 3),
            else_=4
        ),
        # Replace .asc().nullsfirst() with MySQL/MariaDB compatible syntax
        models.Assessment.due_date.is_(None).desc(), # NULLs first
        models.Assessment.due_date.asc(),            # Then ascending date
        # Assuming default NULLS LAST for DESC is acceptable for attempt_timestamp
        desc(ScoreAlias.attempt_timestamp)
    ).limit(limit)
    # --- END CORRECTION ---

    results = assessments_query.all()

    # Map to schema
    return [
        schemas.ParentAssessmentStatus(
            assessment_id=row.assessment_id,
            assessment_name=row.assessment_name,
            subject_name=row.subject_name,
            status=row.status, # Status comes directly from the query result now
            due_date=row.due_date,
            score_achieved=row.score_achieved,
            max_score=row.max_score
        ) for row in results
    ]

@router.get("/timetable/{student_id}", response_model=List[schemas.ParentTimetableEntry])
def get_child_timetable(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Gets the weekly timetable for the specified child's section.
    NOTE: Requires the 'timetables' table to be populated with data.
    """
    parent_id = _get_parent_id_from_user(current_user, db)
    _verify_parent_access_to_child(parent_id, student_id, db) # Authorize access

    # Get child's section ID
    grade_section_info = _get_child_grade_section(student_id, db)
    if not grade_section_info:
        logger.warning(f"Cannot fetch timetable for student {student_id} as section is unknown.")
        return []
    section_id = grade_section_info[2]

    # Query the timetable table for the specific section
    timetable_entries = db.query(
        models.Timetable.day_of_week,
        models.Timetable.start_time,
        models.Timetable.end_time,
        models.Subject.name.label("subject_name"),
        models.Teacher.name.label("teacher_name")
    ).select_from(models.Timetable).join(
        models.Subject, models.Timetable.subject_id == models.Subject.id
    ).outerjoin( # Outer join in case teacher is not assigned or deleted
        models.Teacher, models.Timetable.teacher_id == models.Teacher.id
    ).filter(
        models.Timetable.section_id == section_id
    ).order_by(
        models.Timetable.day_of_week,
        models.Timetable.start_time
    ).all()

    if not timetable_entries:
         logger.info(f"No timetable entries found for section ID {section_id}.")
         # Optionally return a default structure or message
         return []

    # Map to schema using from_orm
    return [schemas.ParentTimetableEntry.from_orm(entry) for entry in timetable_entries]
