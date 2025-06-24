# backend/routes/lesson.py
# --- Add Query to imports ---
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload, selectinload # Added selectinload
from typing import List, Dict, Union, Optional
from sqlalchemy.exc import IntegrityError
import logging # Added logging

from backend import models, schemas # Import the new LessonBasicInfo schema
from backend.database import get_db
from backend.dependencies import get_current_user # Keep authentication
# Import term helper function if needed, or replicate validation logic
try:
    from .terms import _get_term # Assuming terms.py is in the same directory
except ImportError: # Handle potential circular import or structure issues
    def _get_term(term_id: int, db: Session):
        term = db.query(models.Term).filter(models.Term.id == term_id).first()
        if not term:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Term with id {term_id} not found."
            )
        return term

# --- Helper Function to Validate Subject Existence (similar to _get_term) ---
def _get_subject(subject_id: int, db: Session):
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subject with id {subject_id} not found."
        )
    return subject
# --- End Helper ---

logger = logging.getLogger(__name__) # Added logger
router = APIRouter(prefix="/lessons", tags=["Lessons"])


# === HELPER FUNCTION (Modified for Term) ===
def _get_lesson_files_filtered(
    lesson_id: int,
    db: Session,
    filter_url_type: Optional[str] = None
) -> List[Dict[str, Union[str, int, None]]]:
    """
    Helper function to retrieve file information for a lesson,
    optionally filtering by URL type (e.g., 'https', 'gs').
    """
    # Eager load related data including term
    db_lesson = db.query(models.Lesson).options(
        selectinload(models.Lesson.pdfs).selectinload(models.PDF.urls).joinedload(models.PDFUrl.url),
        selectinload(models.Lesson.videos).joinedload(models.Video.url),
        joinedload(models.Lesson.term) # Load term info too
    ).filter(models.Lesson.id == lesson_id).first()

    if db_lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    files = []

    # PDFs
    for pdf in db_lesson.pdfs:
        for pdf_url_assoc in pdf.urls:
            db_url = pdf_url_assoc.url
            if db_url:
                if filter_url_type is None or db_url.url_type == filter_url_type:
                    files.append({
                        "id": pdf.id,
                        "name": pdf.name,
                        "url": db_url.url,
                        "type": "pdf",
                        "url_type": db_url.url_type,
                        "size": pdf.size
                    })

    # Videos
    for video in db_lesson.videos:
        db_url = video.url
        if db_url:
            if filter_url_type is None or db_url.url_type == filter_url_type:
                files.append({
                    "id": video.id,
                    "name": video.name,
                    "url": db_url.url,
                    "type": "video",
                    "url_type": db_url.url_type,
                    "size": video.size
                })

    return files

# --- Validate Subject Existence ---
def _validate_subject_exists(subject_id: int, db: Session):
    """Checks if the subject exists."""
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Subject with id {subject_id} not found.")

# --- Modified and Existing Endpoints ---

@router.post("/", response_model=schemas.LessonInfo, status_code=status.HTTP_201_CREATED)
def create_lesson(
    lesson: schemas.LessonCreate,  # Schema should no longer include term_id
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Creates a new lesson, linking it to a subject."""
    _validate_subject_exists(lesson.subject_id, db)

    db_lesson = models.Lesson(**lesson.dict())
    try:
        db.add(db_lesson)
        db.commit()
        db.refresh(db_lesson)
        logger.info(f"Created Lesson '{db_lesson.name}' (ID: {db_lesson.id}) for Subject {lesson.subject_id} by user {current_user.username}")
        return db_lesson
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error creating lesson: {e}", exc_info=True)
        detail = "Failed to create lesson due to database constraint."
        if "FOREIGN KEY (`subject_id`)" in str(e.orig):
            detail = f"Invalid subject_id ({lesson.subject_id}). Subject does not exist."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error creating lesson: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")

@router.get("/{lesson_id}", response_model=schemas.LessonInfo)
def read_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves a lesson by ID."""
    db_lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if db_lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )
    return db_lesson

