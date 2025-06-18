# backend/routes/urls.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from backend import models, schemas
from backend.database import get_db
from backend.dependencies import get_current_user # Keep authentication
from sqlalchemy.exc import IntegrityError

router = APIRouter(prefix="/urls", tags=["urls"])


@router.post("/", response_model=schemas.URLInfo, status_code=status.HTTP_201_CREATED) # Use URLInfo for response
def create_url(
    url: schemas.URLCreate, # Input uses URLCreate with UrlTypeEnum validation
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Creates a new URL (requires authentication). Only 'https' or 'gs' url_type allowed."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    # The input `url` object already has url_type validated as UrlTypeEnum
    # We pass the validated enum member's value directly to the model
    db_url = models.URL(url=url.url, url_type=url.url_type.value)
    db.add(db_url)
    try:
        db.commit()
        db.refresh(db_url)
        return db_url # Return the ORM object, Pydantic maps it to URLInfo
    except IntegrityError as e:
        db.rollback()
        # Check for the specific CheckConstraint violation
        if "chk_url_type_values" in str(e.orig):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid url_type. Must be 'https' or 'gs'.")
        # Handle other integrity errors if necessary
        raise HTTPException(status_code=500, detail=f"Failed to create URL due to database constraint: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create URL: {e}")


@router.get("/{url_id}", response_model=schemas.URLInfo) # Use URLInfo for response
def read_url(
    url_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves a URL by ID (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_url = db.query(models.URL).filter(models.URL.id == url_id).first()
    if db_url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    # Return ORM object; Pydantic maps if configured
    return db_url


@router.get("/", response_model=List[schemas.URLInfo]) # Use URLInfo for response
def read_urls(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Retrieves all URLs (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_urls = db.query(models.URL).offset(skip).limit(limit).all()
    # Return ORM objects; Pydantic maps if configured
    return db_urls


@router.put("/{url_id}", response_model=schemas.URLInfo) # Use URLInfo for response
def update_url(
    url_id: int,
    url: schemas.URLCreate, # Use URLCreate for input data (with Enum validation)
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Updates a URL by ID (requires authentication). Only 'https' or 'gs' url_type allowed."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_url = db.query(models.URL).filter(models.URL.id == url_id).first()
    if db_url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    # Update using validated data from the schema
    db_url.url = url.url
    db_url.url_type = url.url_type.value # Use the validated enum value

    try:
        db.commit()
        db.refresh(db_url)
        # Return ORM object; Pydantic maps if configured
        return db_url
    except IntegrityError as e:
        db.rollback()
        # Check for the specific CheckConstraint violation
        if "chk_url_type_values" in str(e.orig):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid url_type. Must be 'https' or 'gs'.")
        # Handle other integrity errors if necessary
        raise HTTPException(status_code=500, detail=f"Failed to update URL due to database constraint: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update URL: {e}")


@router.delete("/{url_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_url(
    url_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user), # Authentication check
):
    """Deletes a URL by ID (requires authentication)."""
    # --- AUTHORIZATION REMOVED ---
    # if current_user.user_type != "Admin":
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    # --- END REMOVAL ---

    db_url = db.query(models.URL).filter(models.URL.id == url_id).first()
    if db_url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    # Check dependencies if cascade delete isn't set/reliable
    # Note: AssignmentSample also links here now, but FK is SET NULL, so shouldn't block deletion.
    has_pdf_links = db.query(models.PDFUrl.pdf_id).filter(models.PDFUrl.url_id == url_id).limit(1).first()
    has_videos = db.query(models.Video.id).filter(models.Video.url_id == url_id).limit(1).first()
    has_images = db.query(models.Image.id).filter(models.Image.url_id == url_id).limit(1).first()

    # Check if the URL is directly linked by AssignmentSample (if FK was RESTRICT/CASCADE instead of SET NULL)
    # has_assignment_samples = db.query(models.AssignmentSample.id).filter(models.AssignmentSample.file_url_id == url_id).limit(1).first()

    # Adjust the check based on dependencies that block deletion (CASCADE on PDFUrl means PDFs block URL delete)
    if has_pdf_links: # or has_videos or has_images: # Videos/Images use SET NULL, so they don't block
        dependencies = []
        if has_pdf_links: dependencies.append("PDFs")
        # if has_videos: dependencies.append("Videos") # Don't add if SET NULL
        # if has_images: dependencies.append("Images") # Don't add if SET NULL
        # if has_assignment_samples: dependencies.append("Assignment Samples") # Don't add if SET NULL
        raise HTTPException(status_code=409, detail=f"Cannot delete URL. It is referenced by {', '.join(dependencies)}.")

    try:
        db.delete(db_url)
        db.commit()
        return None # Return None for 204
    except IntegrityError as e: # Catch potential FK violations if check missed something or cascade fails
         db.rollback()
         # Check which constraint failed if possible (DB dependent)
         raise HTTPException(status_code=409, detail=f"Cannot delete URL. It might be referenced by other items. Error: {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete URL: {e}")
