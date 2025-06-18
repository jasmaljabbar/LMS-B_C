# backend/routes/assignment_formats.py
from pydantic import BaseModel, Field
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import List, Optional, Dict, Any
from sqlalchemy.exc import IntegrityError
# --- Added Import ---
import uuid
# --- End Added Import ---

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.logger_utils import log_activity

from backend.services.generation_service import generate_assignment_questions, modify_assignment_questions

router = APIRouter(prefix="/assignment-formats", tags=["Assignment Formats"])
logger = logging.getLogger(__name__)

# --- CRUD Endpoints for Formats (create_assignment_format, read_assignment_formats, read_assignment_format, update_assignment_format, delete_assignment_format - remain unchanged) ---
@router.post("/", response_model=schemas.AssignmentFormatInfo, status_code=status.HTTP_201_CREATED)
def create_assignment_format(
    format_data: schemas.AssignmentFormatCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Creates a new assignment paper format with specified question types and counts.
    Requires Teacher or Admin role.
    """
    if current_user.user_type not in ["Teacher", "Admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Teachers or Admins can create assignment formats.")

    subject = db.query(models.Subject).filter(models.Subject.id == format_data.subject_id).first()
    if not subject:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subject with ID {format_data.subject_id} not found.")

    existing_format = db.query(models.AssignmentFormat).filter(models.AssignmentFormat.name == format_data.name).first()
    if existing_format:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Assignment format name '{format_data.name}' already exists.")

    db_format = models.AssignmentFormat(
        name=format_data.name,
        subject_id=format_data.subject_id,
        created_by_user_id=current_user.id
    )
    db.add(db_format)
    try:
        db.flush(); format_id = db_format.id
        format_questions = []
        for q_count in format_data.questions:
            if q_count.count > 0:
                db_q = models.AssignmentFormatQuestion(assignment_format_id=format_id, question_type=q_count.type.value, count=q_count.count)
                format_questions.append(db_q)
        if not format_questions: logger.warning(f"Format '{format_data.name}' created with no questions > 0.")
        db.add_all(format_questions); db.commit(); db.refresh(db_format)
        db.refresh(db_format, attribute_names=['questions', 'creator', 'subject'])
        log_activity(db=db, user_id=current_user.id, action='ASSIGNMENT_FORMAT_CREATED',
                     details=f"User '{current_user.username}' created format '{db_format.name}' (ID: {db_format.id}) for Subject ID {db_format.subject_id}.",
                     target_entity='AssignmentFormat', target_entity_id=db_format.id)
        return db_format
    except IntegrityError as e:
        db.rollback(); logger.error(f"Integrity error creating format: {e}", exc_info=True)
        if "uq_assignment_formats_name" in str(e.orig): raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Format name '{format_data.name}' already exists.")
        elif "FOREIGN KEY (`subject_id`)" in str(e.orig):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Subject with ID {format_data.subject_id} not found.")
        else: raise HTTPException(status_code=400, detail="DB constraint violation.")
    except Exception as e:
        db.rollback(); logger.error(f"Unexpected error creating format: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error.")

@router.get("/", response_model=List[schemas.AssignmentFormatInfo])
def read_assignment_formats(
    subject_id: Optional[int] = Query(None, description="Filter by Subject ID"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Retrieves a list of all assignment paper formats, optionally filtered by subject ID.
    """
    query = db.query(models.AssignmentFormat).options(
        selectinload(models.AssignmentFormat.questions),
        joinedload(models.AssignmentFormat.creator).load_only(models.User.username),
        joinedload(models.AssignmentFormat.subject)
    )

    if subject_id is not None:
        subject_exists = db.query(models.Subject.id).filter(models.Subject.id == subject_id).first()
        if not subject_exists:
            raise HTTPException(status_code=404, detail=f"Subject with ID {subject_id} not found.")
        query = query.filter(models.AssignmentFormat.subject_id == subject_id)

    formats = query.order_by(models.AssignmentFormat.name).offset(skip).limit(limit).all()
    return formats

@router.get("/{format_id}", response_model=schemas.AssignmentFormatInfo)
def read_assignment_format(
    format_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user),
):
    """
    Retrieves a specific assignment paper format by its ID.
    """
    db_format = db.query(models.AssignmentFormat).options(
        selectinload(models.AssignmentFormat.questions),
        joinedload(models.AssignmentFormat.creator).load_only(models.User.username),
        joinedload(models.AssignmentFormat.subject)
    ).filter(models.AssignmentFormat.id == format_id).first()
    if not db_format: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Format not found.")
    return db_format

