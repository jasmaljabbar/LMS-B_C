# backend/routes/pdfs.py
import os
import logging  # Import the logging module
from fastapi import APIRouter, Depends, HTTPException, Request, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from sqlalchemy.exc import IntegrityError

from backend import models, schemas
from backend.database import get_db, SessionLocal
from backend.dependencies import get_current_user # Keep authentication
from google.cloud import storage
from dotenv import load_dotenv
from pathlib import Path
from fastapi.responses import FileResponse, JSONResponse

load_dotenv()

router = APIRouter(prefix="/pdfs", tags=["PDFs"])

# Configure logging
logging.basicConfig(level=logging.INFO)  # Set the logging level (e.g., INFO, DEBUG)
logger = logging.getLogger(__name__)  # Get a logger for the current module

# Initialize Google Cloud Storage client

# client = storage.Client()
# bucket_name = os.getenv("GCS_BUCKET_NAME")
# if not bucket_name:
#     raise ValueError("GCS_BUCKET_NAME environment variable not set.")
# try:
#     bucket = client.get_bucket(bucket_name)
# except Exception as e:
#      raise ValueError(f"Could not get GCS bucket '{bucket_name}'. Error: {e}")


# async def upload_to_gcs(file: UploadFile, file_name: str):
#     """
#     Uploads a PDF file to Google Cloud Storage and returns both HTTPS and GS URLs.
#     """
#     logger.info(f"upload_to_gcs called with file_name: {file_name}")

#     try:
#         blob = bucket.blob(file_name)
#         contents = await file.read()
#         blob.upload_from_string(contents, content_type=file.content_type)

#         # Get both HTTPS and GS URLs
#         https_url = blob.public_url  # https://storage.googleapis.com/bucket/file
#         gs_url = f"gs://{bucket_name}/{file_name}"  # gs://bucket/file

#         logger.info(f"File uploaded to GCS. HTTPS URL: {https_url}, GS URL: {gs_url}")
#         return https_url, gs_url, len(contents)
#     except Exception as e:
#         logger.error(f"Error uploading file {file_name} to GCS: {e}", exc_info=True)
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error uploading to GCS: {str(e)}",
#         )


import os
from pathlib import Path

# Configure upload directory
PDF_UPLOAD_DIR = Path("uploads/pdfs")
PDF_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

async def upload_pdf_to_mysql(file: UploadFile, file_name: str):
    db = SessionLocal()
    try:
        contents = await file.read()
        file_size = len(contents)
        
        if not contents.startswith(b'%PDF-'):
            raise HTTPException(400, detail="Invalid PDF file")
        
        # Generate safe filename
        safe_filename = f"{Path(file_name).stem[:100]}.pdf"  # Truncate if needed
        file_path = PDF_UPLOAD_DIR / safe_filename
        
        # Save to filesystem
        with open(file_path, "wb") as f:
            f.write(contents)
        
        # Store metadata in database
        db_file = models.FileStorage(
            file_name=safe_filename,
            file_path=str(file_path),
            content_type="application/pdf",
            file_size=file_size,
            https_url=f"/pdfs/{safe_filename}",
            gs_url=f"local:/{file_path}"
        )
        
        db.add(db_file)
        db.commit()
        return (
            db_file.https_url,
            db_file.gs_url,
            db_file.file_size
        )
    except Exception as e:
        # Cleanup failed upload
        if 'file_path' in locals() and file_path.exists():
            try:
                os.unlink(file_path)
            except:
                pass
        db.rollback()
        logger.error(f"PDF upload failed: {e}", exc_info=True)
        raise HTTPException(500, detail=f"PDF upload failed: {str(e)}")
    finally:
        db.close()

# Add this endpoint to serve PDFs
# @router.get("/pdfs/{file_name}")
# async def serve_pdf(file_name: str):
#     """Serve PDF files from filesystem"""
#     file_path = PDF_UPLOAD_DIR / file_name
#     if not file_path.exists():
#         raise HTTPException(404, detail="PDF not found")
    
#     return FileResponse(
#         file_path,
#         media_type="application/pdf",
#         filename=file_name
#     )


