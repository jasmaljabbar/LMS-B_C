# backend/routes/subject.py
from fastapi import APIRouter, Depends, HTTPException, status
# --- Add joinedload ---
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional # Added Optional
from sqlalchemy.exc import IntegrityError
import logging # Added logging

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user # Keep authentication

# --- Get logger ---
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.post("/", response_model=schemas.SubjectInfo, status_code=status.HTTP_201_CREATED)
def create_subject(
    subject: schemas.SubjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Creates a new subject."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
    #     )
    # --- END REMOVAL ---

    # Check if grade exists
    grade_exists = db.query(models.Grade.id).filter(models.Grade.id == subject.grade_id).first()
    if not grade_exists:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Grade with ID {subject.grade_id} not found.")


    db_subject = models.Subject(**subject.dict())
    try:
        db.add(db_subject)
        db.commit()
        db.refresh(db_subject)
        return db_subject
    except IntegrityError as e:
        db.rollback()
        # This check is now redundant due to the explicit check above, but kept for safety
        if "FOREIGN KEY (`grade_id`)" in str(e.orig):
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid grade_id ({subject.grade_id}). Grade does not exist.",
            )
        else:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, # Or 500 for unexpected DB error
                detail="Failed to create subject due to database constraint.",
            )
    except Exception as e:
        db.rollback()
        # Log general errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")



@router.get("/{subject_id}", response_model=schemas.SubjectInfo)
def read_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves a subject by ID."""
    # No specific role check was present here
    db_subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if db_subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found"
        )
    return db_subject


@router.get("/", response_model=List[schemas.SubjectInfo])
def read_subjects(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves all subjects."""
    # No specific role check was present here
    db_subjects = db.query(models.Subject).offset(skip).limit(limit).all()
    return db_subjects

@router.get("/grade/{grade_id}", response_model=List[schemas.SubjectInfo])
def read_subjects_by_grade(
    grade_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves subjects by grade ID."""
    # No specific role check was present here
    # Check if grade exists first (optional but good practice)
    grade_exists = db.query(models.Grade.id).filter(models.Grade.id == grade_id).first()
    if not grade_exists:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Grade with id {grade_id} not found.")

    db_subjects = (
        db.query(models.Subject)
        .filter(models.Subject.grade_id == grade_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return db_subjects


# --- NEW ENDPOINT ---
@router.get(
    "/{subject_id}/grade-sections",
    response_model=schemas.SubjectGradeSectionDetails,
    summary="Get Grade and Sections for a Subject",
    description="Retrieves the grade details and all associated section details for a given subject ID."
)
def read_grade_and_sections_for_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """
    Retrieves the Grade and all Sections associated with the Grade
    linked to the specified Subject ID.
    """
    # No specific role check needed beyond authentication for this read operation

    # Fetch the subject and eagerly load its related grade
    db_subject = db.query(models.Subject).options(
        joinedload(models.Subject.grade) # Eager load the grade
    ).filter(models.Subject.id == subject_id).first()

    if db_subject is None:
        logger.warning(f"Subject with ID {subject_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subject with ID {subject_id} not found"
        )

    if db_subject.grade is None:
        # This case should ideally not happen if grade_id is non-nullable FK,
        # but good practice to check.
        logger.error(f"Subject {subject_id} found, but has no associated Grade.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grade associated with subject {subject_id} not found."
        )

    # Fetch all sections belonging to the subject's grade
    db_sections = db.query(models.Section).filter(
        models.Section.grade_id == db_subject.grade_id
    ).order_by(models.Section.name).all() # Order sections alphabetically

    # Pydantic's `from_orm` (or `from_attributes=True` in v2) will automatically map
    # db_subject.grade to schemas.GradeInfo and db_sections to List[schemas.SectionInfo]
    # when creating the SubjectGradeSectionDetails response.
    response_data = schemas.SubjectGradeSectionDetails(
        grade=db_subject.grade, # Pass the loaded Grade object
        sections=db_sections    # Pass the list of Section objects
    )

    logger.info(f"Successfully retrieved grade and section details for Subject ID {subject_id}.")
    return response_data
# --- END NEW ENDPOINT ---


@router.put("/{subject_id}", response_model=schemas.SubjectInfo)
def update_subject(
    subject_id: int,
    subject: schemas.SubjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Updates a subject by ID."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
    #     )
    # --- END REMOVAL ---

    db_subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if db_subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found"
        )

    # Check if new grade_id exists
    if subject.grade_id != db_subject.grade_id:
        grade_exists = db.query(models.Grade.id).filter(models.Grade.id == subject.grade_id).first()
        if not grade_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Grade with ID {subject.grade_id} not found.")

    # Update the subject attributes
    update_data = subject.dict()
    for key, value in update_data.items():
        setattr(db_subject, key, value)

    try:
        db.commit()
        db.refresh(db_subject)
        return db_subject
    except IntegrityError as e:
        db.rollback()
        # This check is now redundant
        if "FOREIGN KEY (`grade_id`)" in str(e.orig):
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid grade_id ({subject.grade_id}). Grade does not exist.",
            )
        else:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update subject due to database constraint.",
            )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Deletes a subject by ID."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
    #     )
    # --- END REMOVAL ---

    db_subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if db_subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found"
        )

    # Check for dependencies if cascade delete isn't reliable/desired
    has_lessons = db.query(models.Lesson.id).filter(models.Lesson.subject_id == subject_id).limit(1).first()
    has_assessments = db.query(models.Assessment.id).filter(models.Assessment.subject_id == subject_id).limit(1).first()
    has_timetable = db.query(models.Timetable.id).filter(models.Timetable.subject_id == subject_id).limit(1).first()
    # Add check for AssignmentSamples if its subject_id FK is RESTRICT/NO ACTION
    has_assignment_samples = db.query(models.AssignmentSample.id).filter(models.AssignmentSample.subject_id == subject_id).limit(1).first()
    # Add check for AssignmentFormat if its subject_id FK is RESTRICT/NO ACTION
    has_assignment_formats = db.query(models.AssignmentFormat.id).filter(models.AssignmentFormat.subject_id == subject_id).limit(1).first()


    if has_lessons or has_assessments or has_timetable or has_assignment_samples or has_assignment_formats:
        dependencies = []
        if has_lessons: dependencies.append("lessons")
        if has_assessments: dependencies.append("assessments")
        if has_timetable: dependencies.append("timetable entries")
        if has_assignment_samples: dependencies.append("assignment samples")
        if has_assignment_formats: dependencies.append("assignment formats")
        raise HTTPException(status_code=409, detail=f"Cannot delete subject with associated {', '.join(dependencies)}.")

    try:
        db.delete(db_subject)
        db.commit()
        return None # Return None for 204
    except IntegrityError as e: # Catch potential FK violations if check above missed something or cascade fails
         db.rollback()
         raise HTTPException(status_code=409, detail=f"Cannot delete subject. It might still be referenced by other items. Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
