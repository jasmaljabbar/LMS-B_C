# backend/routes/images.py
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload # Added joinedload
from typing import List, Union, Optional # Added Optional
from sqlalchemy.exc import IntegrityError

from backend import models, schemas
from backend.database import get_db , SessionLocal
from backend.dependencies import get_current_user # Keep authentication
from google.cloud import storage
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/images", tags=["Images"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Google Cloud Storage client
# client = storage.Client()
bucket_name = os.getenv("GCS_BUCKET_NAME")
# bucket = client.get_bucket(bucket_name)



# async def upload_to_gcs(file: UploadFile, file_name: str):
#     """Uploads an image file to Google Cloud Storage."""
#     logger.info(f"upload_to_gcs called with file_name: {file_name}")
#     try:
#         blob = bucket.blob(file_name)
#         contents = await file.read()
#         blob.upload_from_string(contents, content_type=file.content_type)
#         logger.info(f"Uploaded {file.filename} to GCS as {file_name}")
#         return blob.public_url  # Return the public URL
#     except Exception as e:
#         logger.error(f"Error uploading image file {file_name} to GCS: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error uploading image to GCS: {str(e)}",
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



@router.post("/", response_model=schemas.ImageInfo, status_code=status.HTTP_201_CREATED)
async def create_image(
    name: str = Form(...),  # This is the image title
    pdf_id: int = Form(...),
    image_file: UploadFile = File(...),
    image_number: Optional[int] = Form(None), # Use Optional typing
    page_number: Optional[int] = Form(None),
    chapter_number: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Creates a new image entry with file upload."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type not in ["Admin", "Teacher"]:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
    #     )
    # --- END REMOVAL ---

    db_url: Optional[models.URL] = None
    gcs_file_name: Optional[str] = None
    url_id: Optional[int] = None

    # Upload file to GCS
    file_extension = image_file.filename.split(".")[-1] if image_file.filename and '.' in image_file.filename else 'jpg' # Default extension?
    # Make GCS filename more unique
    img_num_str = f"_img{image_number}" if image_number is not None else ""
    page_num_str = f"_pg{page_number}" if page_number is not None else ""
    gcs_file_name = f"images/pdf_{pdf_id}/{name.replace(' ', '_')}{img_num_str}{page_num_str}.{file_extension}"
    try:
        image_url = await upload_to_mysql(image_file, gcs_file_name)
    except HTTPException as e:
        raise e # Re-raise GCS errors
    except Exception as e:
        logger.error(f"Unhandled error during image upload GCS call: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to upload image file.")


    # Create URL entry in the database first
    try:
        # --- MODIFIED LINE: Changed url_type ---
        db_url = models.URL(url=image_url, url_type=schemas.UrlTypeEnum.HTTPS.value) # Use "https" from Enum value
        # --- END MODIFICATION ---
        db.add(db_url)
        db.flush() # Get url_id before creating image
        if not db_url.id:
             raise Exception("Failed to generate URL ID after flush.")
        url_id = db_url.id
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating URL for image: {str(e)}")
        # GCS cleanup needed here for orphaned file (implement if critical)
        # _delete_gcs_file(gcs_file_name) # Example helper
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create URL entry for image")


    # Create Image entry in the database
    db_image = models.Image(
        name=name,
        pdf_id=pdf_id,
        image_number=image_number,
        page_number=page_number,
        chapter_number=chapter_number,
        url_id=url_id, # Use the generated URL ID
    )
    db.add(db_image)
    try:
        db.commit() # Commit both URL and Image
        db.refresh(db_url)
        db.refresh(db_image)
        logger.info(f"Created Image '{name}' (ID: {db_image.id}) for PDF {pdf_id} by user {current_user.username}")
        # Eager load URL for response model
        db.refresh(db_image, attribute_names=['url'])
        return db_image
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError creating image DB entry: {str(e)}")
        # GCS cleanup needed here for orphaned file
        # _delete_gcs_file(gcs_file_name) # Example helper
        # Clean up the orphaned URL?
        if url_id:
             try:
                 url_to_delete = db.get(models.URL, url_id) # Get URL within session
                 if url_to_delete:
                     db.delete(url_to_delete)
                     db.commit()
             except Exception as cleanup_e:
                 logger.error(f"Failed to cleanup orphaned URL {url_id} after image creation failure: {cleanup_e}")

        # Check if it's the pdf_id constraint
        if "FOREIGN KEY (`pdf_id`)" in str(e.orig):
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid pdf_id ({pdf_id}). PDF does not exist.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database constraint violation during image creation.",
            )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating Image DB entry: {str(e)}")
         # GCS cleanup needed here for orphaned file
        # _delete_gcs_file(gcs_file_name) # Example helper
        # Clean up the orphaned URL?
        if url_id:
             try:
                 url_to_delete = db.get(models.URL, url_id)
                 if url_to_delete:
                     db.delete(url_to_delete)
                     db.commit()
             except Exception as cleanup_e:
                 logger.error(f"Failed to cleanup orphaned URL {url_id} after image creation failure: {cleanup_e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create image entry")


