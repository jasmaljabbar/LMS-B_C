# backend/routes/grades.py
# --- Add necessary imports ---
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload, selectinload, Query # Import Query for type hint
from typing import List, Optional, Dict # Import Dict
# --- Add 'and_' ---
from sqlalchemy import func, over, and_ # Import func, over, and_

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user # Keep authentication

logger = logging.getLogger(__name__) # Get logger
router = APIRouter(prefix="/grades", tags=["grades"])


@router.post("/", response_model=schemas.GradeCreate, status_code=status.HTTP_201_CREATED)
def create_grade(
    grade: schemas.GradeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Creates a new grade (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_grade = models.Grade(**grade.dict())
    db.add(db_grade)
    db.commit()
    db.refresh(db_grade)
    # Return input data as per response_model
    return grade


@router.get("/{grade_id}", response_model=schemas.GradeInfo)
def read_grade(
    grade_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves a grade by ID (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_grade = db.query(models.Grade).filter(models.Grade.id == grade_id).first()
    if db_grade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found")
    # Map manually or rely on from_orm
    return db_grade # Pydantic v2+ can handle this if schema configured
    # return schemas.GradeInfo(id=db_grade.id, name=db_grade.name)


@router.get("/", response_model=List[schemas.GradeInfo])
def read_grades(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves all grades (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_grades = db.query(models.Grade).offset(skip).limit(limit).all()
    # Map manually or rely on from_orm
    return db_grades # Pydantic v2+ can handle list of ORM objects
    # return [schemas.GradeInfo(id=grade.id, name=grade.name) for grade in db_grades]


# --- NEW ENDPOINT: Get Students by Grade ---
@router.get(
    "/{grade_id}/students",
    response_model=List[schemas.StudentDetails],
    summary="Get Students by Grade",
    description="Retrieves details for all students currently assigned to any section within the specified grade for the current year."
)
def read_students_by_grade(
    grade_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """
    Retrieves full details for all students assigned to any section
    within the given grade for the current academic year.
    """
    # 1. Verify Grade exists
    db_grade = db.query(models.Grade).filter(models.Grade.id == grade_id).first()
    if not db_grade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Grade with ID {grade_id} not found.")

    # 2. Find students in sections of this grade for the current year
    current_year = datetime.now().year

    # Get student IDs who were in this grade during the current year
    student_ids_query = db.query(models.StudentYear.studentId).join(
        models.Section, models.StudentYear.sectionId == models.Section.id
    ).filter(
        models.Section.grade_id == grade_id,
        models.StudentYear.year == current_year
    ).distinct()
    student_ids = [sid[0] for sid in student_ids_query.all()]

    if not student_ids:
        logger.info(f"No students found in grade {grade_id} for year {current_year}.")
        return []

    # Fetch the latest StudentYear record for each relevant student using a subquery
    # The subquery determines the latest year record for each student
    latest_year_subquery = db.query(
        models.StudentYear.studentId,
        func.max(models.StudentYear.year).label('latest_year')
    ).filter(
        models.StudentYear.studentId.in_(student_ids) # Only consider students potentially in the grade
    ).group_by(
        models.StudentYear.studentId
    ).subquery()

    # Query the actual StudentYear records that match the student ID and latest year,
    # And also ensure it belongs to the target grade.
    latest_student_years = db.query(models.StudentYear).join(
        latest_year_subquery,
        and_(
            models.StudentYear.studentId == latest_year_subquery.c.studentId,
            models.StudentYear.year == latest_year_subquery.c.latest_year
        )
    ).join( # Join section to filter by grade_id *again* to be certain
           # (This ensures the *latest* record is indeed in the target grade)
        models.Section, models.StudentYear.sectionId == models.Section.id
    ).filter(
        models.Section.grade_id == grade_id,
        models.StudentYear.year == current_year # Explicitly ensure it's the *current* year's record
    ).options(
        # Load section and grade associated with this specific StudentYear record
        joinedload(models.StudentYear.section).joinedload(models.Section.grade)
    ).all()


    # Create a map for quick lookup: student_id -> latest StudentYear object (for the current year in the target grade)
    student_year_map: Dict[int, models.StudentYear] = {sy.studentId: sy for sy in latest_student_years}

    # Fetch the student objects themselves, joining user info
    # Filter based on the keys found in the map (students who have a relevant current year record)
    relevant_student_ids = list(student_year_map.keys())
    if not relevant_student_ids:
         logger.info(f"No students found in grade {grade_id} with a record for the current year {current_year}.")
         return []

    db_students = db.query(models.Student).options(
        joinedload(models.Student.user) # Eager load user info
    ).filter(
        models.Student.id.in_(relevant_student_ids) # Only fetch students with a valid current year record
    ).order_by(models.Student.name).all() # Order by student name


    # 3. Construct the response
    student_details_list = []
    for db_student in db_students:
        if not db_student.user:
            logger.warning(f"Skipping student {db_student.id} in grade {grade_id} due to missing user data.")
            continue

        # We know the student is in the map because we filtered by relevant_student_ids
        current_sy = student_year_map.get(db_student.id)

        # Double check just in case map logic had issues (shouldn't happen now)
        if current_sy and current_sy.section:
            student_details_list.append(schemas.StudentDetails(
                id=db_student.id,
                name=db_student.name,
                user=db_student.user,
                section=current_sy.section, # Pass the section object from the current StudentYear
                year=current_sy.year       # Pass the current year
            ))
        else:
             logger.error(f"Data inconsistency: Student {db_student.id} was expected in map but StudentYear/Section data missing.")


    logger.info(f"Retrieved {len(student_details_list)} student details for grade {grade_id}, year {current_year}.")
    return student_details_list
# --- END NEW ENDPOINT ---


@router.put("/{grade_id}", response_model=schemas.GradeCreate)
def update_grade(
    grade_id: int,
    grade: schemas.GradeCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Updates a grade by ID (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_grade = db.query(models.Grade).filter(models.Grade.id == grade_id).first()
    if db_grade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found")

    db_grade.name = grade.name
    db.commit()
    db.refresh(db_grade)
    # Return the ORM object which Pydantic can map if schema configured
    # Or return the input `grade` object if response_model matches exactly
    return db_grade # Assuming GradeCreate matches GradeInfo fields needed for response


@router.delete("/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grade(
    grade_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Deletes a grade by ID (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_grade = db.query(models.Grade).filter(models.Grade.id == grade_id).first()
    if db_grade is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grade not found")

    # Check for dependencies if cascade delete isn't reliable/desired
    has_sections = db.query(models.Section.id).filter(models.Section.grade_id == grade_id).limit(1).first()
    has_subjects = db.query(models.Subject.id).filter(models.Subject.grade_id == grade_id).limit(1).first()
    has_terms = db.query(models.Term.id).filter(models.Term.grade_id == grade_id).limit(1).first()

    if has_sections or has_subjects or has_terms:
       dependencies = []
       if has_sections: dependencies.append("sections")
       if has_subjects: dependencies.append("subjects")
       if has_terms: dependencies.append("terms")
       raise HTTPException(status_code=409, detail=f"Cannot delete grade with associated {', '.join(dependencies)}.")

    try:
        db.delete(db_grade)
        db.commit()
        return None # Return None for 204
    except Exception as e: # Catch potential FK violations if check above missed something or cascade fails
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Cannot delete grade. It might be referenced. Error: {e}")
    