# backend/services/analysis_service.py
import os
import logging
import json
from fastapi import HTTPException, status
from pydantic import ValidationError
from typing import Optional # Added for Optional type hint
import uuid # Added for session_id generation

from backend import schemas # Import schemas for validation and enums
from backend.database import SessionLocal # Added for DB session
from backend.models import LLMTokenUsage # Added for DB model

# --- Vertex AI Imports ---
try:
    import google.cloud.aiplatform as aiplatform
    from google.cloud.aiplatform.gapic.schema import predict
    from google.protobuf import json_format
    from google.protobuf.struct_pb2 import Value
    from vertexai.generative_models import GenerativeModel, Part, FinishReason
    import vertexai
except ImportError:
    aiplatform = None
    GenerativeModel = None
    Part = None
    vertexai = None
    FinishReason = None
    logging.getLogger(__name__).warning("google-cloud-aiplatform or vertexai library not installed. AI service features will be disabled.")

logger = logging.getLogger(__name__)

# --- Vertex AI Configuration (Needed by the service) ---
GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("PROJECT_ID"))
GCP_LOCATION = os.getenv("VERTEX_AI_LOCATION", os.getenv("LOCATION", "us-central1"))
GEMINI_MODEL_NAME = os.getenv("VERTEX_AI_MODEL", "gemini-1.5-flash-001")

# --- Vertex AI Initialization ---
vertexai_initialized = False
if aiplatform and vertexai and GCP_PROJECT_ID and GCP_LOCATION:
    try:
        # Ensure credentials are set before initializing
        vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
        vertexai_initialized = True
        logger.info(f"Vertex AI initialized for project '{GCP_PROJECT_ID}' in location '{GCP_LOCATION}'. (Analysis Service)")
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {e}", exc_info=True)
else:
    logger.warning("Vertex AI not initialized due to missing configuration or libraries. (Analysis Service)")