@router.get("/{image_id}", response_model=schemas.ImageInfo)
def read_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves an image by ID."""
    # Eager load URL for response
    db_image = db.query(models.Image).options(
        joinedload(models.Image.url)
    ).filter(models.Image.id == image_id).first()
    if db_image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )
    return db_image


@router.get("/", response_model=List[schemas.ImageInfo])
def read_images(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves all images with pagination."""
    # Eager load URL for response
    db_images = db.query(models.Image).options(
        joinedload(models.Image.url)
    ).offset(skip).limit(limit).all()
    return db_images


@router.put("/{image_id}", response_model=schemas.ImageInfo)
async def update_image(
    image_id: int,
    name: str = Form(...),  # This is the image title
    pdf_id: int = Form(...),
    image_file: Optional[UploadFile] = File(None), #Make this optional
    image_number: Optional[int] = Form(None),
    page_number: Optional[int] = Form(None),
    chapter_number: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Updates an image by ID."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin": # Example: only Admin could update
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
    #     )
    # --- END REMOVAL ---

    # Eager load URL for potential update/cleanup
    db_image = db.query(models.Image).options(
        joinedload(models.Image.url)
    ).filter(models.Image.id == image_id).first()

    if db_image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    # Store old URL ID/path for cleanup if replacing file
    old_url_id = db_image.url_id
    db_url_old = db_image.url # Use loaded relationship
    old_gcs_url_path = None
    if db_url_old and db_url_old.url.startswith(f"https://storage.googleapis.com/{bucket_name}/"):
        old_gcs_url_path = db_url_old.url.split(f"{bucket_name}/", 1)[1].split('?')[0]

    # Update basic info first
    db_image.name = name
    db_image.pdf_id = pdf_id
    db_image.image_number = image_number
    db_image.page_number = page_number
    db_image.chapter_number = chapter_number

    gcs_file_name: Optional[str] = None
    image_url: Optional[str] = None
    db_url_new: Optional[models.URL] = None

    if image_file:
        # Upload new file to GCS
        file_extension = image_file.filename.split(".")[-1] if image_file.filename and '.' in image_file.filename else 'jpg'
        img_num_str = f"_img{image_number}" if image_number is not None else ""
        page_num_str = f"_pg{page_number}" if page_number is not None else ""
        gcs_file_name = f"images/pdf_{pdf_id}/{name.replace(' ', '_')}{img_num_str}{page_num_str}.{file_extension}"
        try:
            image_url = await upload_to_mysql(image_file, gcs_file_name)
        except HTTPException as e: # Catch GCS upload errors
            db.rollback() # Rollback potential basic info changes
            raise e
        except Exception as e:
            db.rollback()
            logger.error(f"Error uploading updated image file to GCS: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to upload updated image file")

        # Update existing URL or create new one
        if db_url_old:
            if db_url_old.url != image_url:
                 db_url_old.url = image_url
            db_url_old.url_type = schemas.UrlTypeEnum.HTTPS.value # Ensure correct type
            logger.debug(f"Updating existing URL {db_url_old.id} for image {image_id}")
        else:
            # Create a *new* URL entry for the new file if none existed
            try:
                # --- MODIFIED LINE: Changed url_type ---
                db_url_new = models.URL(url=image_url, url_type=schemas.UrlTypeEnum.HTTPS.value) # Use "https" from Enum value
                # --- END MODIFICATION ---
                db.add(db_url_new)
                db.flush()
                if not db_url_new.id:
                    raise Exception("Failed to generate new URL ID during update.")
                db_image.url_id = db_url_new.id # Point image to the new URL ID
                logger.debug(f"Created new URL with id: {db_url_new.id} for updated image {image_id}")
            except Exception as e:
                db.rollback()
                # GCS cleanup for the newly uploaded file?
                raise HTTPException(status_code=500, detail=f"Failed to create new URL entry during update: {e}")

    try:
        db.commit() # Commit image update (and potentially new/updated URL)
        db.refresh(db_image)
        # Refresh the relationships for the response model
        db.refresh(db_image, attribute_names=['url'])

        # --- Cleanup old GCS file (if GCS filename changed) ---
        if image_file and old_gcs_url_path and gcs_file_name and old_gcs_url_path != gcs_file_name and bucket:
            try:
                old_blob = bucket.blob(old_gcs_url_path)
                if old_blob.exists():
                    old_blob.delete()
                    logger.info(f"Deleted old GCS file due to path change: {old_gcs_url_path}")
            except Exception as gcs_e:
                logger.error(f"Failed to delete old GCS file {old_gcs_url_path}: {gcs_e}")
        # --- End Cleanup ---

        logger.info(f"Updated Image ID {image_id} by user {current_user.username}")
        return db_image
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError during image update commit: {str(e)}")
        if "FOREIGN KEY (`pdf_id`)" in str(e.orig):
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid pdf_id ({pdf_id}). PDF does not exist.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database constraint violation during image update.",
            )
    except Exception as e:
        db.rollback()
        logger.error(f"Error committing image update {image_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while updating image.")


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Deletes an image by ID."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin": # Example: only Admin could delete
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
    #     )
    # --- END REMOVAL ---

    # Eager load URL for GCS path and deletion
    db_image = db.query(models.Image).options(
        joinedload(models.Image.url)
    ).filter(models.Image.id == image_id).first()

    if db_image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
        )

    url_id_to_delete = db_image.url_id
    db_url_to_delete = db_image.url # Use loaded relationship
    gcs_blob_name = None

    if db_url_to_delete:
        gcs_url_to_delete = db_url_to_delete.url
        # --- Derive expected GCS blob name ---
        if gcs_url_to_delete and gcs_url_to_delete.startswith(f"https://storage.googleapis.com/{bucket_name}/"):
            gcs_blob_name = gcs_url_to_delete.split(f"{bucket_name}/", 1)[1].split('?')[0]
        else:
            logger.warning(f"Could not determine GCS blob name from URL {gcs_url_to_delete} for image {image_id}.")

    try:
        # Delete the image entry first (URL FK is SET NULL)
        db.delete(db_image)
        db.commit()
        logger.info(f"Deleted Image {image_id} by user {current_user.username}.")

        # Now, attempt to delete the corresponding URL entry
        if db_url_to_delete:
            url_in_session = db.get(models.URL, url_id_to_delete)
            if url_in_session:
                try:
                    db.delete(url_in_session)
                    db.commit()
                    logger.info(f"Deleted associated URL {url_id_to_delete} for image {image_id}.")
                except Exception as url_del_e:
                    db.rollback()
                    logger.error(f"Failed to delete URL {url_id_to_delete} after image deletion: {url_del_e}", exc_info=True)
            else:
                logger.warning(f"URL {url_id_to_delete} not found in session for deletion after image delete.")
        else:
            logger.info(f"No associated URL found or already deleted for image {image_id}.")

        # --- GCS Deletion ---
        if gcs_blob_name and bucket:
            try:
                blob = bucket.blob(gcs_blob_name)
                if blob.exists():
                    blob.delete()
                    logger.info(f"Deleted GCS file: {gcs_blob_name}")
                else:
                    logger.warning(f"GCS file not found for deletion: {gcs_blob_name}")
            except Exception as gcs_e:
                logger.error(f"Failed to delete GCS file {gcs_blob_name}: {gcs_e}")
        elif db_url_to_delete:
             logger.warning(f"Deletion of GCS file skipped for image {image_id} because blob name could not be determined from URL: {db_url_to_delete.url}")
        # --- End GCS Deletion ---

        return None # Return None for 204
    except Exception as e:
        db.rollback() # Rollback image delete if subsequent steps fail
        logger.error(f"Error deleting image {image_id} or associated URL {url_id_to_delete}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete image {image_id}: {e}")


