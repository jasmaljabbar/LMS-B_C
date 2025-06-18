# backend/routes/students.py
import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload, selectinload # Added selectinload here
from typing import List, Optional

# --- Import from sqlalchemy needed for the fix ---
from sqlalchemy import Row, func, over # Added Row, func, over

from backend import models, schemas, utils
from backend.database import get_db
from backend.dependencies import get_current_user # Keep authentication
from backend.logger_utils import log_activity # <--- IMPORT log_activity
from google.cloud import storage
from dotenv import load_dotenv
import logging # Import logging

load_dotenv()
logger = logging.getLogger(__name__) # Get logger

router = APIRouter(prefix="/students", tags=["students"])

# --- Helper function for admin check REMOVED ---
# def _verify_admin(current_user: models.User):
#     if current_user.user_type != "Admin":
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Access restricted to administrators."
#         )

# --- GCS Setup ---
# try:
#     client = storage.Client()
#     bucket_name = os.getenv("GCS_BUCKET_NAME")
#     bucket = client.get_bucket(bucket_name) if bucket_name else None
#     if not bucket:
#         logger.warning("GCS bucket not found or GCS_BUCKET_NAME not set. File uploads will fail.")
# except Exception as e:
#     logger.error(f"Failed to initialize Google Cloud Storage client: {e}", exc_info=True)
#     bucket = None

# async def upload_to_gcs(file: UploadFile, user_id: int):
#     """Uploads an image file to Google Cloud Storage, including user ID in filename."""
#     if not bucket:
#         logger.error("GCS bucket not available. Cannot upload file.")
#         raise HTTPException(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             detail="File storage service is unavailable.",
#         )
#     try:
#         # Basic sanitization of filename extension
#         parts = file.filename.split(".")
#         ext = parts[-1].lower() if len(parts) > 1 else "bin"
#         allowed_extensions = {"png", "jpg", "jpeg", "gif", "webp"} # Example allowed image extensions
#         if ext not in allowed_extensions:
#              raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}")

#         blob_name = f"users/{user_id}.{ext}"  # Filename with user ID and safe extension
#         blob = bucket.blob(blob_name)
#         contents = await file.read()
#         blob.upload_from_string(contents, content_type=file.content_type)
#         logger.info(f"Uploaded photo for user {user_id} to GCS: {blob.public_url}")
#         return blob.public_url  # Return the public URL
#     except HTTPException as http_exc: # Re-raise client errors
#         raise http_exc
#     except Exception as e:
#         logger.error(f"Error uploading photo for user {user_id} to GCS: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error uploading photo to GCS: {str(e)}",
#         )


# Allowed file extensions and their corresponding content types
ALLOWED_EXTENSIONS = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp"
}

async def upload_user_file(file: UploadFile, user_id: int) -> Optional[str]:
    """
    Uploads a user file to MySQL database with validation
    Returns: public URL for accessing the file
    """
    # File validation
    file_ext = file.filename.split(".")[-1].lower() if "." in file.filename else None
    if not file_ext or file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS.keys())}"
        )
    
    if file.content_type != ALLOWED_EXTENSIONS[file_ext]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content type doesn't match its extension"
        )

    db: Session = next(get_db())
    try:
        contents = await file.read()
        
        # Create database record
        db_file = models.UserFile(
            user_id=user_id,
            filename=file.filename,
            content_type=file.content_type,
            data=contents
        )
        
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        
        logger.info(f"Uploaded file for user {user_id}. File ID: {db_file.id}")
        return f"/api/files/{db_file.id}"  # Return the URL to access the file
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading file for user {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading file"
        )
    finally:
        db.close()


