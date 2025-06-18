# backend/routes/assessments.py
import logging
import json # Import json
# --- Add Query ---
from fastapi import APIRouter, HTTPException, Depends, status, Query
# --- Add List, Optional ---
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from enum import Enum
from sqlalchemy.exc import IntegrityError
from datetime import datetime # Import datetime
import uuid # Added import for uuid

# Assuming QuestionGenerator might still be needed here for the old endpoint
try:
    # Use relative import assuming services is a sibling package/directory
    from ..services.question_generator import QuestionGenerator
except ImportError:
    # Fallback if the structure is different or running script directly
    try:
        from backend.services.question_generator import QuestionGenerator
    except ImportError:
        QuestionGenerator = None
        logging.getLogger(__name__).warning("QuestionGenerator service not found.")


from backend.database import get_db
from backend import models, schemas
from backend.dependencies import get_current_user
from backend.logger_utils import log_activity # Import log_activity

router = APIRouter(
    prefix="/assessments",
    tags=["Assessments"]
)

logger = logging.getLogger(__name__)

# Initialize question generator (keep if generation is done here)
question_generator = None
if QuestionGenerator:
    try:
        question_generator = QuestionGenerator()
    except Exception as e:
        logger.error(f"Failed to initialize QuestionGenerator: {e}", exc_info=True)
        question_generator = None


# --- Existing Enum and Request Models for original Generation (Keep if needed) ---
class QuestionType(str, Enum):
    FILL_IN_BLANKS = "fill_in_blanks"
    MATCH_FOLLOWING = "match_following"
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    SHORT_ANSWER = "short_answer"

class QuestionRequest(BaseModel):
    type: QuestionType
    count: int

class GenerateQuestionsRequest(BaseModel):
    lesson_ids: List[int]
    questions: List[QuestionRequest]


