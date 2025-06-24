# backend/routes/parents.py
import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
# --- MODIFIED IMPORT: Added selectinload ---
from sqlalchemy.orm import Session, joinedload, selectinload
from typing import List, Optional
# --- ADDED IMPORT ---
from sqlalchemy.exc import IntegrityError

from backend import models, schemas, utils
from backend.database import get_db, SessionLocal
from backend.dependencies import get_current_user # Keep authentication
# --- ADDED IMPORT ---
from backend.logger_utils import log_activity # Import log_activity
# --- END ADDED IMPORT ---
from google.cloud import storage
from dotenv import load_dotenv
import logging

from backend.gcs_client import get_gcs_client_and_bucket

client, bucket = get_gcs_client_and_bucket()


load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/parents", tags=["parents"])

# Initialize Google Cloud Storage client
# client = storage.Client()
bucket_name = os.getenv("GCS_BUCKET_NAME")
# bucket = client.get_bucket(bucket_name)



# async def upload_to_gcs(file: UploadFile, user_id: int):
#     """Uploads an image file to Google Cloud Storage, including user ID in filename."""
#     try:
#         file_extension = file.filename.split(".")[-1]  # Get the file extension
#         blob_name = f"users/{user_id}.{file_extension}"  # Filename with user ID
#         blob = bucket.blob(blob_name)
#         contents = await file.read()
#         blob.upload_from_string(contents, content_type=file.content_type)
#         return blob.public_url  # Return the public URL
#     except Exception as e:
#         logger.error(f"Error uploading photo for user {user_id} to GCS: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error uploading to GCS: {str(e)}",
#         )

async def upload_to_mysql(file: UploadFile, user_id: int):
    """Uploads a file to MySQL database"""
    db = SessionLocal()
    try:
        # Read file contents
        contents = await file.read()
        
        # Create new database record
        db_file = models.UserFile(
            user_id=user_id,
            filename=file.filename,
            content_type=file.content_type,
            data=contents
        )
        
        # Add to database
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        
        # Return some identifier (could be the ID or a success message)
        return str(db_file.id)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )
    finally:
        db.close()


@router.post("/", response_model=schemas.ParentInfo, status_code=status.HTTP_201_CREATED)
async def create_parent(
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
    photo: UploadFile = File(None),  # Make photo optional
):
    """Creates a new parent (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    # Check if username is already taken
    db_user = db.query(models.User).filter(models.User.username == username).first()
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    # Check if email is already taken
    db_email = db.query(models.User).filter(models.User.email == email).first()
    if db_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Hash the password
    hashed_password = utils.hash_password(password)

    # Create the user
    db_user = models.User(
        username=username,
        password_hash=hashed_password,
        user_type="Parent", # Still create as Parent type
        email=email,
    )
    db.add(db_user)
    # Use flush to get ID for GCS and Parent profile creation before final commit
    db.flush()

     # Upload photo to GCS if provided
    photo_url = None
    if photo:
        try:
            photo_url = await upload_to_mysql(photo, db_user.id)  # Pass user ID to GCS upload
            db_user.photo = photo_url # Add photo URL to user object before parent creation
        except HTTPException as e:
            db.rollback() # Rollback user creation if photo upload fails
            raise e # Re-raise GCS error

    # Create the parent profile
    db_parent = models.Parent(name=name, user_id=db_user.id)
    db.add(db_parent)

    try:
        db.commit() # Commit user (with potential photo update) and parent together
        db.refresh(db_user)
        db.refresh(db_parent)
        # Return based on ParentInfo schema
        return schemas.ParentInfo(id=db_parent.id, name=db_parent.name, user_id=db_parent.user_id, photo=db_user.photo)
    except Exception as e:
        db.rollback()
        # Attempt to clean up GCS photo if upload happened but DB commit failed
        if photo_url and bucket:
             try:
                 # Parse blob name from URL and delete
                 parts = photo_url.split(f"{bucket_name}/", 1)
                 if len(parts) > 1:
                     blob_name = parts[1].split('?')[0] # Remove query params
                     blob = bucket.blob(blob_name)
                     if blob.exists():
                         blob.delete()
                         logger.warning(f"Cleaned up orphaned GCS file on parent creation failure: {blob_name}")
             except Exception as cleanup_e:
                 logger.error(f"Failed GCS cleanup on parent creation failure: {cleanup_e}")
        logger.error(f"Failed to commit parent creation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create parent: {e}")


@router.get("/{parent_id}", response_model=schemas.ParentDetails)
def read_parent(
    parent_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves a parent by ID."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_parent = db.query(models.Parent).options(
        joinedload(models.Parent.user) # Eager load user details
    ).filter(models.Parent.id == parent_id).first()

    if db_parent is None or db_parent.user is None: # Check if parent or user exists
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent or associated user not found")

    # Use from_orm for nested schemas
    return db_parent # Pydantic v2+ handles nested ORM objects if configured


@router.get("/", response_model=List[schemas.ParentDetails])
def read_parents(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves all parents."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_parents = db.query(models.Parent).options(
        joinedload(models.Parent.user) # Eager load user details for each parent
    ).offset(skip).limit(limit).all()

    # Use from_orm for nested schemas
    return db_parents # Pydantic v2+ handles list of ORM objects


@router.put("/{parent_id}", response_model=schemas.ParentInfo)
async def update_parent(
    parent_id: int,
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: Optional[str] = Form(None), # Make password optional for update
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
    photo: UploadFile = File(None),
):
    """Updates a parent by ID."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_parent = db.query(models.Parent).filter(models.Parent.id == parent_id).first()
    if db_parent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent not found")

    db_user = db.query(models.User).filter(models.User.id == db_parent.user_id).first()
    if db_user is None:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated user not found")

    # Check username/email conflicts before proceeding
    if username != db_user.username:
        existing_user = db.query(models.User.id).filter(models.User.username == username, models.User.id != db_user.id).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already taken.")
    if email != db_user.email:
        existing_email = db.query(models.User.id).filter(models.User.email == email, models.User.id != db_user.id).first()
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already taken.")

    # Upload new photo to GCS if provided
    if photo:
        try:
            photo_url = await upload_to_mysql(photo, db_user.id)
            db_user.photo = photo_url
        except HTTPException as e:
            # No DB changes made yet, just re-raise
            raise e

    # Hash the password ONLY if provided
    if password:
        hashed_password = utils.hash_password(password)
        db_user.password_hash = hashed_password

    # Update other user fields
    db_user.username = username
    db_user.email = email
    # user_type remains Parent

    # Update parent name
    db_parent.name = name

    try:
        db.commit() # Commit changes to both User and Parent
        db.refresh(db_parent)
        db.refresh(db_user)
        # Return based on ParentInfo schema
        return schemas.ParentInfo(id=db_parent.id, name=db_parent.name, user_id=db_parent.user_id, photo=db_user.photo)
    except Exception as e:
        db.rollback()
        # Handle potential GCS cleanup if needed (if photo was uploaded but commit failed)
        logger.error(f"Failed to commit parent update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update parent: {e}")


