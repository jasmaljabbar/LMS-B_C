# backend/routes/assignment_samples.py
import os
import logging
# import json # No longer needed here
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
# --- ADD selectinload ---
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
import uuid # Added import for uuid
from pathlib import Path
from datetime import datetime
# from pydantic import ValidationError # No longer needed here

# --- Remove Vertex AI Imports ---
# try: ... except ImportError: ... (Removed)

# --- Import the analysis service ---
from backend.services.analysis_service import analyze_pdf_for_questions # <-- Corrected import

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user
from backend.logger_utils import log_activity
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/assignment-samples", tags=["Assignment Samples"])
logger = logging.getLogger(__name__)

# --- GCS Configuration ---
# GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
# --- Remove Vertex AI Config Vars (they are in the service now) ---
# client = None
bucket = None
# if GCS_BUCKET_NAME:
#     try:
#         client = storage.Client()
#         if client:
#             bucket = client.get_bucket(GCS_BUCKET_NAME)
#             logger.info(f"Successfully connected to GCS bucket: {GCS_BUCKET_NAME}")
#         else:
#             logger.error(f"Failed to initialize Google Cloud Storage client or get bucket '{GCS_BUCKET_NAME}' using ADC", exc_info=True)
#             bucket = None
#     except Exception as e:
#         logger.error(
#             f"Failed to initialize Google Cloud Storage client or get bucket '{GCS_BUCKET_NAME}' using ADC: {e}",
#             exc_info=True)
#         client = None
#         bucket = None
# else:
#     logger.warning("GCS_BUCKET_NAME not set in environment. GCS operations will be disabled.")
# --- Remove Vertex AI Initialization block ---


# --- GCS Helpers ---
# async def _upload_assignment_pdf_to_gcs(file: UploadFile, assignment_id: int) -> tuple[str, str, int]:
#     """Uploads an assignment PDF to GCS and returns the public HTTPS URL, GS URI, and size."""
#     if not bucket:
#         logger.error("GCS bucket is not available. Cannot upload file.")
#         raise HTTPException(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             detail="File storage service is unavailable.",
#         )
#     try:
#         if file.content_type != "application/pdf":
#             raise HTTPException(status_code=400, detail="Invalid file type. Only PDF is allowed.")
#         blob_name = f"assignments_pdfs/{assignment_id}.pdf"
#         blob = bucket.blob(blob_name)
#         contents = await file.read()
#         blob.upload_from_string(contents, content_type=file.content_type)
#         https_url = blob.public_url
#         gs_url = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
#         file_size = len(contents)
#         logger.info(f"Successfully uploaded assignment PDF {assignment_id} to GCS. HTTPS: {https_url}, GS: {gs_url}")
#         return https_url, gs_url, file_size
#     except HTTPException as http_exc:
#         raise http_exc
#     except Exception as e:
#         logger.error(f"Error uploading assignment PDF {assignment_id} to GCS: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error uploading assignment PDF to GCS: {str(e)}",
#         )


