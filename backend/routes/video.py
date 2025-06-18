# backend/routes/video.py
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from datetime import datetime

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/videos", tags=["Videos"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Remove GCS-related imports and initialization
# Google Cloud Storage is no longer needed


async def upload_to_mysql(file: UploadFile, file_name: str, user_id: int = None):
    """Uploads a video file to MySQL database"""
    db: Session = next(get_db())
    try:
        # Read file contents
        contents = await file.read()
        file_size = len(contents)
        
        # Create database record
        db_file = models.UserFile(
            user_id=user_id or 0,  # Use provided user_id or default to 0
            filename=file_name,
            content_type=file.content_type,
            data=contents,
            created_at=datetime.utcnow()
        )
        
        # Add to database
        db.add(db_file)
        db.commit()
        db.refresh(db_file)
        
        # Generate access URL pointing to your file serving endpoint
        access_url = f"/api/files/{db_file.id}"
        
        logger.info(f"Successfully uploaded {file_name} to MySQL. Size: {file_size} bytes")
        return access_url, file_size  # Return access URL and file size
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error uploading {file_name} to MySQL: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading to database: {str(e)}",
        )
    finally:
        db.close()


@router.post("/", response_model=schemas.VideoInfo, status_code=status.HTTP_201_CREATED)
async def create_video(
    name: str = Form(...),  # video Name. User input.
    lesson_id: int = Form(...),
    video_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Creates a new video, uploads the file to MySQL database.
    """
    db_video: Optional[models.Video] = None
    db_url: Optional[models.URL] = None
    mysql_file_name: Optional[str] = None
    video_url: Optional[str] = None

    try:
        # 1. Create Video entry first (without url_id and size)
        db_video = models.Video(
            name=name,
            lesson_id=lesson_id
            # url_id and size will be added later
        )
        db.add(db_video)
        db.flush() # Use flush to get the db_video.id before commit

        # Check if ID was generated
        if not db_video.id:
            raise Exception("Failed to generate Video ID after flush.")

        # 2. Construct filename using video_id
        file_extension = ""
        original_filename = video_file.filename or ""
        if '.' in original_filename:
            file_extension = original_filename.split(".")[-1]
        # Use a default extension if none found
        if not file_extension:
            logger.warning(f"Could not determine file extension for {original_filename}. Using 'mp4' as default.")
            file_extension = 'mp4'

        mysql_file_name = f"video_{db_video.id}.{file_extension}"
        logger.debug(f"Generated MySQL filename: {mysql_file_name}")

        # 3. Upload to MySQL with video_id as filename
        try:
            video_url, file_size = await upload_to_mysql(video_file, mysql_file_name, current_user.id)
        except HTTPException as http_exc:
            # If MySQL fails, rollback the flushed Video object
            db.rollback()
            logger.error(f"MySQL upload failed for {mysql_file_name}. Rolling back Video {db_video.id} creation.")
            raise http_exc
        except Exception as mysql_exc:
            db.rollback()
            logger.error(f"Unexpected MySQL upload error for {mysql_file_name}. Rolling back Video {db_video.id} creation: {mysql_exc}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload video file.")

        # 4. Create URL entry
        db_url = models.URL(url=video_url, url_type=schemas.UrlTypeEnum.LOCAL.value)  # Changed to LOCAL
        db.add(db_url)
        db.flush() # Get url_id

        if not db_url.id:
            raise Exception("Failed to generate URL ID after flush.")

        # 5. Update Video entry with url_id and size
        db_video.url_id = db_url.id
        db_video.size = file_size
        db.flush()

        # 6. Commit everything together
        db.commit()

        db.refresh(db_video)
        db.refresh(db_url)

        logger.info(f"Created video '{db_video.name}' (ID: {db_video.id}) with URL {db_url.id} and MySQL file {mysql_file_name} by user {current_user.username}")
        # Eager load relationship for response model computed field
        db.refresh(db_video, attribute_names=['url'])
        return db_video

    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError: {str(e)}")
        # Clean up MySQL file if upload succeeded before DB error
        # Note: For MySQL, cleanup would involve deleting the UserFile record
        # This is handled by the rollback in upload_to_mysql function
        
        # Check constraint violations
        if "FOREIGN KEY (`lesson_id`)" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid lesson_id ({lesson_id}). Lesson does not exist.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database constraint violation during video creation.",
            )
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating video: {str(e)}", exc_info=True)
        # MySQL cleanup is handled by rollback in upload_to_mysql
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )


@router.get("/{video_id}", response_model=schemas.VideoInfo)
def read_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves a video by ID."""
    db_video = db.query(models.Video).options(
        joinedload(models.Video.url)
    ).filter(models.Video.id == video_id).first()

    if db_video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )
    return db_video


