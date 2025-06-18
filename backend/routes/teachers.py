# backend/routes/teachers.py
import json
import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload # Added joinedload
from typing import List, Optional

from backend import models, schemas, utils
from backend.database import get_db , SessionLocal
from backend.dependencies import get_current_user # Keep authentication
from google.cloud import storage
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teachers", tags=["teachers"])

# Initialize Google Cloud Storage client
# client = storage.Client()
# bucket_name = os.getenv("GCS_BUCKET_NAME")
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


@router.post("/", response_model=schemas.TeacherInfo, status_code=status.HTTP_201_CREATED)
async def create_teacher(
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    grade_ids: str = Form(...),  # Accept grade IDs
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
    photo: UploadFile = File(None),  # Make photo optional
):
    """Creates a new teacher (requires authentication)."""
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

     # Fetch grades to assign
    grade_ids_list = [int(id.strip()) for id in grade_ids.split(',') if id.strip()]
    grades = db.query(models.Grade).filter(models.Grade.id.in_(grade_ids_list)).all()
    if not grades:
        raise HTTPException(status_code=404, detail="No valid grades found")

    # Create the user
    db_user = models.User(
        username=username,
        password_hash=hashed_password,
        user_type="Teacher", # Still create as Teacher type
        email=email,
    )
    db.add(db_user)
    # Use flush to get ID for GCS and Teacher profile creation before final commit
    db.flush()

    # Upload photo to GCS if provided
    photo_url = None
    if photo:
        try:
            photo_url = await upload_to_mysql(photo, db_user.id)
            db_user.photo = photo_url # Add photo URL to user object
        except HTTPException as e:
            db.rollback()
            raise e

    # Create the teacher profile
    db_teacher = models.Teacher(name=name, user_id=db_user.id, grades=grades)
    db.add(db_teacher)
    print("Grades fetched:", grades)
    print("db_teacher fetched:", db_teacher)


    try:
        db.commit() # Commit user (with potential photo update) and teacher together
        db.refresh(db_user)
        db.refresh(db_teacher)
        # Return based on TeacherInfo schema
        return schemas.TeacherInfo(id=db_teacher.id, name=db_teacher.name, user_id=db_teacher.user_id, photo=db_user.photo)
    except Exception as e:
        db.rollback()
        # GCS cleanup?
        logger.error(f"Failed to commit teacher creation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create teacher: {e}")


@router.get("/{teacher_id}", response_model=schemas.TeacherDetails)
def read_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves a teacher by ID."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_teacher = db.query(models.Teacher).options(
        joinedload(models.Teacher.user) # Eager load user details
    ).filter(models.Teacher.id == teacher_id).first()

    if db_teacher is None or db_teacher.user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher or associated user not found")

    # Use from_orm for nested schemas
    return db_teacher # Pydantic v2+ handles nested ORM


@router.get("/", response_model=List[schemas.TeacherDetails])
def read_teachers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves all teachers."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_teachers = db.query(models.Teacher).options(
        joinedload(models.Teacher.user) # Eager load user details
    ).offset(skip).limit(limit).all()

    # Use from_orm for nested schemas
    return db_teachers # Pydantic v2+ handles list of ORM

@router.get("/my-grades/{teacher_id}", response_model=List[schemas.GradeOut])
def get_teacher_grades(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get grades assigned to a specific teacher"""
    # Optional: Add authorization check if needed
    # if current_user.user_type != "Admin" and current_user.id != teacher_id:
    #     raise HTTPException(status_code=403, detail="Not authorized")

    # Get the teacher with grades using the relationship
    teacher = db.query(models.Teacher)\
        .options(joinedload(models.Teacher.grades))\
        .filter(models.Teacher.id == teacher_id)\
        .first()

    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Debug print to check what's being returned
    print(f"Grades for teacher {teacher_id}: {[g.id for g in teacher.grades]}")

    return teacher.grades


@router.put("/{teacher_id}", response_model=schemas.TeacherInfo)
async def update_teacher(
    teacher_id: int,
    name: str = Form(...),
    username: str = Form(...),
    email: str = Form(...),
    password: Optional[str] = Form(None), # Make password optional
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
    photo: UploadFile = File(None),
):
    """Updates a teacher by ID."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_teacher = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if db_teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")

    db_user = db.query(models.User).filter(models.User.id == db_teacher.user_id).first()
    if db_user is None:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated user not found")

    # Conflict checks?
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
            raise e

    # Hash the password ONLY if provided
    if password:
        hashed_password = utils.hash_password(password)
        db_user.password_hash = hashed_password

    # Update other user fields
    db_user.username = username
    db_user.email = email
    # user_type remains Teacher

    # Update teacher name
    db_teacher.name = name

    try:
        db.commit() # Commit changes to both User and Teacher
        db.refresh(db_teacher)
        db.refresh(db_user)
        # Return based on TeacherInfo schema
        return schemas.TeacherInfo(id=db_teacher.id, name=db_teacher.name, user_id=db_teacher.user_id, photo=db_user.photo)
    except Exception as e:
        db.rollback()
        # GCS cleanup?
        logger.error(f"Failed to commit teacher update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update teacher: {e}")


@router.post("/{teacher_id}/photo")
async def update_teacher_photo(
    teacher_id: int,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Updates a teacher's profile photo."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_teacher = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if db_teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")

    db_user = db.query(models.User).filter(models.User.id == db_teacher.user_id).first()
    if db_user is None:
         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated user not found")

    try:
        photo_url = await upload_to_mysql(photo, db_user.id)  # Uploads and overwrites.
        db_user.photo = photo_url
        db.commit()
        db.refresh(db_user)
        return {"message": "Teacher photo updated successfully", "photo_url": photo_url}
    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit teacher photo update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update teacher photo: {e}")


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teacher(
    teacher_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Deletes a teacher by ID."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_teacher = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if db_teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")

    # Get the user_id associated with the teacher
    user_id = db_teacher.user_id
    photo_url_to_delete = None

    try:
        # Fetch user to get photo URL before deleting
        db_user = db.query(models.User).filter(models.User.id == user_id).first()
        if db_user:
            photo_url_to_delete = db_user.photo
            db.delete(db_user) # This should trigger cascade deletion
            db.commit()
            logger.info(f"Deleted User {user_id} and associated Teacher {teacher_id} by {current_user.username}")
        else:
             logger.warning(f"User {user_id} not found for Teacher {teacher_id}, attempting direct Teacher delete.")
             db.delete(db_teacher)
             db.commit()
             logger.info(f"Deleted Teacher {teacher_id} (user was missing) by {current_user.username}")

        # GCS Photo Cleanup
        if photo_url_to_delete and bucket:
           try:
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
        logger.error(f"Error deleting teacher {teacher_id} or associated user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete teacher or associated user: {e}")