@router.post(
    "/", response_model=schemas.StudentDetails, status_code=status.HTTP_201_CREATED
)
async def create_student(
        name: str = Form(...),
        username: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        year: int = Form(...),
        sectionId: int = Form(...),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user), # Authentication check
        photo: UploadFile = File(None),
):
    """Creates a new student, associated user, and student year record."""
    # _verify_admin(current_user) # <-- CALL REMOVED

    # --- Input Validation and Conflict Checks ---
    if not name or not username or not email or not password:
         raise HTTPException(status_code=400, detail="Missing required fields.")

    # Check if section exists
    section_check = db.query(models.Section.id).filter(models.Section.id == sectionId).first()
    if not section_check:
        raise HTTPException(status_code=400, detail=f"Section with ID {sectionId} not found.")

    db_user_check = db.query(models.User.id).filter(models.User.username == username).first()
    if db_user_check:
        raise HTTPException(status_code=400, detail="Username already registered.")
    db_email_check = db.query(models.User.id).filter(models.User.email == email).first()
    if db_email_check:
        raise HTTPException(status_code=400, detail="Email already registered.")

    # --- Database Operations ---
    hashed_password = utils.hash_password(password)
    db_user: Optional[models.User] = None
    db_student: Optional[models.Student] = None
    gcs_photo_url: Optional[str] = None

    try:
        # Create the user
        db_user = models.User(
            username=username, password_hash=hashed_password, user_type="Student", email=email, is_active=True # Default to active
        )
        db.add(db_user)
        db.flush() # Get user ID

        # Upload photo *before* creating student profile (user ID is needed)
        if photo:
            gcs_photo_url = await upload_user_file(photo, db_user.id)
            db_user.photo = gcs_photo_url # Add URL to user object

        # Create the student profile
        db_student = models.Student(name=name, user_id=db_user.id)
        db.add(db_student)
        db.flush() # Get student ID

        # Create StudentYear entry
        db_student_year = models.StudentYear(studentId=db_student.id, year=year, sectionId=sectionId)
        db.add(db_student_year)

        # Commit the entire transaction
        db.commit()
        logger.info(f"Successfully created student '{name}' (ID: {db_student.id}) and user '{username}' (ID: {db_user.id}).")

        # --- Audit Logging (after successful commit) ---
        log_activity(
            db=db,
            user_id=current_user.id, # Logged in user performed the action
            action='STUDENT_CREATED',
            details=f"User '{current_user.username}' created student '{name}' (User ID: {db_user.id}, Student ID: {db_student.id}). Assigned to section {sectionId} for year {year}.",
            target_entity='Student',
            target_entity_id=db_student.id
        )

        # Refresh objects to get final state for the response
        db.refresh(db_user)
        db.refresh(db_student)
        db.refresh(db_student_year)

        # --- Prepare and Return Response ---
        # Re-fetch section with grade info for the response schema
        db_section = db.query(models.Section).options(joinedload(models.Section.grade)).filter(models.Section.id == sectionId).first()
        if not db_section: # Should not happen if initial check passed and no commit error
             logger.error(f"Critical error: Section {sectionId} disappeared after student creation transaction for student {db_student.id}.")
             raise HTTPException(status_code=500, detail="Internal server error: Could not retrieve section details.")

        user_details = schemas.UserDetails.from_orm(db_user)
        section_info = schemas.SectionInfo.from_orm(db_section)

        return schemas.StudentDetails(
            id=db_student.id, name=db_student.name, user=user_details, section=section_info, year=db_student_year.year
        )

    except HTTPException as http_exc:
        db.rollback() # Rollback on client errors too
        raise http_exc # Re-raise HTTP exceptions
    except Exception as e:
        db.rollback() # Rollback on any other error
        logger.error(f"Error creating student '{username}': {e}", exc_info=True)
        # Basic GCS cleanup attempt if photo was uploaded but DB failed
        if gcs_photo_url and db_user and db_user.id and bucket:
            try:
                # Need to reconstruct blob name used during upload
                parts = gcs_photo_url.split(f"users/{db_user.id}.")
                if len(parts) > 1:
                    ext_with_query = parts[-1] # May include query params if public_url was used incorrectly
                    ext = ext_with_query.split('?')[0] # Remove query params if present
                    blob_name = f"users/{db_user.id}.{ext}"
                    blob = bucket.blob(blob_name)
                    if blob.exists():
                        blob.delete()
                        logger.warning(f"Attempted cleanup of potentially orphaned GCS file: {blob_name}")
            except Exception as cleanup_e:
                logger.error(f"Failed during GCS cleanup attempt for user {db_user.id}: {cleanup_e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during student creation."
        )