@router.put("/{format_id}", response_model=schemas.AssignmentFormatInfo)
def update_assignment_format(
    format_id: int, format_update_data: schemas.AssignmentFormatUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user),
):
    """
    Updates an assignment paper format.
    Updating 'questions' replaces the entire list of question definitions for this format.
    Requires creator or Admin role.
    """
    db_format = db.query(models.AssignmentFormat).options(
        selectinload(models.AssignmentFormat.questions),
        joinedload(models.AssignmentFormat.creator),
        joinedload(models.AssignmentFormat.subject)
        ).filter(models.AssignmentFormat.id == format_id).first()

    if not db_format: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Format not found.")
    is_admin = current_user.user_type == "Admin"; is_creator = db_format.creator and db_format.created_by_user_id == current_user.id
    if not (is_admin or is_creator): raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    updated_fields = []; original_name = db_format.name
    if format_update_data.name is not None and db_format.name != format_update_data.name:
        existing = db.query(models.AssignmentFormat.id).filter(models.AssignmentFormat.name == format_update_data.name, models.AssignmentFormat.id != format_id).first()
        if existing: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Format name '{format_update_data.name}' exists.")
        db_format.name = format_update_data.name; updated_fields.append("name")

    if format_update_data.subject_id is not None and db_format.subject_id != format_update_data.subject_id:
        subject = db.query(models.Subject).filter(models.Subject.id == format_update_data.subject_id).first()
        if not subject:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Subject with ID {format_update_data.subject_id} not found.")
        db_format.subject_id = format_update_data.subject_id
        updated_fields.append("subject_id")

    if format_update_data.questions is not None:
        db.query(models.AssignmentFormatQuestion).filter(models.AssignmentFormatQuestion.assignment_format_id == format_id).delete(synchronize_session=False)
        new_questions = []
        for q_count in format_update_data.questions:
             if q_count.count > 0: new_questions.append(models.AssignmentFormatQuestion(assignment_format_id=format_id, question_type=q_count.type.value, count=q_count.count))
        if new_questions: db.add_all(new_questions)
        updated_fields.append("questions"); db.expire(db_format, ['questions'])

    if not updated_fields: logger.info(f"No updates for format {format_id}."); db.refresh(db_format, attribute_names=['questions', 'creator', 'subject']); return db_format
    try:
        db.commit(); db.refresh(db_format);
        db.refresh(db_format, attribute_names=['questions', 'creator', 'subject'])
        log_activity(db=db, user_id=current_user.id, action='ASSIGNMENT_FORMAT_UPDATED',
                     details=f"User '{current_user.username}' updated format '{original_name}' -> '{db_format.name}' (ID: {format_id}). Fields: {', '.join(updated_fields)}.",
                     target_entity='AssignmentFormat', target_entity_id=format_id)
        return db_format
    except IntegrityError as e:
        db.rollback(); logger.error(f"Integrity error updating format {format_id}: {e}", exc_info=True)
        if "uq_assignment_formats_name" in str(e.orig): raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Format name '{format_update_data.name}' exists.")
        elif "uq_assignment_format_question_type" in str(e.orig): raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate question type.")
        elif "FOREIGN KEY (`subject_id`)" in str(e.orig):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Subject with ID {format_update_data.subject_id} not found.")
        else: raise HTTPException(status_code=400, detail="DB constraint violation.")
    except Exception as e:
        db.rollback(); logger.error(f"Unexpected error updating format {format_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error.")

@router.delete("/{format_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment_format(
    format_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user),
):
    """
    Deletes an assignment paper format and its associated question definitions.
    Requires creator or Admin role.
    """
    db_format = db.query(models.AssignmentFormat).options(joinedload(models.AssignmentFormat.creator)).filter(models.AssignmentFormat.id == format_id).first()
    if not db_format: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Format not found.")
    is_admin = current_user.user_type == "Admin"; is_creator = db_format.creator and db_format.created_by_user_id == current_user.id
    if not (is_admin or is_creator): raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    format_name_deleted = db_format.name
    try:
        has_assessments = db.query(models.Assessment.id).filter(models.Assessment.assignment_format_id == format_id).limit(1).first()
        if has_assessments:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete format, it is currently used by one or more assessments.")

        db.delete(db_format); db.commit()
        log_activity(db=db, user_id=current_user.id, action='ASSIGNMENT_FORMAT_DELETED',
                     details=f"User '{current_user.username}' deleted format '{format_name_deleted}' (ID: {format_id}).",
                     target_entity='AssignmentFormat', target_entity_id=format_id)
        return None
    except IntegrityError as e: db.rollback(); logger.error(f"Integrity error deleting format {format_id}: {e}", exc_info=True); raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete format, referenced elsewhere.")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e: db.rollback(); logger.error(f"Unexpected error deleting format {format_id}: {e}", exc_info=True); raise HTTPException(status_code=500, detail="Failed delete.")