@router.get("/pdf/{pdf_id}", response_model=List[schemas.ImageInfo])
def read_images_by_pdf(
    pdf_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves all images for a specific PDF ID."""
    # No specific role check was present here
    # Check if PDF exists
    pdf_exists = db.query(models.PDF.id).filter(models.PDF.id == pdf_id).first()
    if not pdf_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"PDF with id {pdf_id} not found.")

    db_images = (
        db.query(models.Image)
        .options(joinedload(models.Image.url)) # Eager load URL
        .filter(models.Image.pdf_id == pdf_id)
        .all()
    )
    return db_images

@router.get("/lesson/{lesson_id}", response_model=List[schemas.ImageInfo])
def read_images_by_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves all images for a specific lesson ID."""
    # No specific role check was present here
    # Check if Lesson exists
    lesson_exists = db.query(models.Lesson.id).filter(models.Lesson.id == lesson_id).first()
    if not lesson_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson with id {lesson_id} not found.")

    # Get PDFs associated with the lesson
    pdf_ids = [
        pdf.id for pdf in db.query(models.PDF.id).filter(models.PDF.lesson_id == lesson_id).all()
    ]

    if not pdf_ids:
        return [] # No PDFs, so no images for this lesson

    # Retrieve images linked to those PDFs
    db_images = (
        db.query(models.Image)
        .options(joinedload(models.Image.url)) # Eager load URL
        .filter(models.Image.pdf_id.in_(pdf_ids))
        .all()
    )
    return db_images