# Configuration for file storage
UPLOAD_DIR = Path("assignment_uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

async def _upload_assignment_pdf_to_mysql(file: UploadFile, assignment_id: int) -> tuple[str, str, int]:
    """Uploads an assignment PDF to MySQL/hybrid storage and returns access URL, storage path, and size."""
    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF is allowed.")

    db: Session = next(get_db())
    try:
        contents = await file.read()
        file_size = len(contents)
        file_name = f"{assignment_id}.pdf"
        
        # Hybrid approach: Store file on disk and metadata in DB
        file_path = UPLOAD_DIR / file_name
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Create database record
        db_file = models.UserFile(
            user_id=0,  # Or set to the appropriate user ID
            filename=file_name,
            content_type=file.content_type,
            file_path=str(file_path),  # Store path to file
            file_size=file_size,
            created_at=datetime.utcnow()
        )
        
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        
        # Generate URLs similar to GCS interface
        https_url = f"/api/assignments/{db_file.id}/pdf"  # Download endpoint
        storage_path = f"mysql://assignments/{db_file.id}"  # Conceptual storage location
        
        logger.info(f"Successfully uploaded assignment PDF {assignment_id}. Size: {file_size} bytes")
        return https_url, storage_path, file_size
        
    except Exception as e:
        # Clean up file if it was partially written
        if 'file_path' in locals() and file_path.exists():
            try:
                file_path.unlink()
            except:
                pass
        db.rollback()
        logger.error(f"Error uploading assignment PDF {assignment_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading assignment PDF"
        )
    finally:
        db.close()



def _delete_assignment_pdf_from_gcs(assignment_id: int):
    """Deletes an assignment PDF from GCS."""
    if not bucket:
        logger.warning("GCS bucket is not available. Skipping GCS deletion.")
        return False
    try:
        blob_name = f"assignments_pdfs/{assignment_id}.pdf"
        blob = bucket.blob(blob_name)
        if blob.exists():
            blob.delete()
            logger.info(f"Successfully deleted assignment PDF {assignment_id} from GCS.")
            return True
        else:
            logger.warning(f"Assignment PDF {assignment_id} not found in GCS for deletion.")
            return False
    except Exception as e:
        logger.error(f"Error deleting assignment PDF {assignment_id} from GCS: {e}", exc_info=True)
        return False


# --- CRUD Endpoints ---

@router.post("/", response_model=schemas.AssignmentSampleInfo, status_code=status.HTTP_201_CREATED)
async def create_assignment_sample(
    name: str = Form(...),
    subject_id: int = Form(...),
    description: Optional[str] = Form(None),
    pdf_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Creates a new assignment sample, uploads the PDF to GCS, storing both HTTPS and GS URLs.
    Requires Teacher or Admin role.
    """
    if current_user.user_type not in ["Teacher", "Admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Teachers or Admins can create assignment samples.")
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail=f"Subject with ID {subject_id} not found.")
    db_assignment: Optional[models.AssignmentSample] = None
    assignment_id_generated: Optional[int] = None
    db_https_url: Optional[models.URL] = None
    db_gs_url: Optional[models.URL] = None
    try:
        db_assignment = models.AssignmentSample(
            name=name, description=description, subject_id=subject_id,
            created_by_user_id=current_user.id, file_size=None
        )
        db.add(db_assignment); db.flush()
        if not db_assignment.id: raise Exception("Failed ID gen")
        assignment_id_generated = db_assignment.id
        https_url_str, gs_url_str, file_size = await _upload_assignment_pdf_to_mysql(pdf_file, assignment_id_generated)
        db_assignment.file_size = file_size
        db_https_url = models.URL(url=https_url_str, url_type=schemas.UrlTypeEnum.HTTPS.value)
        db_gs_url = models.URL(url=gs_url_str, url_type=schemas.UrlTypeEnum.GS.value)
        db.add_all([db_https_url, db_gs_url]); db.flush()
        if not db_https_url.id or not db_gs_url.id: raise Exception("Failed URL ID gen")
        db_assignment.urls.append(db_https_url)
        db_assignment.urls.append(db_gs_url)
        db.commit(); db.refresh(db_assignment)
        db.refresh(db_assignment, attribute_names=['urls', 'creator'])
        log_activity(db=db, user_id=current_user.id, action='ASSIGNMENT_SAMPLE_CREATED',
                     details=f"User '{current_user.username}' created assignment sample '{name}' (ID: {db_assignment.id}) for Subject ID {subject_id}.",
                     target_entity='AssignmentSample', target_entity_id=db_assignment.id)
        return db_assignment
    except IntegrityError as e:
        db.rollback();
        if assignment_id_generated: _delete_assignment_pdf_from_gcs(assignment_id_generated)
        logger.error(f"Integrity error creating assignment sample: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Database constraint violation.")
    except HTTPException as http_exc:
        db.rollback(); raise http_exc
    except Exception as e:
        db.rollback();
        if assignment_id_generated: _delete_assignment_pdf_from_gcs(assignment_id_generated)
        logger.error(f"Unexpected error creating assignment sample: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")

@router.get("/", response_model=List[schemas.AssignmentSampleInfo])
def read_assignment_samples(
    subject_id: Optional[int] = Query(None, description="Filter by Subject ID"),
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Retrieves a list of assignment samples, optionally filtered by subject.
    """
    query = db.query(models.AssignmentSample).options(
        selectinload(models.AssignmentSample.urls),
        joinedload(models.AssignmentSample.creator).load_only(models.User.username)
    )
    if subject_id:
        subject = db.query(models.Subject.id).filter(models.Subject.id == subject_id).first()
        if not subject: raise HTTPException(status_code=404, detail=f"Subject with ID {subject_id} not found.")
        query = query.filter(models.AssignmentSample.subject_id == subject_id)
    assignments = query.order_by(models.AssignmentSample.created_at.desc()).offset(skip).limit(limit).all()
    return assignments

@router.get("/{assignment_id}", response_model=schemas.AssignmentSampleInfo)
def read_assignment_sample(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Retrieves a specific assignment sample by ID.
    """
    assignment = db.query(models.AssignmentSample).options(
        selectinload(models.AssignmentSample.urls),
        joinedload(models.AssignmentSample.creator).load_only(models.User.username)
    ).filter(models.AssignmentSample.id == assignment_id).first()
    if not assignment: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment sample not found.")
    return assignment

@router.get("/urls/https", response_model=List[str])
def get_assignment_sample_https_urls_by_subject(
    subject_id: int = Query(..., description="ID of the subject to filter by"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Retrieves a list of HTTPS URLs for all assignment samples associated with a specific subject.
    """
    subject = db.query(models.Subject.id).filter(models.Subject.id == subject_id).first()
    if not subject: raise HTTPException(status_code=404, detail=f"Subject with ID {subject_id} not found.")
    assignments = db.query(models.AssignmentSample).options(selectinload(models.AssignmentSample.urls)).filter(models.AssignmentSample.subject_id == subject_id).all()
    https_urls: List[str] = []
    for assignment in assignments:
        for url_obj in assignment.urls:
            if url_obj.url_type == schemas.UrlTypeEnum.HTTPS.value:
                https_urls.append(url_obj.url); break
    return https_urls

@router.put("/{assignment_id}", response_model=schemas.AssignmentSampleInfo)
async def update_assignment_sample(
    assignment_id: int,
    name: Optional[str] = Form(None),
    subject_id: Optional[int] = Form(None),
    description: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Updates an assignment sample. Allows updating metadata and optionally replacing the PDF file (updates both URLs).
    Requires creator or Admin role.
    """
    db_assignment = db.query(models.AssignmentSample).options(
         selectinload(models.AssignmentSample.urls),
         joinedload(models.AssignmentSample.creator)
    ).filter(models.AssignmentSample.id == assignment_id).first()
    if not db_assignment: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment sample not found.")
    is_admin = current_user.user_type == "Admin"; is_creator = db_assignment.creator and db_assignment.created_by_user_id == current_user.id
    if not (is_admin or is_creator): raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    updated_fields = []; original_name = db_assignment.name
    if name is not None and db_assignment.name != name: db_assignment.name = name; updated_fields.append("name")
    if description is not None and db_assignment.description != description: db_assignment.description = description; updated_fields.append("description")
    if subject_id is not None and db_assignment.subject_id != subject_id:
        subject = db.query(models.Subject.id).filter(models.Subject.id == subject_id).first()
        if not subject: raise HTTPException(status_code=404, detail=f"Subject with ID {subject_id} not found.")
        db_assignment.subject_id = subject_id; updated_fields.append("subject_id")
    old_urls_to_delete = list(db_assignment.urls)
    if pdf_file:
        try:
            new_https_url, new_gs_url, new_file_size = await _upload_assignment_pdf_to_mysql(pdf_file, assignment_id)
            updated_fields.append("file"); db_assignment.file_size = new_file_size
            db_https_url_new = models.URL(url=new_https_url, url_type=schemas.UrlTypeEnum.HTTPS.value)
            db_gs_url_new = models.URL(url=new_gs_url, url_type=schemas.UrlTypeEnum.GS.value)
            db.add_all([db_https_url_new, db_gs_url_new]); db.flush()
            if not db_https_url_new.id or not db_gs_url_new.id: raise Exception("Failed new URL ID gen")
            db_assignment.urls.clear(); db.flush()
            db_assignment.urls.append(db_https_url_new); db_assignment.urls.append(db_gs_url_new)
            updated_fields.append("urls")
        except HTTPException as http_exc: db.rollback(); raise http_exc
        except Exception as e:
            db.rollback(); logger.error(f"Unexpected error during file update for assignment sample {assignment_id}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Unexpected error during file update.")
    else: old_urls_to_delete = []
    if not updated_fields:
        logger.info(f"No updates for assignment sample {assignment_id}."); db.refresh(db_assignment, attribute_names=['urls', 'creator']); return db_assignment
    try:
        db.commit()
        if old_urls_to_delete:
            url_ids_to_delete = [url.id for url in old_urls_to_delete]
            logger.info(f"Attempting delete old URLs: {url_ids_to_delete}")
            urls_in_session = db.query(models.URL).filter(models.URL.id.in_(url_ids_to_delete)).all()
            if urls_in_session:
                for old_url in urls_in_session: db.delete(old_url)
                try: db.commit(); logger.info(f"Deleted old URLs: {url_ids_to_delete}")
                except Exception as del_e: db.rollback(); logger.error(f"Failed delete old URLs {url_ids_to_delete}: {del_e}", exc_info=True)
        db.refresh(db_assignment); db.refresh(db_assignment, attribute_names=['urls', 'creator'])
        log_activity(db=db, user_id=current_user.id, action='ASSIGNMENT_SAMPLE_UPDATED',
                     details=f"User '{current_user.username}' updated sample '{db_assignment.name}' (ID: {assignment_id}). Fields: {', '.join(updated_fields)}.",
                     target_entity='AssignmentSample', target_entity_id=assignment_id)
        return db_assignment
    except IntegrityError as e:
        db.rollback(); logger.error(f"Integrity error updating sample {assignment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="DB constraint violation during update.")
    except Exception as e:
        db.rollback(); logger.error(f"Unexpected error committing sample update {assignment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Unexpected error during update.")

@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment_sample(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Deletes an assignment sample, its associated URL entries via cascade, and the file from GCS.
    Requires creator or Admin role.
    """
    db_assignment = db.query(models.AssignmentSample).options(selectinload(models.AssignmentSample.urls), joinedload(models.AssignmentSample.creator)).filter(models.AssignmentSample.id == assignment_id).first()
    if not db_assignment: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment sample not found.")
    is_admin = current_user.user_type == "Admin"; is_creator = db_assignment.creator and db_assignment.created_by_user_id == current_user.id
    if not (is_admin or is_creator): raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    url_ids_to_delete = [url.id for url in db_assignment.urls]
    assignment_name_deleted = db_assignment.name
    try:
        db.delete(db_assignment); db.commit()
        logger.info(f"Deleted AssignmentSample {assignment_id} and associated URLs ({url_ids_to_delete}) via cascade.")
        _delete_assignment_pdf_from_gcs(assignment_id)
        log_activity(db=db, user_id=current_user.id, action='ASSIGNMENT_SAMPLE_DELETED',
                     details=f"User '{current_user.username}' deleted assignment sample '{assignment_name_deleted}' (ID: {assignment_id}).",
                     target_entity='AssignmentSample', target_entity_id=assignment_id)
        return None
    except Exception as e:
        db.rollback(); logger.error(f"Error during deletion process for sample {assignment_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to complete assignment sample deletion.")


# --- ANALYSIS ENDPOINT ---
@router.post("/{assignment_id}/analyze", response_model=schemas.QuestionAnalysisResponse)
async def analyze_assignment_sample(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Analyzes an assignment sample PDF using Gemini to identify question types and counts.
    Requires Vertex AI to be initialized and appropriate permissions.
    """
    if current_user.user_type not in ["Teacher", "Admin"]:
         raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to analyze assignment samples.")

    assignment = db.query(models.AssignmentSample).options(
        selectinload(models.AssignmentSample.urls)
    ).filter(models.AssignmentSample.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment sample not found.")

    gs_url = None
    for url_obj in assignment.urls:
        if url_obj.url_type == schemas.UrlTypeEnum.GS.value:
            gs_url = url_obj.url
            break
    if not gs_url:
        logger.error(f"No GS URL found for assignment sample {assignment_id}.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="GS URL for the assignment sample PDF not found.")

    logger.info(f"Analyzing assignment sample {assignment_id} using GS URL: {gs_url}")

    try:
        # Call the analysis service
        validated_response = await analyze_pdf_for_questions(
            gs_url=gs_url,
            user_id=current_user.id,
            action="analyze_assignment_sample",
            session_id=str(uuid.uuid4())
        )

        log_activity(
            db=db, user_id=current_user.id, action='ASSIGNMENT_SAMPLE_ANALYZED',
            details=f"User '{current_user.username}' triggered AI analysis for assignment sample '{assignment.name}' (ID: {assignment_id}). Result: {validated_response.dict()}",
            target_entity='AssignmentSample', target_entity_id=assignment_id
        )
        return validated_response
    except HTTPException as ai_exc:
        logger.error(f"AI service failed for assignment {assignment_id}: {ai_exc.detail}")
        raise ai_exc
    except Exception as e:
         logger.error(f"Unexpected error calling analysis service for assignment {assignment_id}: {e}", exc_info=True)
         raise HTTPException(status_code=500, detail="An unexpected error occurred during analysis.")
