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
    current_user: models.User = Depends(get_current_user),
):
    """Creates a new subject for a specific student."""
    print(current_user.user_type)
    # Check if current user is parent or admin
    if current_user.user_type not in ["Parent", "Admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only parents or admins can create subjects"
        )
    
    # If parent, verify they own the student
    if current_user.user_type == "parent":
        parent = db.query(models.Parent).filter(models.Parent.user_id == current_user.id).first()
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Parent profile not found"
            )
        
        # Check if student belongs to parent
        student_exists = db.query(models.Student).filter(
            models.Student.id == subject.student_id,
            models.Student.parents.any(id=parent.id)
        ).first()
        
        if not student_exists:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to create subjects for this student"
            )
    
    # Check if student exists
    student = db.query(models.Student).filter(models.Student.id == subject.student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Student with ID {subject.student_id} not found."
        )
    
    # Check for duplicate subject name for this student
    existing_subject = db.query(models.Subject).filter(
        models.Subject.student_id == subject.student_id,
        models.Subject.name == subject.name
    ).first()
    
    if existing_subject:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subject '{subject.name}' already exists for this student."
        )
    
    db_subject = models.Subject(
        name=subject.name,
        student_id=subject.student_id
    )
    
    try:
        db.add(db_subject)
        db.commit()
        db.refresh(db_subject)
        return db_subject
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the subject: {str(e)}"
        )



@router.get("/{subject_id}", response_model=schemas.SubjectInfo)
def read_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves a subject by ID."""
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
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves all subjects."""
    db_subjects = db.query(models.Subject).offset(skip).limit(limit).all()
    return db_subjects

@router.get("/student/{student_id}", response_model=List[schemas.SubjectInfo])
def read_subjects_by_student(
    student_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves subjects by student ID."""
    # Check if student exists first
    student_exists = db.query(models.Student.id).filter(models.Student.id == student_id).first()
    if not student_exists:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student with id {student_id} not found.")

    db_subjects = (
        db.query(models.Subject)
        .filter(models.Subject.student_id == student_id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return db_subjects

@router.get(
    "/{subject_id}/student-details",
    response_model=schemas.SubjectStudentDetails,
    summary="Get Student Details for a Subject",
    description="Retrieves the student details for a given subject ID."
)
def read_student_details_for_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Retrieves the Student details associated with the specified Subject ID.
    """
    # Fetch the subject and eagerly load its related student
    db_subject = db.query(models.Subject).options(
        joinedload(models.Subject.student)  # Eager load the student
    ).filter(models.Subject.id == subject_id).first()

    if db_subject is None:
        logger.warning(f"Subject with ID {subject_id} not found.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subject with ID {subject_id} not found"
        )

    if db_subject.student is None:
        logger.error(f"Subject {subject_id} found, but has no associated Student.")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student associated with subject {subject_id} not found."
        )

    return schemas.SubjectStudentDetails(
        student=db_subject.student
    )

@router.put("/{subject_id}", response_model=schemas.SubjectInfo)
def update_subject(
    subject_id: int,
    subject: schemas.SubjectCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Updates a subject by ID."""
    db_subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if db_subject is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found"
        )

    # Check if new student_id exists
    if subject.student_id != db_subject.student_id:
        student_exists = db.query(models.Student.id).filter(models.Student.id == subject.student_id).first()
        if not student_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail=f"Student with ID {subject.student_id} not found."
            )

        # If user is parent, verify they own the new student
        if current_user.user_type == "Parent":
            parent = db.query(models.Parent).filter(models.Parent.user_id == current_user.id).first()
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Parent profile not found"
                )
            
            student_belongs = db.query(models.Student).filter(
                models.Student.id == subject.student_id,
                models.Student.parents.any(id=parent.id)
            ).first()
            
            if not student_belongs:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to move subject to this student"
                )

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
        if "FOREIGN KEY (`student_id`)" in str(e.orig):
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid student_id ({subject.student_id}). Student does not exist.",
            )
        else:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update subject due to database constraint.",
            )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An unexpected error occurred: {e}"
        )


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
