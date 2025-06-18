# backend/routes/terms.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from sqlalchemy.exc import IntegrityError, NoResultFound

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user # Keep authentication

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/terms", tags=["Terms"])

# --- Helper Function to Validate Grade Existence ---
def _get_grade(grade_id: int, db: Session):
    grade = db.query(models.Grade).filter(models.Grade.id == grade_id).first()
    if not grade:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Grade with id {grade_id} not found."
        )
    return grade

# --- Helper Function to Validate Term Existence ---
def _get_term(term_id: int, db: Session):
    term = db.query(models.Term).filter(models.Term.id == term_id).first()
    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Term with id {term_id} not found."
        )
    return term

@router.post("/", response_model=schemas.TermInfo, status_code=status.HTTP_201_CREATED)
def create_term(
    term_data: schemas.TermCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Creates a new academic term for a specific grade and year."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     logger.warning(f"User '{current_user.username}' not authorized to create terms.")
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    # Validate grade exists
    _get_grade(term_data.grade_id, db)

    db_term = models.Term(**term_data.dict())

    try:
        db.add(db_term)
        db.commit()
        db.refresh(db_term)
        logger.info(f"Created Term '{db_term.name}' (ID: {db_term.id}) for Grade {db_term.grade_id}, Year {db_term.year} by user {current_user.username}")
        return db_term
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating term: {e}", exc_info=True)
        if "uq_term_name_year_grade" in str(e.orig):
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A term with name '{term_data.name}' already exists for grade {term_data.grade_id} in year {term_data.year}."
            )
        # Grade FK check redundant due to _get_grade
        elif "FOREIGN KEY (`grade_id`)" in str(e.orig):
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid grade_id ({term_data.grade_id}). Grade does not exist.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error during term creation."
            )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating term: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create term")


@router.get("/{term_id}", response_model=schemas.TermInfo)
def read_term(
    term_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves a specific term by its ID."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type not in ["Admin", "Teacher", "Student", "Parent"]:
    #      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_term = _get_term(term_id, db) # Use helper
    return db_term


@router.get("/", response_model=List[schemas.TermInfo])
def read_terms(
    grade_id: Optional[int] = None,
    year: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves a list of terms, optionally filtered by grade and/or year."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type not in ["Admin", "Teacher", "Student", "Parent"]:
    #      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    query = db.query(models.Term)
    if grade_id:
        query = query.filter(models.Term.grade_id == grade_id)
    if year:
        query = query.filter(models.Term.year == year)

    terms = query.order_by(models.Term.year, models.Term.grade_id, models.Term.name).offset(skip).limit(limit).all()
    return terms


@router.put("/{term_id}", response_model=schemas.TermInfo)
def update_term(
    term_id: int,
    term_update_data: schemas.TermUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Updates an existing term."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     logger.warning(f"User '{current_user.username}' not authorized to update term {term_id}.")
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_term = _get_term(term_id, db) # Fetch existing term

    # Validate the new grade_id exists if it's being changed and is provided
    if term_update_data.grade_id is not None and term_update_data.grade_id != db_term.grade_id:
        _get_grade(term_update_data.grade_id, db)

    # Update fields from the request data (only those provided)
    update_data = term_update_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_term, key, value)

    try:
        db.commit()
        db.refresh(db_term)
        logger.info(f"Updated Term ID {term_id} by user {current_user.username}")
        return db_term
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error updating term {term_id}: {e}", exc_info=True)
        # Use the potentially updated values for the error message if available
        name = term_update_data.name if 'name' in update_data else db_term.name
        grade_id = term_update_data.grade_id if 'grade_id' in update_data else db_term.grade_id
        year = term_update_data.year if 'year' in update_data else db_term.year

        if "uq_term_name_year_grade" in str(e.orig):
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A term with name '{name}' already exists for grade {grade_id} in year {year}."
            )
        # Grade FK check redundant
        elif "FOREIGN KEY (`grade_id`)" in str(e.orig):
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid grade_id ({grade_id}). Grade does not exist.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database error during term update."
            )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating term {term_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update term")


@router.delete("/{term_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_term(
    term_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Deletes a term. WARNING: This may fail if lessons or scores are linked."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     logger.warning(f"User '{current_user.username}' not authorized to delete term {term_id}.")
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_term = _get_term(term_id, db)

    # Check for dependencies if cascade delete isn't reliable/desired
    has_lessons = db.query(models.Lesson.id).filter(models.Lesson.term_id == term_id).limit(1).first()
    has_scores = db.query(models.StudentAssessmentScore.id).filter(models.StudentAssessmentScore.term_id == term_id).limit(1).first()

    if has_lessons or has_scores:
        dependencies = []
        if has_lessons: dependencies.append("lessons")
        if has_scores: dependencies.append("assessment scores")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete term {term_id} because it has associated {', '.join(dependencies)}."
        )

    try:
        db.delete(db_term)
        db.commit()
        logger.info(f"Deleted Term ID {term_id} by user {current_user.username}")
        return None
    except IntegrityError as e: # Catch FK errors if check above failed or ON DELETE RESTRICT is used
        db.rollback()
        logger.error(f"Integrity error deleting term {term_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete term {term_id}. It might be referenced by lessons or scores."
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error deleting term {term_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete term")