@router.get("/", response_model=List[schemas.VideoInfo])
def read_videos(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves all videos."""
    db_videos = db.query(models.Video).options(
        joinedload(models.Video.url)
    ).offset(skip).limit(limit).all()
    return db_videos


@router.put("/{video_id}", response_model=schemas.VideoInfo)
async def update_video(
    video_id: int,
    name: str = Form(...),
    lesson_id: int = Form(...),
    video_file: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """
    Updates a video by ID. If a new file is provided, it replaces the old one
    in MySQL database using the video's ID as the filename.
    """
    db_video = db.query(models.Video).options(
        joinedload(models.Video.url)
    ).filter(models.Video.id == video_id).first()

    if db_video is None:
        logger.warning(f"Video with id {video_id} not found for update")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )

    # Store old URL ID for potential cleanup
    old_url_id = db_video.url_id
    db_url_old = db_video.url  # Use the already loaded relationship
    old_file_id = None

    # Extract file ID from old URL if it exists
    if db_url_old and db_url_old.url.startswith("/api/files/"):
        try:
            old_file_id = int(db_url_old.url.split("/api/files/")[1])
        except (IndexError, ValueError):
            logger.warning(f"Could not extract file ID from URL: {db_url_old.url}")

    # Update basic info first
    db_video.name = name
    db_video.lesson_id = lesson_id

    mysql_file_name = None
    new_video_url = None

    if video_file:
        # Generate filename based on video_id
        file_extension = ""
        original_filename = video_file.filename or ""
        if '.' in original_filename:
            file_extension = original_filename.split(".")[-1]
        if not file_extension:
            logger.warning(f"Could not determine file extension for updated file {original_filename}. Using 'mp4'.")
            file_extension = 'mp4'

        mysql_file_name = f"video_{db_video.id}.{file_extension}"
        logger.debug(f"Updating MySQL file: {mysql_file_name}")

        try:
            # Upload new file
            new_video_url, file_size = await upload_to_mysql(video_file, mysql_file_name, current_user.id)
            db_video.size = file_size # Update size
        except HTTPException as e:
            db.rollback()
            raise e
        except Exception as e:
            db.rollback()
            logger.error(f"Error uploading updated video file to MySQL: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to upload updated video file")

        # Update existing URL object or create new one
        if db_url_old:
            if db_url_old.url != new_video_url:
                db_url_old.url = new_video_url
            db_url_old.url_type = schemas.UrlTypeEnum.LOCAL.value  # Changed to LOCAL
            logger.debug(f"Updating existing URL {db_url_old.id} for video {video_id}")
        else:
            # Create new URL object if none existed before
            try:
                db_url_new = models.URL(url=new_video_url, url_type=schemas.UrlTypeEnum.LOCAL.value)  # Changed to LOCAL
                db.add(db_url_new)
                db.flush()
                if not db_url_new.id:
                    raise Exception("Failed to generate new URL ID during update.")
                db_video.url_id = db_url_new.id
                logger.debug(f"Created new URL with id: {db_url_new.id} for updated video {video_id}")
            except Exception as e:
                db.rollback()
                logger.error(f"Failed to create new URL entry during update: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to create new URL entry during update: {e}")

    try:
        db.commit()
        db.refresh(db_video)
        db.refresh(db_video, attribute_names=['url'])

        # Cleanup old MySQL file if a new file was uploaded
        if video_file and old_file_id:
            try:
                old_file = db.query(models.UserFile).filter(models.UserFile.id == old_file_id).first()
                if old_file:
                    db.delete(old_file)
                    db.commit()
                    logger.info(f"Deleted old MySQL file with ID: {old_file_id}")
            except Exception as cleanup_e:
                logger.error(f"Failed to delete old MySQL file {old_file_id}: {cleanup_e}")

        logger.info(f"Updated video with id: {db_video.id} by user {current_user.username}")
        return db_video
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError during video update commit: {str(e)}")
        if "FOREIGN KEY (`lesson_id`)" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid lesson_id ({lesson_id}). Lesson does not exist.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database constraint violation during video update.",
            )
    except Exception as e:
        db.rollback()
        logger.error(f"Error committing video update {video_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An unexpected error occurred while updating video.")


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Deletes a video by ID, its associated URL entry, and the corresponding MySQL file."""
    # Eager load URL for deletion and getting file ID
    db_video = db.query(models.Video).options(
        joinedload(models.Video.url)
    ).filter(models.Video.id == video_id).first()

    if db_video is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Video not found"
        )

    url_id_to_delete = db_video.url_id
    db_url_to_delete = db_video.url
    file_id_to_delete = None

    # Extract file ID from URL
    if db_url_to_delete and db_url_to_delete.url.startswith("/api/files/"):
        try:
            file_id_to_delete = int(db_url_to_delete.url.split("/api/files/")[1])
        except (IndexError, ValueError):
            logger.warning(f"Could not extract file ID from URL: {db_url_to_delete.url}")

    try:
        # Delete the video entry first
        db.delete(db_video)
        db.commit()
        logger.info(f"Deleted Video {video_id} by user {current_user.username}.")

        # Delete the corresponding URL entry if it exists
        if db_url_to_delete:
            url_in_session = db.get(models.URL, url_id_to_delete)
            if url_in_session:
                try:
                    db.delete(url_in_session)
                    db.commit()
                    logger.info(f"Deleted associated URL {url_id_to_delete} for video {video_id}.")
                except Exception as url_del_e:
                    db.rollback()
                    logger.error(f"Failed to delete URL {url_id_to_delete} after video deletion: {url_del_e}", exc_info=True)
            else:
                logger.warning(f"URL {url_id_to_delete} not found in session for deletion after video delete.")

        # Delete MySQL file
        if file_id_to_delete:
            try:
                file_to_delete = db.query(models.UserFile).filter(models.UserFile.id == file_id_to_delete).first()
                if file_to_delete:
                    db.delete(file_to_delete)
                    db.commit()
                    logger.info(f"Deleted MySQL file with ID: {file_id_to_delete}")
                else:
                    logger.warning(f"MySQL file with ID {file_id_to_delete} not found for deletion")
            except Exception as file_e:
                logger.error(f"Failed to delete MySQL file {file_id_to_delete}: {file_e}")

        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting video {video_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete video {video_id}: {e}")


@router.get("/lesson/{lesson_id}", response_model=List[schemas.VideoInfo])
def read_videos_by_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Retrieves all videos for a specific lesson ID, including the video URL."""
    # Check if lesson exists
    lesson_exists = db.query(models.Lesson.id).filter(models.Lesson.id == lesson_id).first()
    if not lesson_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lesson with id {lesson_id} not found.")

    db_videos = (
        db.query(models.Video)
        .options(joinedload(models.Video.url))
        .filter(models.Video.lesson_id == lesson_id)
        .all()
    )
    return db_videos


# Add endpoint to serve video files
@router.get("/file/{file_id}")
async def get_video_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Serves video file from MySQL database"""
    from fastapi.responses import StreamingResponse
    import io
    
    file_record = db.query(models.UserFile).filter(models.UserFile.id == file_id).first()
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Create a BytesIO object from the file data
    file_data = io.BytesIO(file_record.data)
    
    return StreamingResponse(
        io.BytesIO(file_record.data),
        media_type=file_record.content_type,
        headers={"Content-Disposition": f"inline; filename={file_record.filename}"}
    )