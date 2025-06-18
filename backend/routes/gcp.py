# backend/routes/gcp.py
import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2 import service_account
import google.auth.transport.requests
from dotenv import load_dotenv

from backend import models, schemas # Import schemas
from backend.dependencies import get_current_user # Import authentication dependency

# Load environment variables from .env
load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/gcp", tags=["GCP Configuration"])

# Define necessary constants from environment variables
# Use GOOGLE_CLOUD_PROJECT if available, fallback to PROJECT_ID
GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("PROJECT_ID"))
# Use VERTEX_AI_LOCATION if available, fallback to LOCATION
GCP_LOCATION = os.getenv("VERTEX_AI_LOCATION", os.getenv("LOCATION", "us-central1")) # Default added

# Define the necessary scopes for Google Cloud APIs
# 'cloud-platform' is generally sufficient for most services including Vertex AI, GCS etc.
SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]


def generate_bearer_token() -> str:
    """
    Generates a Google Cloud bearer token using service account credentials.
    Raises HTTPException on failure.
    """
    try:
        # Load credentials
        credentials, project = google.auth.default(scopes=SCOPES)
        if not credentials:
            logger.error("Could not find default Google credentials.")
            raise DefaultCredentialsError("No default credentials found.")

        # Request object for refreshing token
        auth_req = google.auth.transport.requests.Request()

        # Refresh token (obtains a new token or uses cached one if valid)
        credentials.refresh(auth_req)

        # Get the access token
        bearer_token = credentials.token
        if not bearer_token:
             logger.error("Failed to obtain bearer token after credential refresh.")
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail="Could not obtain GCP access token.",
             )

        logger.info("Successfully generated GCP bearer token.")
        return bearer_token

    except google.auth.exceptions.RefreshError as e:
         logger.error(f"Error refreshing GCP credentials: {e}", exc_info=True)
         raise HTTPException(
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
             detail=f"Failed to refresh GCP credentials: {e}",
         )
    except Exception as e:
        logger.error(f"Unexpected error generating bearer token: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating GCP token.",
        )


@router.get(
    "/credentials",
    response_model=schemas.GcpCredentialsResponse,
    summary="Get GCP Credentials for Client-Side Use",
    description="Provides a short-lived GCP access token, project ID, and location. Requires user authentication."
)
def get_gcp_credentials(
    current_user: models.User = Depends(get_current_user) # Ensure user is logged in
):
    """
    API endpoint to retrieve necessary GCP configuration for client-side operations.
    Requires authentication to ensure only logged-in users can request tokens.
    """
    # --- Validate Essential Configuration ---
    if not GCP_PROJECT_ID:
        logger.error("GCP Project ID (GOOGLE_CLOUD_PROJECT or PROJECT_ID) not configured in environment.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Server configuration error: GCP Project ID not set.",
        )

    if not GCP_LOCATION:
         logger.error("GCP Location (VERTEX_AI_LOCATION or LOCATION) not configured in environment.")
         raise HTTPException(
             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
             detail="Server configuration error: GCP Location not set.",
         )
    # --- End Validation ---


    # Generate the bearer token (will raise HTTPException on failure)
    bearer_token = generate_bearer_token()

    # Return the credentials
    return schemas.GcpCredentialsResponse(
        access_token=bearer_token,
        project_id=GCP_PROJECT_ID,
        location=GCP_LOCATION
    )