@router.post("/{parent_id}/photo")
async def update_parent_photo(
    parent_id: int,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Updates a parent's profile photo."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_parent = db.query(models.Parent).filter(models.Parent.id == parent_id).first()
    if db_parent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent not found")

    db_user = db.query(models.User).filter(models.User.id == db_parent.user_id).first()
    if db_user is None:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated user not found")

    try:
        photo_url = await upload_to_mysql(photo, db_user.id) #Uploads and overwrites.
        db_user.photo = photo_url
        db.commit()
        db.refresh(db_user)
        return {"message": "Parent photo updated successfully", "photo_url": photo_url}
    except HTTPException as e:
        db.rollback() # Photo upload failed, no DB change needed
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit parent photo update: {e}", exc_info=True)
        # GCS cleanup might be needed if upload succeeded but commit failed (less likely here)
        raise HTTPException(status_code=500, detail=f"Failed to update parent photo: {e}")


@router.delete("/{parent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_parent(
    parent_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Deletes a parent by ID."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_parent = db.query(models.Parent).filter(models.Parent.id == parent_id).first()
    if db_parent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parent not found")

    # Get the user_id associated with the parent *before* deleting parent
    user_id = db_parent.user_id
    photo_url_to_delete = None

    try:
        # Fetch user to get photo URL before deleting
        db_user = db.query(models.User).filter(models.User.id == user_id).first()
        if db_user:
            photo_url_to_delete = db_user.photo
            db.delete(db_user) # This should trigger cascade deletion of Parent profile
            db.commit()
            logger.info(f"Deleted User {user_id} and associated Parent {parent_id} by {current_user.username}")
        else:
             # If user is already gone, try deleting parent directly
             logger.warning(f"User {user_id} not found for Parent {parent_id}, attempting direct Parent delete.")
             db.delete(db_parent)
             db.commit()
             logger.info(f"Deleted Parent {parent_id} (user was missing) by {current_user.username}")

        # GCS Photo Cleanup
        if photo_url_to_delete and bucket:
           try:
               # Parse blob name from URL and delete
               if photo_url_to_delete.startswith(f"https://storage.googleapis.com/{bucket_name}/"):
                   blob_name = photo_url_to_delete.split(f"{bucket_name}/", 1)[1].split('?')[0]
                   blob = bucket.blob(blob_name)
                   if blob.exists():
                       blob.delete()
                       logger.info(f"Deleted GCS photo for user {user_id}: {blob_name}")
           except Exception as cleanup_e:
               logger.error(f"Failed GCS cleanup for user {user_id}: {cleanup_e}")

        return None # Return None for 204

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting parent {parent_id} or associated user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete parent or associated user: {e}")


# === NEW ENDPOINTS for Parent-Student Association ===

@router.post(
    "/{parent_id}/students/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Associate Student with Parent"
)
def associate_student_with_parent(
    parent_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Associates a specific student with a specific parent."""
    # Authorization Check (Example: Only Admins can associate)
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Fetch parent and student, ensuring they exist
    db_parent = db.query(models.Parent).options(selectinload(models.Parent.children)).filter(models.Parent.id == parent_id).first()
    if not db_parent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Parent with ID {parent_id} not found.")

    db_student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not db_student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Student with ID {student_id} not found.")

    # Check if association already exists
    if db_student in db_parent.children:
        logger.warning(f"Association between Parent {parent_id} and Student {student_id} already exists.")
        # Return 204 indicating the desired state is achieved, or 409 Conflict
        return # Or raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Association already exists.")

    # Create association
    try:
        db_parent.children.append(db_student)
        db.commit()
        logger.info(f"Associated Student {student_id} with Parent {parent_id} by user {current_user.username}")

        # --- ADDED AUDIT LOG ---
        log_activity(
            db=db,
            user_id=current_user.id,
            action='PARENT_STUDENT_ASSOCIATED',
            details=f"User '{current_user.username}' associated Parent '{db_parent.name}' (ID: {parent_id}) with Student '{db_student.name}' (ID: {student_id}).",
            target_entity='Parent', # Or 'Student' or 'Association'
            target_entity_id=parent_id
        )
        # --- END ADDED AUDIT LOG ---

    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError associating Parent {parent_id} and Student {student_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error during association.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error associating Parent {parent_id} and Student {student_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not associate student with parent.")

    return None # Return None for 204 No Content


@router.delete(
    "/{parent_id}/students/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disassociate Student from Parent"
)
def disassociate_student_from_parent(
    parent_id: int,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Disassociates a specific student from a specific parent."""
    # Authorization Check (Example: Only Admins can disassociate)
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    db_parent = db.query(models.Parent).options(selectinload(models.Parent.children)).filter(models.Parent.id == parent_id).first()
    if not db_parent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Parent with ID {parent_id} not found.")

    # Find the student in the parent's children list
    student_to_remove = None
    student_name = "Unknown" # For logging
    for child in db_parent.children:
        if child.id == student_id:
            student_to_remove = child
            student_name = child.name # Get name for logging
            break

    if not student_to_remove:
        logger.warning(f"Association between Parent {parent_id} and Student {student_id} not found for deletion.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Association between parent and student not found.")

    parent_name = db_parent.name # Get name for logging

    try:
        db_parent.children.remove(student_to_remove)
        db.commit()
        logger.info(f"Disassociated Student {student_id} from Parent {parent_id} by user {current_user.username}")

        # --- ADDED AUDIT LOG ---
        log_activity(
            db=db,
            user_id=current_user.id,
            action='PARENT_STUDENT_DISASSOCIATED',
            details=f"User '{current_user.username}' disassociated Parent '{parent_name}' (ID: {parent_id}) from Student '{student_name}' (ID: {student_id}).",
            target_entity='Parent', # Or 'Student' or 'Association'
            target_entity_id=parent_id
        )
        # --- END ADDED AUDIT LOG ---

    except Exception as e:
        db.rollback()
        logger.error(f"Error disassociating Parent {parent_id} and Student {student_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not disassociate student from parent.")

    return None # Return None for 204


@router.get(
    "/{parent_id}/students",
    response_model=List[schemas.StudentInfo], # Using StudentInfo for listing
    summary="List Students Associated with Parent"
)
def list_students_for_parent(
    parent_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves a list of students associated with a specific parent."""
    # Authorization: Check if the current user IS the parent_id requesting, or is Admin
    # is_self = (current_user.user_type == "Parent" and current_user.parent and current_user.parent.id == parent_id)
    # is_admin = (current_user.user_type == "Admin")
    # if not (is_self or is_admin):
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this parent's students")

    db_parent = db.query(models.Parent).options(
        selectinload(models.Parent.children).joinedload(models.Student.user) # Eager load children and their user data
    ).filter(models.Parent.id == parent_id).first()

    if not db_parent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Parent with ID {parent_id} not found.")

    # Prepare response using StudentInfo schema (includes photo from User)
    students_list = []
    for student in db_parent.children:
        photo_url = student.user.photo if student.user else None
        students_list.append(schemas.StudentInfo(
            id=student.id,
            name=student.name,
            user_id=student.user_id,
            photo=photo_url
        ))

    return students_list

# === END NEW ENDPOINTS ===