@router.post("/", response_model=schemas.PDFInfo, status_code=status.HTTP_201_CREATED)
async def create_pdf(
        pdf_name: str = Form(...),
        lesson_id: int = Form(...),
        pdf_file: UploadFile = File(...),
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Creates a new PDF with file upload."""
    logger.info(f"create_pdf called by {current_user.username} with pdf_name: {pdf_name}, lesson_id: {lesson_id}, filename: {pdf_file.filename}")

    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type not in ["Admin", "Teacher"]:
    #     logger.warning(f"User {current_user.username} not authorized to create PDF")
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
    #     )
    # --- END REMOVAL ---

    db_pdf = None # Initialize db_pdf
    try:
        # Create PDF entry first without size
        db_pdf = models.PDF(
            name=pdf_name,
            lesson_id=lesson_id
        )
        db.add(db_pdf)
        db.flush() # Use flush to get the db_pdf.id before commit

        # Use pdf_id in the GCS filename for uniqueness
        file_extension = ""
        if '.' in pdf_file.filename:
            file_extension = pdf_file.filename.split(".")[-1]
        gcs_file_name = f"pdfs/{db_pdf.id}.{file_extension}" if file_extension else f"pdfs/{db_pdf.id}"
        logger.debug(f"Generated GCS filename: {gcs_file_name}")

        # Upload to GCS with pdf_id as filename
        https_url, gs_url, file_size = await upload_pdf_to_mysql(pdf_file, gcs_file_name)

        # Update PDF with file size
        db_pdf.size = file_size
        db.flush() # Flush size update

       # Create only gs URL entry
        db_gs_url = models.URL(url=gs_url, url_type="gs")
        db.add(db_gs_url)
        db.flush()
        db.refresh(db_gs_url)

        # Associate only the gs URL
        pdf_gs_url = models.PDFUrl(
            pdf_id=db_pdf.id,
            url_id=db_gs_url.id
        )
        db.add(pdf_gs_url)

        db.commit() # Commit everything together

        db.refresh(db_pdf) # Refresh the PDF object to load relationships if needed by response model

        # logger.info(f"Created PDF {db_pdf.id} with HTTPS URL {db_https_url.id} and GS URL {db_gs_url.id}")
        return db_pdf
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError: {str(e)}")
        # Check if the error is due to the lesson_id foreign key constraint
        if "FOREIGN KEY (`lesson_id`)" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid lesson_id ({lesson_id}). Lesson does not exist.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database constraint violation during PDF creation.",
            )
    except HTTPException as http_exc: # Catch specific HTTP exceptions from GCS upload
        db.rollback()
        raise http_exc
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating PDF: {str(e)}", exc_info=True)
         # Potentially orphaned GCS file if upload succeeded but DB failed
        if db_pdf and db_pdf.id and 'gcs_file_name' in locals():
             logger.warning(f"Potentially orphaned GCS file: {gcs_file_name}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@router.get("/{pdf_id}", response_model=schemas.PDFInfo)
def read_pdf(
        pdf_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves a PDF by ID."""
    # No specific role check was present here
    logger.info(f"read_pdf called with pdf_id: {pdf_id}")
    db_pdf = db.query(models.PDF).filter(models.PDF.id == pdf_id).first()

    if db_pdf is None:
        logger.warning(f"PDF with id {pdf_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found"
        )
    return db_pdf

@router.get("/{pdf_id}/url", response_model=schemas.PDFUrlInfo)
async def get_pdf_url(
    pdf_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Get the URL for a specific PDF"""
    pdf = db.query(models.PDF).filter(models.PDF.id == pdf_id).first()
    if not pdf:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    # Get the PDFUrl association and URL
    pdf_url = db.query(models.PDFUrl).join(models.URL).filter(
        models.PDFUrl.pdf_id == pdf_id
    ).first()
    
    if not pdf_url:
        raise HTTPException(status_code=404, detail="PDF URL not found")
    
    # Return as a dictionary matching PDFUrlInfo model
    return {
        "pdf_id": pdf_id,
        "url": pdf_url.url.url,
        # Add any other fields you defined in PDFUrlInfo
    }

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse









from fastapi.responses import FileResponse

@router.get("/{pdf_id}/file")
async def get_pdf_file(
    pdf_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Serve the actual PDF file"""
    db_pdf = db.query(models.PDF).filter(models.PDF.id == pdf_id).first()
    
    if db_pdf is None:
        raise HTTPException(status_code=404, detail="PDF not found")
    
    # Assuming you have a way to get the file path from your database
    file_storage = db.query(models.FileStorage).filter(
        models.FileStorage.file_name == f"{pdf_id}.pdf"
    ).first()
    
    if not file_storage:
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        file_storage.file_path,
        media_type="application/pdf",
        filename=f"document_{pdf_id}.pdf"
    )

from fastapi.responses import FileResponse, Response

@router.api_route("/serve-pdf/{pdf_id}", methods=["GET", "HEAD"])
async def serve_pdf(pdf_id: int):
    try:
        # Debug: Print the pdf_id and constructed path
        print(f"Requested PDF ID: {pdf_id}")
        
        # Construct the file path - ADJUST THIS TO YOUR ACTUAL STRUCTURE
        pdf_path = f"uploads/pdfs/{pdf_id}.pdf"
        
        # Debug: Print the full absolute path
        absolute_path = os.path.abspath(pdf_path)
        print(f"Looking for PDF at: {absolute_path}")
        print(f"File exists: {os.path.exists(pdf_path)}")
        
        # Check if file exists
        if not os.path.exists(pdf_path):
            # List files in the directory for debugging
            pdf_dir = "uploads/pdfs"
            if os.path.exists(pdf_dir):
                files = os.listdir(pdf_dir)
                print(f"Files in {pdf_dir}: {files}")
            else:
                print(f"Directory {pdf_dir} does not exist")
            
            raise HTTPException(status_code=404, detail=f"PDF not found at {absolute_path}")
        
        # Return the file
        return FileResponse(
            path=pdf_path,
            media_type="application/pdf",
            filename=f"document_{pdf_id}.pdf"
        )
    except Exception as e:
        print(f"Error serving PDF: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lesson/{lesson_id}", response_model=List[schemas.PDFInfo])
def read_pdfs_by_lesson(
        lesson_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves all PDFs for a specific lesson ID."""
    # No specific role check was present here
    logger.info(f"read_pdfs_by_lesson called with lesson_id: {lesson_id}")

    db_pdfs = (
        db.query(models.PDF).filter(models.PDF.lesson_id == lesson_id).all()
    )
    logger.debug(db_pdfs)

    if not db_pdfs:
        db_lesson = db.query(models.Lesson).filter(models.Lesson.id == lesson_id).first()
        if not db_lesson:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Lesson with id {lesson_id} not found.",
            )
        logger.info(f"No PDFs found for lesson {lesson_id}")
        return [] # Return empty list

    logger.debug(f"Returning {len(db_pdfs)} PDFs for lesson {lesson_id}")
    return db_pdfs


@router.get("/", response_model=List[schemas.PDFInfo])
def read_pdfs(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves all PDFs."""
    logger.info(f"read_pdfs called with skip: {skip}, limit: {limit}")
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type not in ["Admin"]:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_pdfs = db.query(models.PDF).offset(skip).limit(limit).all()
    logger.debug(f"Returning {len(db_pdfs)} PDFs")
    return db_pdfs


@router.put("/{pdf_id}", response_model=schemas.PDFInfo)
async def update_pdf(
        pdf_id: int,
        pdf_name: str = Form(...),
        lesson_id: int = Form(...),
        pdf_file: UploadFile = File(None),  # Optional file update
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Updates a PDF by ID. Allows updating the file or just the name/lesson_id."""
    logger.info(f"update_pdf called by {current_user.username} with pdf_id: {pdf_id}, pdf_name: {pdf_name}, lesson_id: {lesson_id}")

    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type not in ["Admin", "Teacher"]:
    #     logger.warning(f"User {current_user.username} not authorized to update PDF")
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
    #     )
    # --- END REMOVAL ---

    db_pdf = db.query(models.PDF).filter(models.PDF.id == pdf_id).first()

    if db_pdf is None:
        logger.warning(f"PDF with id {pdf_id} not found")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found"
        )

    # Update basic attributes
    db_pdf.name = pdf_name
    db_pdf.lesson_id = lesson_id # Assuming lesson_id can be updated

    if pdf_file:
        # Upload new file to GCS
        file_extension = ""
        if '.' in pdf_file.filename:
            file_extension = pdf_file.filename.split(".")[-1]
        gcs_file_name = f"pdfs/{db_pdf.id}.{file_extension}" if file_extension else f"pdfs/{db_pdf.id}"
        logger.debug(f"Updating GCS file: {gcs_file_name}")

        try:
            https_url, gs_url, file_size = await upload_pdf_to_mysql(pdf_file, gcs_file_name)
            db_pdf.size = file_size # Update size
        except HTTPException as e: # Catch GCS upload errors
             db.rollback() # Rollback any potential changes before error
             raise e
        except Exception as e:
            db.rollback()
            logger.error(f"Error uploading updated file to GCS: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to upload updated file")


        # --- Find and update existing https/gs URLs OR create new ones ---
        logger.warning(f"Replacing URL associations for PDF {pdf_id}. Consider implementing proper update logic.")
        db.query(models.PDFUrl).filter(models.PDFUrl.pdf_id == pdf_id).delete(synchronize_session=False)
        # Note: This doesn't delete the old URL objects themselves from the 'urls' table.

        db.flush() # Ensure deletions happen before additions if needed

        db_https_url = models.URL(url=https_url, url_type="https")
        db_gs_url = models.URL(url=gs_url, url_type="gs")
        db.add_all([db_https_url, db_gs_url])
        db.flush() # Get IDs

        # Create new associations
        pdf_https_assoc = models.PDFUrl(pdf_id=pdf_id, url_id=db_https_url.id)
        pdf_gs_assoc = models.PDFUrl(pdf_id=pdf_id, url_id=db_gs_url.id)
        db.add_all([pdf_https_assoc, pdf_gs_assoc])

    # Commit changes
    try:
        db.commit()
        db.refresh(db_pdf)
        logger.info(f"Updated PDF with id: {db_pdf.id}")
        return db_pdf
    except IntegrityError as e:
        db.rollback()
        logger.error(f"IntegrityError during PDF update: {str(e)}")
        if "FOREIGN KEY (`lesson_id`)" in str(e):
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid lesson_id ({lesson_id}). Lesson does not exist.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Database constraint violation during PDF update.",
            )
    except Exception as e:
        db.rollback()
        logger.error(f"Error committing PDF update {pdf_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while updating PDF: {str(e)}"
        )


@router.delete("/{pdf_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pdf(
        pdf_id: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Deletes a PDF by ID and its associations. Does NOT automatically delete URLs or GCS files."""
    logger.info(f"delete_pdf called by {current_user.username} with pdf_id: {pdf_id}")

    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type not in ["Admin"]:
    #     logger.warning(f"User {current_user.username} not authorized to delete PDF")
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized"
    #     )
    # --- END REMOVAL ---

    db_pdf = db.query(models.PDF).filter(models.PDF.id == pdf_id).first()
    if db_pdf is None:
        logger.warning(f"PDF with id {pdf_id} not found for deletion")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found"
        )

    try:
        # GCS Deletion Placeholder
        # Need to find the GCS URL associated with this PDF *before* deleting DB entries
        # e.g., query PDFUrl -> URL to get the https/gs path, parse blob name, delete blob
        # ...

        # Delete the PDF (cascade should handle PDFUrl if configured)
        db.delete(db_pdf)
        db.commit()
        logger.info(f"Deleted PDF with id: {pdf_id}. Associated URL entries and GCS file were NOT deleted.")
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting PDF {pdf_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete PDF {pdf_id}")

    return # Return None for 204 No Content