async def analyze_pdf_for_questions(
    gs_url: str, 
    user_id: int, 
    action: str, 
    session_id: Optional[str] = None
) -> schemas.QuestionAnalysisResponse:
    """
    Analyzes a PDF from a GS URL using Gemini to identify question types and counts,
    and logs LLM token usage.

    Args:
        gs_url: The gs:// URI of the PDF file.

    Returns:
        A validated QuestionAnalysisResponse object.

    Raises:
        HTTPException: If AI service is unavailable, analysis fails, or response is invalid.
    """
    # --- Check if Vertex AI is available within the function call ---
    if not vertexai_initialized or not GenerativeModel or not Part:
        logger.error("analyze_pdf_for_questions called but Vertex AI is not initialized.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analysis service is not available or configured correctly."
        )

    if not gs_url or not gs_url.startswith("gs://"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid GS URL provided.")

    logger.info(f"Starting AI analysis for GS URL: {gs_url}")

    # --- Prepare and Execute Gemini Request ---
    try:
        # Define the prompt (same as before)
        prompt = f"""
Analyze the provided PDF document located at {gs_url}.
Identify the different types of questions present in the document.
The allowed question types are: "fill_in_blanks", "match_following", "single_select", "multi_select", "short_answer".
Count the number of questions for each identified type.
Return the result ONLY as a JSON object with the following structure:
{{
  "question_counts": [
    {{"type": "allowed_question_type", "count": <number>}},
    ...
  ]
}}
If no questions of a specific allowed type are found, omit it from the list or set its count to 0.
Ensure the output is valid JSON.
"""
        # Create the Part object for the PDF
        pdf_part = Part.from_uri(
            mime_type="application/pdf",
            uri=gs_url
        )

        # Initialize the Gemini model
        model = GenerativeModel(GEMINI_MODEL_NAME)

        # Generate content
        logger.debug(f"Sending request to Gemini model: {GEMINI_MODEL_NAME}")
        response = await model.generate_content_async([prompt, pdf_part])
        logger.debug(f"Received response from Gemini. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'NO_CANDIDATES'}")

        # --- Log Token Usage ---
        logger.debug(f"Attempting to log LLM token usage for action: {action}, user_id: {user_id}, session_id: {session_id if session_id else 'N/A'}")
        db_log_session = None
        try:
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                prompt_tokens = response.usage_metadata.prompt_token_count
                candidate_tokens = response.usage_metadata.candidates_token_count
                total_tokens = prompt_tokens + candidate_tokens
                
                final_session_id = session_id if session_id else str(uuid.uuid4())
                model_name_to_log = GEMINI_MODEL_NAME

                token_entry = LLMTokenUsage(
                    user_id=user_id,
                    session_id=final_session_id,
                    action=action,
                    model_name=model_name_to_log,
                    input_tokens=prompt_tokens,
                    output_tokens=candidate_tokens,
                    total_tokens=total_tokens
                    # timestamp will be handled by server_default
                )
                db_log_session = SessionLocal()
                db_log_session.add(token_entry)
                db_log_session.commit()
                logger.debug(f"Successfully committed LLM token usage for action: {action}, user_id: {user_id}, session_id: {final_session_id}")
                logger.info(f"LLM token usage logged for action: {action}, user_id: {user_id}, session_id: {final_session_id}")
            else:
                logger.warning(f"LLM usage_metadata not available for action: {action}, user_id: {user_id}. Skipping token logging.")
        except Exception as log_exc:
            logger.error(f"Failed to log LLM token usage for action: {action}, user_id: {user_id}: {log_exc}")
            if db_log_session:
                db_log_session.rollback()
        finally:
            if db_log_session:
                db_log_session.close()
        # --- End Log Token Usage ---

        if not response.candidates or response.candidates[0].finish_reason != FinishReason.STOP:
             finish_reason_val = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
             # Convert FinishReason enum to string if it's not already
             finish_reason_str = finish_reason_val.name if hasattr(finish_reason_val, 'name') else str(finish_reason_val)
             logger.error(f"Gemini generation stopped unexpectedly. Reason: {finish_reason_str}")
             raise HTTPException(status_code=500, detail=f"AI analysis failed. Reason: {finish_reason_str}")

        # --- Process Gemini Response ---
        response_text = response.text
        logger.debug(f"Gemini raw response text: {response_text}")

        # Clean potential markdown code block fences
        if response_text.strip().startswith("```json"):
            response_text = response_text.strip()[7:-3].strip()
        elif response_text.strip().startswith("```"):
             response_text = response_text.strip()[3:-3].strip()

        # Parse the JSON response
        try:
            analysis_data = json.loads(response_text)
        except json.JSONDecodeError as json_err:
            logger.error(f"Failed to parse Gemini JSON response: {json_err}\nRaw response: {response.text}")
            # Raise HTTPException to be caught by the route handler
            raise HTTPException(status_code=500, detail="AI analysis service returned invalid JSON.")

        # Validate the parsed data against the Pydantic schema
        try:
            validated_response = schemas.QuestionAnalysisResponse(**analysis_data)
            logger.info(f"Successfully analyzed and validated response for {gs_url}")
            return validated_response
        except ValidationError as val_err:
            logger.error(f"Gemini response failed Pydantic validation: {val_err}\nParsed data: {analysis_data}")
            # Raise HTTPException to be caught by the route handler
            raise HTTPException(status_code=500, detail="AI analysis service returned data in an unexpected format.")

    except HTTPException as http_exc:
        # Re-raise HTTPExceptions directly (e.g., from GS URL validation)
        raise http_exc
    except Exception as e:
        logger.error(f"Error during Gemini analysis processing for {gs_url}: {e}", exc_info=True)
        # Raise a generic HTTPException for other errors
        raise HTTPException(status_code=500, detail=f"An error occurred during AI analysis: {str(e)}")
