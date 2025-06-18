# backend/routes/administrators.py
import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List

from backend import models, schemas, utils
from backend.database import get_db, SessionLocal
from backend.dependencies import get_current_user # Keep authentication
from google.cloud import storage
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

router = APIRouter(prefix="/administrators", tags=["administrators"])

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
        return {"message": "File uploaded successfully", "file_id": db_file.id}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )
    finally:
        db.close()



@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_administrator(
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
    photo: UploadFile = File(None),  # Make photo optional
):
    """Creates a new administrator (requires authentication)."""
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
        user_type="Admin", # Still create as Admin type
        email=email,
    )
    db.add(db_user)
    # Use flush to get ID before commit for GCS
    db.flush()

    # Upload photo to GCS if provided
    photo_url = None
    if photo:
        photo_url = await upload_to_mysql(photo, db_user.id)  # Pass user ID to GCS upload
        db_user.photo = photo_url

    # Commit user (with potential photo)
    db.commit()
    db.refresh(db_user)


    # Note: Response model isn't defined in schemas, returning dict
    return {"message": "Administrator created successfully", "photo_url": photo_url, "username": db_user.username, "email": db_user.email, "id": db_user.id}


@router.get("/{administrator_id}")
def read_administrator(
    administrator_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves an administrator by ID (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    # Still filter by user_type="Admin" to ensure we fetch an admin record
    db_user = db.query(models.User).filter(models.User.id == administrator_id, models.User.user_type == "Admin").first()
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found")

    # Note: Response model isn't defined in schemas, returning dict
    return {"id": db_user.id, "username": db_user.username, "email": db_user.email, "photo": db_user.photo}


@router.get("/")
def read_administrators(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves all administrators (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    # Still filter by user_type="Admin" to retrieve only admins
    db_users = db.query(models.User).filter(models.User.user_type == "Admin").offset(skip).limit(limit).all()

    # Note: Response model isn't defined in schemas, returning list of dicts
    return [{"id": user.id, "username": user.username, "email": user.email, "photo":user.photo} for user in db_users]


@router.put("/{administrator_id}")
async def update_administrator(
    administrator_id: int,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(None), # Make password optional for update
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
    photo: UploadFile = File(None),  # Make photo optional
):
    """Updates an administrator by ID (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # Original check prevented self-update AND required Admin role
    # if current_user.user_type != "Admin" or current_user.id == administrator_id:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL --- (Now allows self-update by any authenticated user)

    # Still filter by user_type="Admin" to ensure we update an admin record
    db_user = db.query(models.User).filter(models.User.id == administrator_id, models.User.user_type == "Admin").first()
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found")

    # Check if the new username is already taken
    if username != db_user.username:
        existing_user = db.query(models.User).filter(models.User.username == username).first()
        if existing_user and existing_user.id != administrator_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already registered")

    # Check if the new email is already taken
    if email != db_user.email:
        existing_email = db.query(models.User).filter(models.User.email == email).first()
        if existing_email and existing_email.id != administrator_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Upload new photo to GCS if provided
    if photo:
        photo_url = await upload_to_mysql(photo, db_user.id)  # Pass user ID to GCS upload
        db_user.photo = photo_url

    # Hash the password ONLY if provided
    if password:
        hashed_password = utils.hash_password(password)
        db_user.password_hash = hashed_password

    db_user.username = username
    db_user.email = email
    # Note: user_type remains "Admin"
    db.commit()
    db.refresh(db_user)


    # Note: Response model isn't defined in schemas, returning dict
    return {"message": "Administrator updated successfully", "photo_url": db_user.photo, "username": db_user.username, "email": db_user.email, "id": db_user.id}


@router.post("/{administrator_id}/photo")
async def update_administrator_photo(
    administrator_id: int,
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Updates an administrator's profile photo (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    # Still filter by user_type="Admin" to ensure we update an admin record
    db_user = db.query(models.User).filter(models.User.id == administrator_id, models.User.user_type == "Admin").first()
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found")

    photo_url = await upload_to_mysql(photo, db_user.id) #Uploads and overwrites.

    db_user.photo = photo_url
    db.commit()
    db.refresh(db_user)

    # Note: Response model isn't defined in schemas, returning dict
    return {"message": "Administrator photo updated successfully", "photo_url": photo_url}



@router.delete("/{administrator_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_administrator(
    administrator_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Deletes an administrator by ID (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    # Still filter by user_type="Admin" to ensure we delete an admin record
    db_user = db.query(models.User).filter(models.User.id == administrator_id, models.User.user_type == "Admin").first()
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found")

    user_id = db_user.id # Store ID for potential GCS cleanup if needed
    # GCS Photo Cleanup Placeholder
    # photo_url_to_delete = db_user.photo
    # ...

    db.delete(db_user)
    db.commit()

    # GCS Photo Cleanup (Actual)
    # if photo_url_to_delete and bucket:
    #    try:
    #       # parse blob name and delete
    #    except Exception as e:
    #        # log error
    # ...

    return None # Return None for 204