@router.get("/", response_model=List[schemas.LessonInfo])
def read_lessons(
    subject_id: Optional[int] = None,  # Only subject filter remains
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves lessons, optionally filtered by subject_id."""
    query = db.query(models.Lesson)
    if subject_id:
        query = query.filter(models.Lesson.subject_id == subject_id)

    db_lessons = query.offset(skip).limit(limit).all()
    return db_lessons

@router.get("/subject/{subject_id}", response_model=List[schemas.LessonInfo])
def read_lessons_by_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves lessons by subject ID."""
    subject_exists = db.query(models.Subject.id).filter(models.Subject.id == subject_id).first()
    if not subject_exists:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subject with id {subject_id} not found.")

    db_lessons = db.query(models.Lesson).filter(models.Lesson.subject_id == subject_id).all()
    return db_lessons

# Remove the term-related endpoints completely
# @router.get("/term/{term_id}", ...) - DELETE THIS
# @router.get("/by-term-subject/", ...) - DELETE THIS

@router.put("/{lesson_id}", response_model=schemas.LessonInfo)
def update_lesson(
    lesson_id: int,
    lesson: schemas.LessonCreate,  # Schema should no longer include term_id
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Updates a lesson by ID."""
    db_lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if db_lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    _validate_subject_exists(lesson.subject_id, db)

    # Update fields
    update_data = lesson.dict()
    for key, value in update_data.items():
        setattr(db_lesson, key, value)

    try:
        db.commit()
        db.refresh(db_lesson)
        logger.info(f"Updated Lesson ID {lesson_id} by user {current_user.username}")
        return db_lesson
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error updating lesson {lesson_id}: {e}", exc_info=True)
        detail = "Failed to update lesson due to database constraint."
        if "FOREIGN KEY (`subject_id`)" in str(e.orig):
            detail = f"Invalid subject_id ({lesson.subject_id}). Subject does not exist."
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error updating lesson {lesson_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")


@router.delete("/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Deletes a lesson by ID."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type not in ["Admin", "Teacher"]:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
    #     )
    # --- END REMOVAL ---

    db_lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
    if db_lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found"
        )

    # Optional: Check dependencies if cascade delete isn't reliable/desired
    # pdf_count = db.query(models.PDF).filter(...).count()
    # video_count = db.query(models.Video).filter(...).count()
    # assessment_count = db.query(models.Assessment).filter(...).count()
    # if pdf_count > 0 or video_count > 0 or assessment_count > 0:
    #     raise HTTPException(status_code=409, detail="Cannot delete lesson with associated content (PDFs, videos, assessments).")

    try:
        db.delete(db_lesson)
        db.commit()
        logger.info(f"Deleted Lesson ID {lesson_id} by user {current_user.username}")
        return None
    except IntegrityError as e:
         db.rollback()
         logger.error(f"Integrity error deleting lesson {lesson_id}: {e}", exc_info=True)
         # This might happen if related items block deletion due to FK constraints without cascade
         raise HTTPException(
             status_code=status.HTTP_409_CONFLICT,
             detail=f"Cannot delete lesson {lesson_id} as it might be referenced by other items (PDFs, Videos, Assessments)."
         )
    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error deleting lesson {lesson_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete lesson.")


# Keep file-related endpoints as they are, using the modified helper
@router.get("/{lesson_id}/files", response_model=List[Dict[str, Union[str, int, None]]])
def read_lesson_files(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves ALL file information (id, name, url, type, url_type, size) for a given lesson."""
    # No specific role check was present here
    return _get_lesson_files_filtered(lesson_id, db, filter_url_type=None)

@router.get("/{lesson_id}/files/https", response_model=List[Dict[str, Union[str, int, None]]])
def read_lesson_files_https(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves HTTPS file information (id, name, url, type, url_type, size) for a given lesson."""
    # No specific role check was present here
    return _get_lesson_files_filtered(lesson_id, db, filter_url_type='https')

@router.get("/{lesson_id}/files/gs", response_model=List[Dict[str, Union[str, int, None]]])
def read_lesson_files_gs(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves GS file information (id, name, url, type, url_type, size) for a given lesson."""
    # No specific role check was present here
    return _get_lesson_files_filtered(lesson_id, db, filter_url_type='gs')