@router.get("/{student_id}", response_model=schemas.StudentDetails)
def read_student(
        student_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves a specific student's details by their student ID."""
    # _verify_admin(current_user) # <-- CALL REMOVED

    db_student = db.query(models.Student).options(
        joinedload(models.Student.user) # Eager load the associated User
    ).filter(models.Student.id == student_id).first()

    if not db_student or not db_student.user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found"
        )

    # Fetch the latest student year record for this student
    db_student_year = db.query(models.StudentYear).options(
        joinedload(models.StudentYear.section).joinedload(models.Section.grade) # Eager load section and grade
    ).filter(models.StudentYear.studentId == student_id).order_by(models.StudentYear.year.desc()).first()

    if not db_student_year or not db_student_year.section:
         logger.warning(f"StudentYear or Section info missing for student {student_id}")
         # Return placeholder or raise error - returning placeholder for robustness
         section_info = schemas.SectionInfo(id=-1, name="N/A", grade_id=-1)
         year = -1
    else:
        section_info = schemas.SectionInfo.from_orm(db_student_year.section)
        year = db_student_year.year

    user_details = schemas.UserDetails.from_orm(db_student.user)

    return schemas.StudentDetails(
        id=db_student.id,
        name=db_student.name,
        user=user_details,
        section=section_info,
        year=year
    )


