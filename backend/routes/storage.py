import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from dotenv import load_dotenv
from backend import models, schemas
from backend.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/storage", tags=["Storage Configuration"])
load_dotenv()

# Configuration from environment
STORAGE_CONFIG = {
    "type": "mysql",
    "base_url": os.getenv("LOCAL_STORAGE_URL", "http://localhost:8000/files"),
    "max_size_mb": int(os.getenv("MAX_FILE_SIZE_MB", 10)),
    "allowed_types": [
        "image/jpeg",
        "image/png",
        "application/pdf",
        # Add other allowed types as needed
    ]
}

@router.get(
    "/config",
    response_model=schemas.StorageConfigResponse,
    summary="Get Storage Configuration",
    description="Provides storage configuration for client-side use"
)
def get_storage_config(
    current_user: models.User = Depends(get_current_user)
) -> schemas.StorageConfigResponse:
    """
    Returns local storage configuration for client-side operations
    """
    try:
        return schemas.StorageConfigResponse(
            storage_type=STORAGE_CONFIG["type"],
            base_url=STORAGE_CONFIG["base_url"],
            max_file_size=STORAGE_CONFIG["max_size_mb"] * 1024 * 1024,  # Convert MB to bytes
            allowed_types=STORAGE_CONFIG["allowed_types"]
        )
    except Exception as e:
        logger.error(f"Error getting storage config: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving storage configuration"
        )