# --- Generation and Modification Endpoints ---

class GenerateAssignmentRequest(BaseModel):
    lesson_ids: List[int] = Field(..., min_items=1)

@router.post("/{format_id}/generate", response_model=schemas.GenerateAssignmentResponse)
async def generate_assignment_from_format_and_lessons(
    format_id: int,
    request_body: GenerateAssignmentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Generates assignment questions using Gemini based on a format and lesson content PDFs.
    """
    if current_user.user_type not in ["Teacher", "Admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Teachers or Admins can generate assignments.")

    assignment_format = db.query(models.AssignmentFormat).options(
        selectinload(models.AssignmentFormat.questions)
    ).filter(models.AssignmentFormat.id == format_id).first()
    if not assignment_format:
        raise HTTPException(status_code=404, detail=f"Assignment Format with ID {format_id} not found.")
    if not assignment_format.questions:
         raise HTTPException(status_code=400, detail=f"Assignment Format with ID {format_id} has no question definitions.")

    lesson_gs_urls: List[str] = []
    valid_lesson_ids: List[int] = []
    for lesson_id in request_body.lesson_ids:
        pdf_urls_query = db.query(models.URL.url).join(
            models.PDFUrl, models.URL.id == models.PDFUrl.url_id
        ).join(
            models.PDF, models.PDFUrl.pdf_id == models.PDF.id
        ).filter(
            models.PDF.lesson_id == lesson_id,
            models.URL.url_type == schemas.UrlTypeEnum.GS.value
        )
        found_urls = [row[0] for row in pdf_urls_query.all()]
        if found_urls:
             lesson_gs_urls.extend(found_urls)
             valid_lesson_ids.append(lesson_id)
        else:
             logger.warning(f"No GS PDF URLs found for lesson ID {lesson_id}. It will be skipped.")

    if not lesson_gs_urls:
         raise HTTPException(status_code=404, detail="No processable PDF content (GS URLs) found for the provided lesson IDs.")

    # --- Call the Generation Service with token logging parameters ---
    session_id = str(uuid.uuid4())
    action_name = f"generate_questions_fmt_{format_id}"
    try:
        generation_result = await generate_assignment_questions(
            assignment_format=assignment_format,
            lesson_gs_urls=list(set(lesson_gs_urls)),
            user_id=current_user.id,      # Pass user_id
            action=action_name,           # Pass descriptive action
            session_id=session_id         # Pass session_id
        )
        log_activity(
            db=db, user_id=current_user.id, action='ASSIGNMENT_GENERATED',
            details=f"User '{current_user.username}' generated assignment using format '{assignment_format.name}' (ID: {format_id}), lessons {valid_lesson_ids}. Session: {session_id}.",
            target_entity='AssignmentFormat', target_entity_id=format_id
        )
        return generation_result
    except HTTPException as http_exc: raise http_exc
    except Exception as e:
        logger.error(f"Error calling generation service for format {format_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate assignment questions.")


class ModifyAssignmentRequest(BaseModel):
    previous_questions: List[schemas.GeneratedQuestion]
    modification_instructions: str = Field(..., min_length=5)

@router.post("/modify", response_model=schemas.ModifyAssignmentResponse)
async def modify_generated_assignment(
    request_body: ModifyAssignmentRequest,
    current_user: models.User = Depends(get_current_user),
):
    """
    Modifies previously generated assignment questions based on user instructions using Gemini.
    """
    if current_user.user_type not in ["Teacher", "Admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Teachers or Admins can modify generated assignments.")

    previous_questions_dict = [q.dict(exclude_none=True) for q in request_body.previous_questions]

    try:
        # (Token logging for 'modify' can be added similarly to 'generate' if needed in the future)
        # session_id = str(uuid.uuid4())
        # action_name = "modify_generated_questions"
        modification_result = await modify_assignment_questions(
            previous_questions=previous_questions_dict,
            modification_instructions=request_body.modification_instructions
            # user_id=current_user.id,
            # action=action_name,
            # session_id=session_id
        )
        # Consider adding an audit log here if needed
        return modification_result
    except HTTPException as http_exc: raise http_exc
    except Exception as e:
        logger.error(f"Error calling modification service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to modify assignment questions.")