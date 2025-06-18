# backend/routes/assignment_distributions.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.logger_utils import log_activity
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/assignment-distributions",
    tags=["Assignment Distributions"]
)

# --- Helper to check if student belongs to section for the current year ---
def _get_students_in_section_map(section_id: int, db: Session) -> dict[int, models.Student]:
    """Gets a dict of student_id: Student object for students currently in the section."""
    current_year = datetime.now().year
    students_in_section = db.query(models.Student).join(
        models.StudentYear, models.Student.id == models.StudentYear.studentId
    ).filter(
        models.StudentYear.sectionId == section_id,
        models.StudentYear.year == current_year
    ).all()
    return {student.id: student for student in students_in_section}


# --- API Endpoints ---

@router.post("/", response_model=schemas.AssignmentDistributionInfo, status_code=status.HTTP_201_CREATED)
def create_assignment_distribution(
    distribution_data: schemas.AssignmentDistributionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Distributes an assessment to a section.
    Can target all students in the section or a specific list of students.
    Requires Teacher or Admin role.
    """
    if current_user.user_type not in ["Teacher", "Admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Teachers or Admins can distribute assignments.")

    # --- Validate Foreign Keys ---
    assessment = db.query(models.Assessment).filter(models.Assessment.id == distribution_data.assessment_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail=f"Assessment with ID {distribution_data.assessment_id} not found.")

    section = db.query(models.Section).options(joinedload(models.Section.grade)).filter(models.Section.id == distribution_data.section_id).first() # Load grade for check
    if not section:
        raise HTTPException(status_code=404, detail=f"Section with ID {distribution_data.section_id} not found.")

    # --- Validate Grade Compatibility (Optional but recommended) ---
    # Ensure the assessment's subject belongs to the same grade as the target section
    if assessment.subject_id:
         subject = db.query(models.Subject).filter(models.Subject.id == assessment.subject_id).first()
         if subject and section.grade and subject.grade_id != section.grade_id:
             raise HTTPException(
                 status_code=400,
                 detail=f"Assessment (Subject Grade: {subject.grade_id}) cannot be assigned to Section '{section.name}' (Grade: {section.grade_id}). Grade mismatch."
             )

    # --- Validate Specific Students (if applicable) ---
    students_to_assign = []
    if not distribution_data.assign_to_all_students:
        if not distribution_data.student_ids:
            # Schema validation should catch this, but double-check
            raise HTTPException(status_code=400, detail="student_ids must be provided when assign_to_all_students is False.")

        # Fetch students actually in the target section for the current year
        students_in_section_map = _get_students_in_section_map(distribution_data.section_id, db)
        valid_student_ids_in_section = set(students_in_section_map.keys())

        target_student_ids = set(distribution_data.student_ids)
        invalid_ids = target_student_ids - valid_student_ids_in_section

        if invalid_ids:
            # Fetch names of missing students for a clearer error message
            missing_students_query = db.query(models.Student.name).filter(models.Student.id.in_(invalid_ids)).all()
            missing_names = [s.name for s in missing_students_query]
            raise HTTPException(
                status_code=400,
                detail=(f"Students with IDs {invalid_ids} (Names: {missing_names}) were not found or "
                        f"do not belong to Section '{section.name}' (ID: {distribution_data.section_id}) for the current year.")
            )

        # Get the actual Student objects for valid IDs
        students_to_assign = [students_in_section_map[sid] for sid in target_student_ids if sid in students_in_section_map] # Ensure key exists
        if not students_to_assign:
             raise HTTPException(status_code=400, detail="No valid students provided for specific assignment.")


    # --- Create Distribution Record ---
    db_distribution = models.AssignmentDistribution(
        assessment_id=distribution_data.assessment_id,
        section_id=distribution_data.section_id,
        assigned_by_user_id=current_user.id,
        assign_to_all_students=distribution_data.assign_to_all_students,
    )

    # Link specific students if needed
    if not distribution_data.assign_to_all_students:
        db_distribution.specific_students.extend(students_to_assign)

    try:
        db.add(db_distribution)
        db.commit()
        db.refresh(db_distribution)
        # Eager load necessary fields for the response
        db.refresh(db_distribution, attribute_names=['assessment', 'section', 'assigned_by_user', 'specific_students'])
        # Load student names for the specific_students in the response object if not assign_to_all
        if not db_distribution.assign_to_all_students:
             for student in db_distribution.specific_students:
                 db.refresh(student) # Load student.name

        log_activity(
            db=db, user_id=current_user.id, action='ASSIGNMENT_DISTRIBUTED',
            details=(f"User '{current_user.username}' distributed Assessment '{assessment.name}' (ID: {assessment.id}) "
                     f"to Section '{section.name}' (ID: {section.id}). "
                     f"Target: {'All Students' if db_distribution.assign_to_all_students else f'Specific Students ({len(students_to_assign)})'}."),
            target_entity='AssignmentDistribution', target_entity_id=db_distribution.id,
        )
        return db_distribution

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error distributing assignment: {e}", exc_info=True)
        # Handle potential unique constraint if added later
        # if "uq_assessment_distribution_section" in str(e.orig): ...
        raise HTTPException(status_code=400, detail="Database constraint violation during distribution.")
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error distributing assignment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred during distribution.")


@router.get("/", response_model=List[schemas.AssignmentDistributionInfo])
def read_assignment_distributions(
    assessment_id: Optional[int] = Query(None),
    section_id: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves a list of assignment distributions, optionally filtered."""
    # Add role checks if needed (e.g., Admin sees all, Teacher sees their assignments?)
    query = db.query(models.AssignmentDistribution).options(
        joinedload(models.AssignmentDistribution.assessment),
        joinedload(models.AssignmentDistribution.section),
        joinedload(models.AssignmentDistribution.assigned_by_user).load_only(models.User.id, models.User.username), # Load ID and username
        selectinload(models.AssignmentDistribution.specific_students) # Eager load students if specific
        # Removed nested user/photo loading here for performance, can add back if needed for specific student details display
        #.joinedload(models.Student.user).load_only(models.User.photo)
    )

    if assessment_id:
        query = query.filter(models.AssignmentDistribution.assessment_id == assessment_id)
    if section_id:
        query = query.filter(models.AssignmentDistribution.section_id == section_id)
    # Add filter by assigned_by_user_id if needed

    distributions = query.order_by(models.AssignmentDistribution.assigned_at.desc()).offset(skip).limit(limit).all()

    # Manually refresh student names if needed (since not loading full user)
    # Pydantic mapping relies on the ORM object having the `name` attribute loaded
    for dist in distributions:
        if not dist.assign_to_all_students:
            for student in dist.specific_students:
                db.refresh(student, attribute_names=['name']) # Ensure name is loaded

    return distributions


@router.get("/{distribution_id}", response_model=schemas.AssignmentDistributionInfo)
def read_assignment_distribution(
    distribution_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves a specific assignment distribution by its ID."""
    # Add role checks if needed
    distribution = db.query(models.AssignmentDistribution).options(
        joinedload(models.AssignmentDistribution.assessment),
        joinedload(models.AssignmentDistribution.section),
        joinedload(models.AssignmentDistribution.assigned_by_user).load_only(models.User.id, models.User.username),
        selectinload(models.AssignmentDistribution.specific_students) # Load students
        #.joinedload(models.Student.user).load_only(models.User.photo) # Remove nested photo for now
    ).filter(models.AssignmentDistribution.id == distribution_id).first()

    if not distribution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment distribution not found.")

    # Manually refresh student names if needed
    if not distribution.assign_to_all_students:
        for student in distribution.specific_students:
            db.refresh(student, attribute_names=['name'])

    return distribution


@router.delete("/{distribution_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment_distribution(
    distribution_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Deletes an assignment distribution.
    This removes the record of assignment but does NOT delete the assessment content
    or student scores (if any were submitted).
    Requires Teacher or Admin role (or creator).
    """
    # Fetch with creator info for authorization check
    db_distribution = db.query(models.AssignmentDistribution).options(
        joinedload(models.AssignmentDistribution.assessment), # Load assessment for logging
        joinedload(models.AssignmentDistribution.section)    # Load section for logging
    ).filter(models.AssignmentDistribution.id == distribution_id).first()

    if not db_distribution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment distribution not found.")

    # Authorization Check
    is_admin = current_user.user_type == "Admin"
    is_creator = db_distribution.assigned_by_user_id == current_user.id
    if not (is_admin or is_creator):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this distribution.")

    # Store details for logging before deletion
    assessment_name = db_distribution.assessment.name if db_distribution.assessment else "N/A"
    section_name = db_distribution.section.name if db_distribution.section else "N/A"

    try:
        # Deleting the distribution will cascade delete entries in
        # assignment_distribution_students due to `ondelete='CASCADE'` on the FK.
        db.delete(db_distribution)
        db.commit()

        log_activity(
            db=db, user_id=current_user.id, action='ASSIGNMENT_DISTRIBUTION_DELETED',
            details=(f"User '{current_user.username}' deleted distribution (ID: {distribution_id}) of "
                     f"Assessment '{assessment_name}' to Section '{section_name}'."),
            target_entity='AssignmentDistribution', target_entity_id=distribution_id,
        )
        return None

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting assignment distribution {distribution_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to delete assignment distribution.")