@router.get("/", response_model=List[schemas.StudentDetails])
def read_students(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves a list of students with their details."""
    # _verify_admin(current_user) # <-- CALL REMOVED

    # Query students with their associated user data
    db_students = db.query(models.Student).options(
        joinedload(models.Student.user)
    ).order_by(models.Student.name).offset(skip).limit(limit).all()

    if not db_students:
        return []

    # Get all relevant student IDs for efficient StudentYear lookup
    student_ids = [s.id for s in db_students]

    # Fetch the latest StudentYear record for each student in the list
    subq = db.query(
        models.StudentYear,
        func.row_number().over(
            partition_by=models.StudentYear.studentId,
            order_by=models.StudentYear.year.desc()
        ).label('rn')
    ).filter(models.StudentYear.studentId.in_(student_ids)).subquery()

    latest_student_years_query = db.query(models.StudentYear).join(
        subq, models.StudentYear.studentId == subq.c.studentId
    ).filter(
        subq.c.rn == 1
    ).options(
        joinedload(models.StudentYear.section).joinedload(models.Section.grade)
    ).all()

    # Create a map for quick lookup
    student_year_map = {sy.studentId: sy for sy in latest_student_years_query}

    # Build the response list
    student_details_list = []
    for db_student in db_students:
        if not db_student.user: # Skip if user data somehow missing
            logger.warning(f"Skipping student {db_student.id} due to missing user data.")
            continue

        user_details = schemas.UserDetails.from_orm(db_student.user)
        latest_sy = student_year_map.get(db_student.id)

        if latest_sy and latest_sy.section:
            section_info = schemas.SectionInfo.from_orm(latest_sy.section)
            year = latest_sy.year
        else:
            section_info = schemas.SectionInfo(id=-1, name="N/A", grade_id=-1) # Placeholder
            year = -1 # Placeholder

        student_details_list.append(schemas.StudentDetails(
            id=db_student.id,
            name=db_student.name,
            user=user_details,
            section=section_info,
            year=year
        ))

    return student_details_list


@router.put("/{student_id}", response_model=schemas.StudentDetails)
async def update_student(
        student_id: int,
        name: str = Form(...),
        username: str = Form(...),
        email: str = Form(...),
        year: int = Form(...), # Current/Target Year for section assignment
        sectionId: int = Form(...),
        password: Optional[str] = Form(None), # Optional: only provide if changing
        is_active: Optional[bool] = Form(None), # Optional: provide to change status
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user), # Authentication check
        photo: UploadFile = File(None), # Optional: provide to update photo
):
    """Updates a student's details, user info, and section assignment for a given year."""
    # _verify_admin(current_user) # <-- CALL REMOVED

    # Fetch student and associated user
    db_student = db.query(models.Student).options(
        joinedload(models.Student.user)
    ).filter(models.Student.id == student_id).first()

    if not db_student or not db_student.user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student or associated user not found."
        )

    db_user = db_student.user
    original_username = db_user.username # For logging changes

    # --- Input Validation and Conflict Checks ---
    # (Validation remains unchanged)
    if not name or not username or not email:
         raise HTTPException(status_code=400, detail="Missing required name, username, or email.")

    section_check = db.query(models.Section.id).filter(models.Section.id == sectionId).first()
    if not section_check:
        raise HTTPException(status_code=400, detail=f"Section with ID {sectionId} not found.")

    if username != db_user.username:
        existing_user = db.query(models.User.id).filter(models.User.username == username, models.User.id != db_user.id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken by another user.")

    if email != db_user.email:
        existing_email = db.query(models.User.id).filter(models.User.email == email, models.User.id != db_user.id).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already taken by another user.")
    # --- End Validation ---

    # --- Database Operations ---
    updated_fields = [] # Track changes for logging
    try:
        # Update student name
        if db_student.name != name:
            db_student.name = name
            updated_fields.append("name")

        # Update user fields
        if db_user.username != username:
            db_user.username = username
            updated_fields.append("username")
        if db_user.email != email:
            db_user.email = email
            updated_fields.append("email")
        if password: # Only update password if provided
            db_user.password_hash = utils.hash_password(password)
            updated_fields.append("password")
        if is_active is not None and db_user.is_active != is_active:
            db_user.is_active = is_active
            updated_fields.append("is_active")

        # Update photo if provided
        gcs_photo_url = None
        if photo:
            gcs_photo_url = await upload_user_file(photo, db_user.id)
            if db_user.photo != gcs_photo_url:
                db_user.photo = gcs_photo_url
                updated_fields.append("photo")

        # Find or create StudentYear record for the specified year
        db_student_year = db.query(models.StudentYear).filter(
            models.StudentYear.studentId == student_id,
            models.StudentYear.year == year
        ).first()

        if db_student_year:
            if db_student_year.sectionId != sectionId:
                db_student_year.sectionId = sectionId
                updated_fields.append(f"sectionId (for year {year})")
        else:
            # Create if it doesn't exist for that year
            db_student_year = models.StudentYear(studentId=student_id, year=year, sectionId=sectionId)
            db.add(db_student_year)
            updated_fields.append(f"sectionId (created for year {year})")

        if not updated_fields:
             logger.info(f"No changes detected for student {student_id}. Returning current state.")
        else:
            db.commit()
            logger.info(f"Successfully updated student {student_id}. Changed fields: {', '.join(updated_fields)}")

            # --- Audit Logging ---
            log_activity(
                db=db,
                user_id=current_user.id, # Logged in user performed the action
                action='STUDENT_UPDATED',
                details=f"User '{current_user.username}' updated student '{name}' (ID: {student_id}). Fields changed: {', '.join(updated_fields)}.",
                target_entity='Student',
                target_entity_id=student_id
            )

        # Refresh objects needed for the response
        db.refresh(db_student)
        db.refresh(db_user)
        if db_student_year: db.refresh(db_student_year) # Refresh if updated/created

        # --- Prepare and Return Response ---
        db_section = db.query(models.Section).options(joinedload(models.Section.grade)).filter(models.Section.id == sectionId).first()
        if not db_section: # Should not happen if validation passed
             logger.error(f"Critical error: Section {sectionId} not found after student update transaction for student {student_id}.")
             raise HTTPException(status_code=500, detail="Internal server error: Could not retrieve section details for response.")

        user_details = schemas.UserDetails.from_orm(db_user)
        section_info = schemas.SectionInfo.from_orm(db_section)

        return schemas.StudentDetails(
            id=db_student.id, name=db_student.name, user=user_details, section=section_info, year=year
        )

    except HTTPException as http_exc:
        db.rollback()
        raise http_exc
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating student {student_id}: {e}", exc_info=True)
        # Potential GCS cleanup needed if photo upload succeeded but DB commit failed
        raise HTTPException(status_code=500, detail="An unexpected error occurred during student update.")


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
        student_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user), # Authentication check
):
    """
    Deletes a student and their associated user account.
    Associated StudentYear records should be deleted via DB cascade.
    Associated StudentAssessmentScores should be deleted via DB cascade.
    """
    # _verify_admin(current_user) # <-- CALL REMOVED

    # Fetch student and user info *before* deleting for logging
    db_student = db.query(models.Student).options(
        joinedload(models.Student.user) # Load user data too
    ).filter(models.Student.id == student_id).first()

    if not db_student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found."
        )

    # Store info for logging before deletion
    student_name_deleted = db_student.name
    user_id_deleted = db_student.user_id
    username_deleted = db_student.user.username if db_student.user else "N/A"

    try:
        # Deleting the User should cascade delete the Student profile, etc.
        db_user_to_delete = db.query(models.User).filter(models.User.id == user_id_deleted).first()

        if db_user_to_delete:
            db.delete(db_user_to_delete)
            db.commit()
            logger.info(f"Successfully deleted user {user_id_deleted} ('{username_deleted}') and associated student data for student ID {student_id}.")

            # --- Audit Logging ---
            log_activity(
                db=db,
                user_id=current_user.id, # Logged in user performed the action
                action='STUDENT_DELETED',
                details=f"User '{current_user.username}' deleted student '{student_name_deleted}' (ID: {student_id}, User: {username_deleted}).",
                target_entity='Student',
                target_entity_id=student_id # Log the student ID that was deleted
            )
        else:
            # If user was somehow already deleted, try deleting student directly
            logger.warning(f"User {user_id_deleted} not found, attempting to delete student {student_id} directly.")
            db.delete(db_student)
            db.commit()
            # Log this unusual situation
            log_activity(
                db=db,
                user_id=current_user.id, # Logged in user performed the action
                action='STUDENT_DELETED_ORPHAN', # Different action code
                details=f"User '{current_user.username}' deleted student '{student_name_deleted}' (ID: {student_id}). Associated user (ID: {user_id_deleted}) was already missing.",
                target_entity='Student',
                target_entity_id=student_id
            )

        # GCS Photo Cleanup Placeholder
        # if db_user_to_delete and db_user_to_delete.photo and bucket:
        #    try:
        #        # Parse blob name from URL and delete
        #        ...
        #    except Exception as cleanup_e:
        #        logger.error(...)

        return None # Return None for 204 No Content

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting student {student_id} or associated user {user_id_deleted}: {e}", exc_info=True)
        # Check for specific DB constraint errors if cascade fails
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete student {student_id}.")


# === NEW ENDPOINT for Parent-Student Association ===

@router.get(
    "/{student_id}/parents",
    response_model=List[schemas.ParentInfo], # Using ParentInfo for listing
    summary="List Parents Associated with Student"
)
def list_parents_for_student(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves a list of parents associated with a specific student."""
    # Authorization: Check if the current user IS the student_id requesting, or is Admin/Teacher?
    # is_self = (current_user.user_type == "Student" and current_user.student and current_user.student.id == student_id)
    # is_admin_or_teacher = (current_user.user_type in ["Admin", "Teacher"])
    # if not (is_self or is_admin_or_teacher):
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this student's parents")


    db_student = db.query(models.Student).options(
        selectinload(models.Student.parents).joinedload(models.Parent.user) # Eager load parents and their user data
    ).filter(models.Student.id == student_id).first()

    if not db_student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student with ID {student_id} not found.")

    # Prepare response using ParentInfo schema (includes photo from User)
    parents_list = []
    for parent in db_student.parents:
        photo_url = parent.user.photo if parent.user else None
        parents_list.append(schemas.ParentInfo(
            id=parent.id,
            name=parent.name,
            user_id=parent.user_id,
            photo=photo_url
        ))

    return parents_list

# === END NEW ENDPOINT ===