# --- Existing Generation Endpoint (Keep if needed, but mark as deprecated) ---
@router.post("/generate")
async def generate_questions(
    request: GenerateQuestionsRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    [DEPRECATED - Use format-based generation] Generate questions based on lesson content.
    """
    logger.warning("Deprecated /assessments/generate endpoint called. Use format-based generation instead.")
    if question_generator is None:
         raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Assessment generation service unavailable.")
    if not request.lesson_ids: raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No lesson IDs provided.")
    lesson_gs_urls = set()
    logger.info(f"Fetching content URLs for lesson IDs: {request.lesson_ids}")
    for lesson_id in request.lesson_ids:
        lesson_exists = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
        if not lesson_exists: logger.warning(f"Lesson ID {lesson_id} not found, skipping."); continue
        db_pdfs = db.query(models.PDF).options(joinedload(models.PDF.urls).joinedload(models.PDFUrl.url)).filter(models.PDF.lesson_id == lesson_id).all()
        found_pdf_url = False
        for pdf in db_pdfs:
            for pdf_url_assoc in pdf.urls:
                if pdf_url_assoc.url and pdf_url_assoc.url.url_type == 'gs': lesson_gs_urls.add(pdf_url_assoc.url.url); found_pdf_url = True
                elif pdf_url_assoc.url and pdf_url_assoc.url.url.startswith("gs://"): lesson_gs_urls.add(pdf_url_assoc.url.url); found_pdf_url = True
        if not found_pdf_url: logger.debug(f"No GS URLs found for any PDFs in lesson {lesson_id}.")
        db_videos = db.query(models.Video).options(joinedload(models.Video.url)).filter(models.Video.lesson_id == lesson_id).all()
        found_video_url = False
        for video in db_videos:
            if video.url and video.url.url_type == 'gs': lesson_gs_urls.add(video.url.url); found_video_url = True
            elif video.url and video.url.url.startswith("gs://"): lesson_gs_urls.add(video.url.url); found_video_url = True
        if not found_video_url: logger.debug(f"No GS URLs found for any Videos in lesson {lesson_id}.")
    final_urls = list(lesson_gs_urls)
    if not final_urls: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No processable content found for the provided lesson IDs.")
    logger.info(f"Generating assessment questions using {len(final_urls)} GS URLs from lessons {request.lesson_ids}.")
    try:
        result = await question_generator.generate_questions(
            final_urls, 
            [{"type": q.type.value, "count": q.count} for q in request.questions],
            user_id=current_user.id,
            action="generate_assessment_questions_legacy", # As specified
            session_id=str(uuid.uuid4())
        )
        return result
    except ValueError as ve: logger.error(f"Question generation failed: {ve}", exc_info=True); raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed: {str(ve)}")
    except Exception as e: logger.error(f"Unexpected error during generation: {e}", exc_info=True); raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error generating questions.")


# --- Endpoint to CREATE an Assessment Definition ---
@router.post("/definitions", response_model=schemas.AssessmentInfo, status_code=status.HTTP_201_CREATED)
def create_assessment_definition(
    assessment_data: schemas.AssessmentCreate, # Input schema now uses lesson_ids
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Creates a new assessment definition (metadata), linking it to one or more lessons,
    and optionally including finalized question content.
    """
    if current_user.user_type not in ["Admin", "Teacher"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to create assessments.")

    # --- MODIFIED: Validate multiple lesson_ids ---
    linked_lessons = []
    if assessment_data.lesson_ids:
        if not isinstance(assessment_data.lesson_ids, list):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="lesson_ids must be a list.")
        if assessment_data.lesson_ids: # Only query if list is not empty
            # Fetch all requested lessons at once for efficiency
            linked_lessons = db.query(models.Lesson).filter(models.Lesson.id.in_(assessment_data.lesson_ids)).all()
            # Check if all provided IDs were found
            if len(linked_lessons) != len(set(assessment_data.lesson_ids)):
                found_ids = {lesson.id for lesson in linked_lessons}
                missing_ids = set(assessment_data.lesson_ids) - found_ids
                raise HTTPException(status_code=404, detail=f"Lesson(s) with ID(s) {missing_ids} not found.")
        else:
            logger.warning("lesson_ids provided as an empty list for assessment creation.")
    # --- END MODIFICATION ---

    # Validate subject_id if provided
    if assessment_data.subject_id:
        subject = db.query(models.Subject.id).filter(models.Subject.id == assessment_data.subject_id).first()
        if not subject: raise HTTPException(status_code=404, detail=f"Subject with ID {assessment_data.subject_id} not found.")

    # Validate assignment_format_id if provided
    if assessment_data.assignment_format_id:
        a_format = db.query(models.AssignmentFormat.id).filter(models.AssignmentFormat.id == assessment_data.assignment_format_id).first()
        if not a_format: raise HTTPException(status_code=404, detail=f"Assignment Format with ID {assessment_data.assignment_format_id} not found.")

    # Prepare content for DB storage
    content_to_store = None
    if assessment_data.content:
        if not isinstance(assessment_data.content, list):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assessment 'content' must be a list of questions.")
        try:
            content_to_store = [q.dict(exclude_none=True) for q in assessment_data.content]
        except Exception as e:
            logger.error(f"Error processing assessment content data: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid format for assessment content field.")

    # Create the Assessment database object
    db_assessment = models.Assessment(
        name=assessment_data.name,
        description=assessment_data.description,
        # lesson_id=assessment_data.lesson_id, # Removed
        subject_id=assessment_data.subject_id,
        due_date=assessment_data.due_date,
        content=content_to_store,
        assignment_format_id=assessment_data.assignment_format_id,
        created_by_user_id=current_user.id
    )

    # --- MODIFIED: Add lessons to the many-to-many relationship ---
    if linked_lessons:
        db_assessment.lessons.extend(linked_lessons)
    # --- END MODIFICATION ---

    try:
        db.add(db_assessment)
        db.commit()
        db.refresh(db_assessment)
        # Load relations needed for the response schema's computed fields
        db.refresh(db_assessment, attribute_names=['creator', 'assignment_format', 'lessons']) # Add 'lessons'

        logger.info(f"Created assessment definition '{db_assessment.name}' (ID: {db_assessment.id}) linked to lessons {[l.id for l in linked_lessons]} by user {current_user.username}")

        # Audit Log
        log_activity(
            db=db, user_id=current_user.id, action='ASSESSMENT_DEFINITION_CREATED',
            details=f"User '{current_user.username}' created assessment definition '{db_assessment.name}' (ID: {db_assessment.id}). Linked lessons: {[l.id for l in linked_lessons]}.",
            target_entity='Assessment', target_entity_id=db_assessment.id
        )

        return db_assessment
    except IntegrityError as e:
         db.rollback()
         logger.error(f"Integrity error creating assessment definition: {e}", exc_info=True)
         raise HTTPException(status_code=400, detail="Database constraint violation during assessment creation.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating assessment definition: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create assessment definition")


# --- Endpoint to GET Assessment Definitions ---
@router.get("/definitions", response_model=List[schemas.AssessmentInfo])
def get_assessment_definitions(
    lesson_id: Optional[int] = Query(None, description="Filter assessments containing this lesson ID"), # Keep lesson filter if needed
    subject_id: Optional[int] = Query(None, description="Filter assessments by subject ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves a list of assessment definitions, optionally filtered."""
    query = db.query(models.Assessment).options(
        selectinload(models.Assessment.lessons), # Eager load lesson links
        joinedload(models.Assessment.assignment_format), # Load format info
        joinedload(models.Assessment.creator).load_only(models.User.username) # Load creator username
    )

    # --- Filter by lesson_id using the association table ---
    if lesson_id:
        # Check if lesson exists
        lesson_exists = db.query(models.Lesson.id).filter(models.Lesson.id == lesson_id).first()
        if not lesson_exists:
             raise HTTPException(status_code=404, detail=f"Lesson with ID {lesson_id} not found.")
        # Join with association table and filter
        query = query.join(models.assessment_lesson_association).filter(
            models.assessment_lesson_association.c.lesson_id == lesson_id
        )
    # --- End lesson_id filter ---

    if subject_id:
        # Check if subject exists
        subject_exists = db.query(models.Subject.id).filter(models.Subject.id == subject_id).first()
        if not subject_exists:
             raise HTTPException(status_code=404, detail=f"Subject with ID {subject_id} not found.")
        query = query.filter(models.Assessment.subject_id == subject_id)

    assessments = query.order_by(models.Assessment.creation_date.desc()).offset(skip).limit(limit).all()
    return assessments

# --- Endpoint to GET a specific Assessment Definition ---
@router.get("/definitions/{assessment_id}", response_model=schemas.AssessmentInfo)
def get_assessment_definition(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves a specific assessment definition by ID."""
    db_assessment = db.query(models.Assessment).options(
        selectinload(models.Assessment.lessons), # Eager load lesson links
        joinedload(models.Assessment.assignment_format), # Load format info
        joinedload(models.Assessment.creator).load_only(models.User.username) # Load creator username
    ).filter(models.Assessment.id == assessment_id).first()
    if not db_assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment definition not found")
    return db_assessment

# --- Endpoint to UPDATE an Assessment Definition ---
@router.put("/definitions/{assessment_id}", response_model=schemas.AssessmentInfo)
def update_assessment_definition(
    assessment_id: int,
    assessment_data: schemas.AssessmentCreate, # Reuse create schema which has lesson_ids
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Updates an assessment definition by ID, optionally replacing content and lesson links."""
    if current_user.user_type not in ["Admin", "Teacher"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Load assessment and its current lessons & creator
    db_assessment = db.query(models.Assessment).options(
        joinedload(models.Assessment.creator),
        selectinload(models.Assessment.lessons) # Eager load current lessons
    ).filter(models.Assessment.id == assessment_id).first()
    if not db_assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment definition not found")

    # Authorization check: Admin or original creator
    is_admin = current_user.user_type == "Admin"
    is_creator = db_assessment.creator and db_assessment.created_by_user_id == current_user.id
    if not (is_admin or is_creator):
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this assessment")

    updated_fields = []

    # --- Update Lesson Links ---
    new_linked_lessons = None
    if assessment_data.lesson_ids is not None: # Check if lesson_ids is part of the payload
        if not isinstance(assessment_data.lesson_ids, list):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="lesson_ids must be a list.")

        # Fetch the new set of lesson objects
        if not assessment_data.lesson_ids: # Handle empty list case
            new_linked_lessons = []
        else:
            new_linked_lessons = db.query(models.Lesson).filter(models.Lesson.id.in_(assessment_data.lesson_ids)).all()
            # Check if all provided IDs were found
            if len(new_linked_lessons) != len(set(assessment_data.lesson_ids)):
                found_ids = {lesson.id for lesson in new_linked_lessons}
                missing_ids = set(assessment_data.lesson_ids) - found_ids
                raise HTTPException(status_code=404, detail=f"Lesson(s) with ID(s) {missing_ids} not found.")

        # Replace the existing lessons association if it has changed
        current_lesson_ids = {lesson.id for lesson in db_assessment.lessons}
        new_lesson_ids_set = set(assessment_data.lesson_ids)
        if current_lesson_ids != new_lesson_ids_set:
            db_assessment.lessons = new_linked_lessons # Replace the list
            updated_fields.append("lessons")
            db.expire(db_assessment, ['lessons']) # Expire to force reload if needed
    # --- END Update Lesson Links ---

    # Update other fields
    if assessment_data.subject_id is not None and assessment_data.subject_id != db_assessment.subject_id:
        subject = db.query(models.Subject.id).filter(models.Subject.id == assessment_data.subject_id).first()
        if not subject: raise HTTPException(status_code=404, detail=f"Subject with ID {assessment_data.subject_id} not found.")
        db_assessment.subject_id = assessment_data.subject_id; updated_fields.append("subject_id")
    if assessment_data.assignment_format_id is not None and assessment_data.assignment_format_id != db_assessment.assignment_format_id:
        a_format = db.query(models.AssignmentFormat.id).filter(models.AssignmentFormat.id == assessment_data.assignment_format_id).first()
        if not a_format: raise HTTPException(status_code=404, detail=f"Assignment Format with ID {assessment_data.assignment_format_id} not found.")
        db_assessment.assignment_format_id = assessment_data.assignment_format_id; updated_fields.append("assignment_format_id")
    if assessment_data.name != db_assessment.name: # Name is required in schema
        db_assessment.name = assessment_data.name; updated_fields.append("name")
    if assessment_data.description != db_assessment.description:
        db_assessment.description = assessment_data.description; updated_fields.append("description")
    if assessment_data.due_date != db_assessment.due_date:
         db_assessment.due_date = assessment_data.due_date; updated_fields.append("due_date")

    # Update content if provided (allow setting to None/empty list)
    if assessment_data.content is not None: # Check if 'content' key is in the payload
        try:
            # Validate and prepare the new content
            if not isinstance(assessment_data.content, list):
                raise ValueError("Assessment 'content' must be a list of questions.")
            content_to_store = [q.dict(exclude_none=True) for q in assessment_data.content]

            # Compare with current content to see if update is needed
            current_content_comparable = db_assessment.content if isinstance(db_assessment.content, list) else []
            if current_content_comparable != content_to_store: # Only mark as updated if changed
                db_assessment.content = content_to_store
                updated_fields.append("content")
        except Exception as e:
            logger.error(f"Error preparing updated assessment content for DB: {e}")
            raise HTTPException(status_code=400, detail="Invalid format for assessment content.")
    # Removed implicit deletion if content is None - only update if explicitly provided


    if not updated_fields:
         logger.info(f"No updates provided for assessment definition {assessment_id}.")
         # Refresh anyway to ensure relationships are loaded for response
         db.refresh(db_assessment, attribute_names=['creator', 'assignment_format', 'lessons'])
         return db_assessment

    try:
        db.commit()
        db.refresh(db_assessment)
        db.refresh(db_assessment, attribute_names=['creator', 'assignment_format', 'lessons']) # Refresh all relations
        logger.info(f"Updated assessment definition ID {assessment_id} by user {current_user.username}. Fields: {', '.join(updated_fields)}")

        log_activity(
            db=db, user_id=current_user.id, action='ASSESSMENT_DEFINITION_UPDATED',
            details=f"User '{current_user.username}' updated assessment definition '{db_assessment.name}' (ID: {assessment_id}). Fields: {', '.join(updated_fields)}.",
            target_entity='Assessment', target_entity_id=assessment_id
        )

        return db_assessment
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error updating assessment definition {assessment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Database constraint violation during assessment update.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating assessment definition {assessment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update assessment definition")

# --- Endpoint to DELETE an Assessment Definition ---
@router.delete("/definitions/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment_definition(
    assessment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Deletes an assessment definition by ID.
    WARNING: This will also delete associated student scores due to cascade!
    """
    if current_user.user_type not in ["Admin", "Teacher"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Load assessment and creator info for authorization check
    db_assessment = db.query(models.Assessment).options(
        joinedload(models.Assessment.creator)
    ).filter(models.Assessment.id == assessment_id).first()
    if not db_assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment definition not found")

    # Authorization check: Admin or original creator
    is_admin = current_user.user_type == "Admin"
    is_creator = db_assessment.creator and db_assessment.created_by_user_id == current_user.id
    if not (is_admin or is_creator):
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this assessment")

    assessment_name_deleted = db_assessment.name # Store name for logging

    try:
        # Cascade should handle deleting associated StudentAssessmentScore rows
        # and rows in assessment_lesson_association
        db.delete(db_assessment)
        db.commit()
        logger.info(f"Deleted assessment definition ID {assessment_id} and its associated scores/lesson links by user {current_user.username}.")

        log_activity(
            db=db, user_id=current_user.id, action='ASSESSMENT_DEFINITION_DELETED',
            details=f"User '{current_user.username}' deleted assessment definition '{assessment_name_deleted}' (ID: {assessment_id}).",
            target_entity='Assessment', target_entity_id=assessment_id
        )

        return None # Return None for 204
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error deleting assessment definition {assessment_id}: {e}", exc_info=True)
        # This might occur if cascade delete fails or FK constraints block it
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete assessment. It might be referenced by items that were not automatically deleted.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting assessment definition {assessment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to delete assessment definition")


# --- Helper function to get students in a section for the current year ---
def _get_current_students_in_section(section_id: int, db: Session) -> List[int]:
    """Gets IDs of students currently assigned to the section."""
    current_year = datetime.utcnow().year
    student_ids = db.query(models.StudentYear.studentId).filter(
        models.StudentYear.sectionId == section_id,
        models.StudentYear.year == current_year
    ).all()
    return [s_id[0] for s_id in student_ids]
# --- End Helper ---

# --- NEW ENDPOINT ---
@router.post(
    "/{assessment_id}/assign-to-section/{section_id}",
    response_model=schemas.AssignmentResponse,
    status_code=status.HTTP_200_OK, # OK status as we are just logging/confirming
    summary="Assign Assessment to Section Students"
)
def assign_assessment_to_section(
    assessment_id: int,
    section_id: int,
    assignment_request: schemas.AssignAssessmentRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Assigns an assessment to students in a specific section.

    This logs the assignment action. It assigns either to all students currently
    in the section (for the current year) or to a specified subset of those students.

    Requires Admin or Teacher role.
    """
    # 1. Authorization Check
    if current_user.user_type not in ["Admin", "Teacher"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admins or Teachers can assign assessments."
        )

    # 2. Validate Assessment
    db_assessment = db.query(models.Assessment).options(
        joinedload(models.Assessment.subject) # Load subject to check grade
    ).filter(models.Assessment.id == assessment_id).first()
    if not db_assessment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assessment with ID {assessment_id} not found."
        )
    if not db_assessment.subject_id or not db_assessment.subject:
        logger.warning(f"Attempted to assign assessment {assessment_id} which has no associated subject.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assessment ID {assessment_id} is not linked to a subject and cannot be assigned."
        )
    assessment_grade_id = db_assessment.subject.grade_id

    # 3. Validate Section
    db_section = db.query(models.Section).filter(models.Section.id == section_id).first()
    if not db_section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section with ID {section_id} not found."
        )

    # 4. Validate Grade Compatibility
    if db_section.grade_id != assessment_grade_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Assessment's subject (Grade {assessment_grade_id}) does not match Section's grade (Grade {db_section.grade_id})."
        )

    # 5. Get Students Currently in Section
    current_section_student_ids = _get_current_students_in_section(section_id, db)
    if not current_section_student_ids:
        logger.info(f"No students found currently in section {section_id} for assignment.")
        return schemas.AssignmentResponse(
            message=f"No students currently in section {section_id} to assign the assessment to.",
            assessment_id=assessment_id,
            section_id=section_id,
            assigned_student_count=0,
            assigned_student_ids=[]
        )

    # 6. Determine Target Students
    target_student_ids: List[int] = []
    assign_to_all = not assignment_request.student_ids # True if None or empty list

    if assign_to_all:
        target_student_ids = current_section_student_ids
        assignment_target_desc = "all students"
    else:
        # Validate provided student IDs are actually in the section
        valid_requested_ids = []
        invalid_requested_ids = []
        current_section_student_set = set(current_section_student_ids)
        requested_set = set(assignment_request.student_ids)

        for req_id in requested_set:
            if req_id in current_section_student_set:
                valid_requested_ids.append(req_id)
            else:
                invalid_requested_ids.append(req_id)

        if invalid_requested_ids:
            logger.warning(f"User {current_user.username} requested assignment to students not in section {section_id}: {invalid_requested_ids}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"The following student IDs are not currently in section {section_id}: {invalid_requested_ids}"
            )
        target_student_ids = sorted(valid_requested_ids)
        assignment_target_desc = f"students with IDs: {target_student_ids}"

    if not target_student_ids:
         # This can happen if assignment_request.student_ids was provided but none were valid
         message = "No valid students specified or found in the section for assignment."
         assigned_count = 0
    else:
         message = f"Assessment '{db_assessment.name}' assigned to {len(target_student_ids)} student(s) in section '{db_section.name}'."
         assigned_count = len(target_student_ids)


    # 7. Log the Assignment Activity
    log_activity(
        db=db,
        user_id=current_user.id,
        action='ASSESSMENT_ASSIGNED_TO_SECTION',
        details=f"User '{current_user.username}' assigned assessment '{db_assessment.name}' (ID: {assessment_id}) to {assignment_target_desc} in section '{db_section.name}' (ID: {section_id}). Target count: {assigned_count}.",
        target_entity='Assessment',
        target_entity_id=assessment_id
        # Consider adding section_id or grade_id to target details if needed, but the main target is the assessment
    )

    # 8. Return Success Response
    return schemas.AssignmentResponse(
        message=message,
        assessment_id=assessment_id,
        section_id=section_id,
        assigned_student_count=assigned_count,
        assigned_student_ids=target_student_ids
    )
# --- END NEW ENDPOINT ---
