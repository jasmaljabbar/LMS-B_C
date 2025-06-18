# backend/routes/student_years.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user # Keep this to ensure user is logged in

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/studentyears", tags=["studentyears"])


@router.post("/", response_model=schemas.StudentYearCreate, status_code=status.HTTP_201_CREATED)
def create_student_year(
    student_year: schemas.StudentYearCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Requires login
):
    """Creates a new student year (requires authentication, ANY user type allowed)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     logger.warning(f"User {current_user.username} ({current_user.user_type}) attempted to create student year - FORBIDDEN.")
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    # Add checks for studentId and sectionId existence before creation
    student_exists = db.query(models.Student.id).filter(models.Student.id == student_year.studentId).first()
    if not student_exists:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Student with ID {student_year.studentId} not found.")
    section_exists = db.query(models.Section.id).filter(models.Section.id == student_year.sectionId).first()
    if not section_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Section with ID {student_year.sectionId} not found.")


    db_student_year = models.StudentYear(**student_year.dict())
    try:
        db.add(db_student_year)
        db.commit()
        db.refresh(db_student_year)
        logger.info(f"User {current_user.username} created student year record for Student ID {student_year.studentId}, Year {student_year.year}")
        return schemas.StudentYearCreate.from_orm(db_student_year)
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating student year record: {e}", exc_info=True)
        # Check for unique constraint violation (studentId, year)
        if "Duplicate entry" in str(e.orig): # Check specific DB error message
             raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Student year record already exists for Student ID {student_year.studentId} and Year {student_year.year}."
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create student year record: {str(e)}")


@router.get("/{student_id}/{year}", response_model=schemas.StudentYearCreate)
def read_student_year(
    student_id: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Requires login
):
    """Retrieves a student year by Student ID and Year (requires authentication, ANY user type allowed)."""
    # --- AUTHORIZATION REMOVED ---
    # is_authorized = False
    # if current_user.user_type == "Admin":
    #     is_authorized = True
    # elif current_user.user_type == "Student":
    #     # Check if the current student user is requesting their own record
    #     student_profile = db.query(models.Student.id).filter(models.Student.user_id == current_user.id).first()
    #     if student_profile and student_profile.id == student_id:
    #         is_authorized = True
    #
    # if not is_authorized:
    #     logger.warning(f"User {current_user.username} ({current_user.user_type}) attempted to access student year record for Student ID {student_id} - FORBIDDEN.")
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this student year record.")
    # --- END REMOVAL ---

    db_student_year = (
        db.query(models.StudentYear)
        .filter(models.StudentYear.studentId == student_id, models.StudentYear.year == year)
        .first()
    )
    if db_student_year is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student year record not found for the specified student and year."
        )
    return schemas.StudentYearCreate.from_orm(db_student_year)


@router.get("/", response_model=List[schemas.StudentYearCreate])
def read_student_years(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Requires login
):
    """Retrieves all student years (Requires authentication, ANY user type allowed)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     logger.warning(f"User {current_user.username} ({current_user.user_type}) attempted to list all student years - FORBIDDEN.")
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_student_years = db.query(models.StudentYear).offset(skip).limit(limit).all()
    return [schemas.StudentYearCreate.from_orm(sy) for sy in db_student_years]


@router.put("/{student_id}/{year}", response_model=schemas.StudentYearCreate)
def update_student_year(
    student_id: int,
    year: int,
    student_year: schemas.StudentYearCreate, # Should contain new sectionId
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Requires login
):
    """Updates a student year record (Requires authentication, ANY user type allowed)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #      logger.warning(f"User {current_user.username} ({current_user.user_type}) attempted to update student year record for Student ID {student_id} - FORBIDDEN.")
    #      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    # Check if the target student year record exists
    db_student_year = (
        db.query(models.StudentYear)
        .filter(models.StudentYear.studentId == student_id, models.StudentYear.year == year)
        .first()
    )
    if db_student_year is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student year record not found for update."
        )

    # Validate the new sectionId exists
    section_exists = db.query(models.Section.id).filter(models.Section.id == student_year.sectionId).first()
    if not section_exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Section with ID {student_year.sectionId} not found.")

    # Update the sectionId
    db_student_year.sectionId = student_year.sectionId
    try:
        db.commit()
        db.refresh(db_student_year)
        logger.info(f"User {current_user.username} updated student year record for Student ID {student_id}, Year {year}. New Section ID: {student_year.sectionId}")
        return schemas.StudentYearCreate.from_orm(db_student_year)
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating student year record: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update student year record: {str(e)}")


@router.delete("/{student_id}/{year}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student_year(
    student_id: int,
    year: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Requires login
):
    """Deletes a student year record (Requires authentication, ANY user type allowed)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     logger.warning(f"User {current_user.username} ({current_user.user_type}) attempted to delete student year record for Student ID {student_id} - FORBIDDEN.")
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_student_year = (
        db.query(models.StudentYear)
        .filter(models.StudentYear.studentId == student_id, models.StudentYear.year == year)
        .first()
    )
    if db_student_year is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student year record not found for deletion."
        )

    try:
        db.delete(db_student_year)
        db.commit()
        logger.info(f"User {current_user.username} deleted student year record for Student ID {student_id}, Year {year}")
        return None # Important: Return None for 204 status
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting student year record: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete student year record.")
