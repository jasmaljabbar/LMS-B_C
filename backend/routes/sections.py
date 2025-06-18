# backend/routes/sections.py
# --- Add necessary imports ---
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload # Import selectinload
from typing import List, Optional
from sqlalchemy import func # Import func

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user # Keep authentication

logger = logging.getLogger(__name__) # Get logger
router = APIRouter(prefix="/sections", tags=["sections"])


@router.post("/", response_model=schemas.SectionCreate, status_code=status.HTTP_201_CREATED)
def create_section(
    section: schemas.SectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Creates a new section (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    # Check if grade exists
    grade_exists = db.query(models.Grade.id).filter(models.Grade.id == section.grade_id).first()
    if not grade_exists:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Grade with ID {section.grade_id} not found.")

    db_section = models.Section(**section.dict())
    db.add(db_section)
    db.commit()
    db.refresh(db_section)
    # Return the input data as per response_model
    return section # Pydantic will validate this matches SectionCreate


@router.get("/{section_id}", response_model=schemas.SectionInfo)
def read_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves a section by ID (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_section = db.query(models.Section).filter(models.Section.id == section_id).first()
    if db_section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    # Map manually or rely on from_orm if config is set in schema
    return db_section # Pydantic v2+ can handle this if schema uses ConfigDict(from_attributes=True)
    # return schemas.SectionInfo(id=db_section.id, name=db_section.name, grade_id=db_section.grade_id)


@router.get("/", response_model=List[schemas.SectionInfo])
def read_sections(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves all sections (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_sections = db.query(models.Section).offset(skip).limit(limit).all()
    # Map manually or rely on from_orm
    return db_sections # Pydantic v2+ can handle list of ORM objects
    # return [schemas.SectionInfo(id=section.id, name=section.name, grade_id=section.grade_id) for section in db_sections]

@router.get("/grade/{grade_id}", response_model=List[schemas.SectionInfo])
def read_sections_by_grade(
    grade_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
    skip: int = 0,
    limit: int = 100,
):
    """Retrieves all sections for a specific grade (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    # Check if grade exists
    grade_exists = db.query(models.Grade.id).filter(models.Grade.id == grade_id).first()
    if not grade_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Grade with ID {grade_id} not found.")

    db_sections = db.query(models.Section).filter(models.Section.grade_id == grade_id).offset(skip).limit(limit).all()
    # Map manually or rely on from_orm
    return db_sections # Pydantic v2+ can handle list of ORM objects
    # return [schemas.SectionInfo(id=section.id, name=section.name, grade_id=section.grade_id) for section in db_sections]


# --- NEW ENDPOINT: Get Students by Section ---
@router.get(
    "/{section_id}/students",
    response_model=List[schemas.StudentDetails],
    summary="Get Students by Section",
    description="Retrieves details for all students currently assigned to the specified section for the current year."
)
def read_students_by_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """
    Retrieves full details for all students assigned to the given section
    for the current academic year.
    """
    # 1. Verify Section exists
    db_section = db.query(models.Section).options(
        joinedload(models.Section.grade) # Load grade info for the response schema
    ).filter(models.Section.id == section_id).first()
    if not db_section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Section with ID {section_id} not found.")

    # 2. Find students in this section for the current year
    current_year = datetime.now().year
    student_year_records = db.query(models.StudentYear).filter(
        models.StudentYear.sectionId == section_id,
        models.StudentYear.year == current_year
    ).all()

    if not student_year_records:
        logger.info(f"No students found in section {section_id} for year {current_year}.")
        return [] # Return empty list if no students are assigned

    student_ids = [sy.studentId for sy in student_year_records]

    # 3. Fetch Student details including User info
    # We need the specific section info for StudentDetails, which we already have (db_section)
    # So we query Students, join User, and construct the response manually or ensure pydantic maps correctly
    db_students = db.query(models.Student).options(
        joinedload(models.Student.user) # Eager load user details
    ).filter(
        models.Student.id.in_(student_ids)
    ).order_by(models.Student.name).all() # Order by name

    # 4. Construct the response using StudentDetails schema
    student_details_list = []
    for db_student in db_students:
        if not db_student.user:
            logger.warning(f"Skipping student {db_student.id} in section {section_id} due to missing user data.")
            continue

        # Construct the StudentDetails object
        student_details_list.append(schemas.StudentDetails(
            id=db_student.id,
            name=db_student.name,
            user=db_student.user, # Pass the loaded User object
            section=db_section,    # Pass the loaded Section object (contains Grade)
            year=current_year      # Use the current year we filtered by
        ))

    logger.info(f"Retrieved {len(student_details_list)} student details for section {section_id}, year {current_year}.")
    return student_details_list
# --- END NEW ENDPOINT ---


@router.put("/{section_id}", response_model=schemas.SectionCreate)
def update_section(
    section_id: int,
    section: schemas.SectionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Updates a section by ID (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_section = db.query(models.Section).filter(models.Section.id == section_id).first()
    if db_section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    # Check if new grade_id exists
    if section.grade_id != db_section.grade_id:
         grade_exists = db.query(models.Grade.id).filter(models.Grade.id == section.grade_id).first()
         if not grade_exists:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Grade with ID {section.grade_id} not found.")

    db_section.name = section.name
    db_section.grade_id = section.grade_id
    db.commit()
    db.refresh(db_section)
    # Return the input data as per response_model
    return section # Pydantic will validate this matches SectionCreate


@router.delete("/{section_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_section(
    section_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Deletes a section by ID (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_section = db.query(models.Section).filter(models.Section.id == section_id).first()
    if db_section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    # Check for dependencies (StudentYear, Timetable) if cascade delete isn't reliable/desired
    # student_year_count = db.query(models.StudentYear).filter(...).count()
    # timetable_count = db.query(models.Timetable).filter(...).count()
    # if student_year_count > 0 or timetable_count > 0:
    #    raise HTTPException(status_code=409, detail="Cannot delete section with associated student assignments or timetable entries.")

    try:
        db.delete(db_section)
        db.commit()
        return None # Return None for 204
    except Exception as e: # Catch potential FK violations
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Cannot delete section. It might be referenced by other items (student assignments, timetable). Error: {e}")
