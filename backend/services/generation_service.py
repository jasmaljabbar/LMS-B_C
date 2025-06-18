# backend/services/generation_service.py
import os
import logging
import json
from fastapi import HTTPException, status
from pydantic import ValidationError
# --- Added Imports ---
from typing import List, Dict, Any, Optional
import uuid
from backend.database import SessionLocal
from backend.models import LLMTokenUsage
# --- End Added Imports ---

# Import models and schemas using relative path if they are in the parent directory
try:
    from .. import models, schemas
except ImportError:
    # Fallback for different execution contexts if needed
    from backend import models, schemas


# --- Vertex AI Imports ---
try:
    import google.cloud.aiplatform as aiplatform
    from vertexai.generative_models import GenerativeModel, Part, FinishReason, GenerationConfig
    import vertexai
except ImportError:
    aiplatform = None
    GenerativeModel = None
    Part = None
    vertexai = None
    FinishReason = None
    GenerationConfig = None
    logging.getLogger(__name__).warning("google-cloud-aiplatform or vertexai library not installed. AI service features will be disabled.")

logger = logging.getLogger(__name__)

# --- Vertex AI Configuration ---
GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("PROJECT_ID"))
GCP_LOCATION = os.getenv("VERTEX_AI_LOCATION", os.getenv("LOCATION", "us-central1"))
GEMINI_MODEL_NAME = os.getenv("VERTEX_AI_MODEL", "gemini-1.5-flash-001")

# --- Vertex AI Initialization ---
vertexai_initialized = False
if aiplatform and vertexai and GCP_PROJECT_ID and GCP_LOCATION:
    try:
        vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
        vertexai_initialized = True
        logger.info(f"Vertex AI initialized for project '{GCP_PROJECT_ID}' in location '{GCP_LOCATION}'. (Generation Service)")
    except Exception as e:
        logger.error(f"Failed to initialize Vertex AI: {e}", exc_info=True)
else:
    logger.warning("Vertex AI not initialized due to missing configuration or libraries. (Generation Service)")


# --- Helper to clean Gemini JSON output ---
def _clean_gemini_json_output(raw_text: str) -> str:
    """Removes potential markdown code fences and leading/trailing whitespace."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
         text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


async def generate_assignment_questions(
    assignment_format: models.AssignmentFormat,
    lesson_gs_urls: List[str],
    user_id: int, # Added user_id
    action: str,  # Added action
    session_id: Optional[str] = None # Added optional session_id
) -> schemas.GenerateAssignmentResponse:
    """
    Generates assignment questions based on a format and lesson content using Gemini.
    Also logs LLM token usage.
    """
    if not vertexai_initialized or not GenerativeModel or not Part or not GenerationConfig:
        logger.error("generate_assignment_questions called but Vertex AI is not initialized/available.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI generation service is not available or configured correctly."
        )

    if not lesson_gs_urls:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No lesson content URLs provided for generation.")

    # --- Construct Prompt ---
    if not assignment_format.questions:
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                             detail=f"Assignment Format '{assignment_format.name}' (ID: {assignment_format.id}) has no question definitions.")

    question_details = "\n".join([f"- {q.count} questions of type '{q.question_type}'" for q in assignment_format.questions])
    allowed_types_str = ', '.join([qt.value for qt in schemas.QuestionTypeEnum])
    prompt = f"""
Generate a set of assignment questions based on the content of the provided PDF documents and the specified format.

Assignment Format Name: {assignment_format.name}
Required Question Structure:
{question_details}

Instructions:
1. Analyze the content of the following PDF document(s).
2. Generate exactly the specified number of questions for each question type listed in the format.
3. Ensure the questions cover the key topics discussed in the document(s).
4. Format the output ONLY as a single JSON object containing a list named "generated_questions".
5. Each object in the "generated_questions" list must have the following fields:
    - "question_number": (Optional) An integer sequence number for the question (start from 1).
    - "question_type": A string matching one of the allowed types ({allowed_types_str}).
    - "question_text": The full text of the question.
    - "options": (Optional) A list of strings for multiple-choice or matching options. Required for 'single_select', 'multi_select', 'match_following'.
    - "correct_answer": (Optional) The correct answer string, or a list of strings for 'multi_select'. May be omitted for 'short_answer'.
    - "explanation": (Optional) A brief explanation for the correct answer.
    - "reference_page": (Optional) An integer representing the page number in the source PDF where the answer or relevant information can be found. If unsure, omit or set to null.
    - "reference_section": (Optional) A string identifying a relevant section or chapter name from the source PDF, if identifiable. If unsure, omit or set to null.
    - "image_svg": (Optional) If the question intrinsically requires a visual diagram (e.g., geometry, graph, flow chart) that can be simply represented, provide the SVG code as a string. Otherwise, this field MUST be null. Keep SVGs simple.
6. Adhere strictly to the JSON format requested. Do not include explanations or introductory text outside the JSON structure.

PDF Content Files:
{', '.join(lesson_gs_urls)}
"""

    # --- Prepare Content Parts ---
    content_parts = [prompt]
    for gs_url in lesson_gs_urls:
        try:
            content_parts.append(Part.from_uri(mime_type="application/pdf", uri=gs_url))
        except Exception as e:
             logger.error(f"Failed to create Part from URI {gs_url}: {e}", exc_info=True)
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not process lesson content URL: {gs_url}")

    # --- Call Gemini ---
    try:
        model = GenerativeModel(GEMINI_MODEL_NAME)
        generation_config = GenerationConfig(response_mime_type="application/json")

        logger.debug(f"Sending generation request to Gemini model: {GEMINI_MODEL_NAME}")
        response = await model.generate_content_async(
            content_parts,
            generation_config=generation_config
        )
        logger.debug(f"Received response from Gemini. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'NO_CANDIDATES'}")

        # --- Log Token Usage ---
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
                )
                db_log_session = SessionLocal()
                db_log_session.add(token_entry)
                db_log_session.commit()
                logger.info(f"LLM token usage logged for action: {action}, user_id: {user_id}, session_id: {final_session_id}, format_id: {assignment_format.id}")
            else:
                logger.warning(f"LLM usage_metadata not available for action: {action}, user_id: {user_id}, format_id: {assignment_format.id}. Skipping token logging.")
        except Exception as log_exc:
            logger.error(f"Failed to log LLM token usage for action: {action}, user_id: {user_id}, format_id: {assignment_format.id}: {log_exc}")
            if db_log_session:
                db_log_session.rollback()
        finally:
            if db_log_session:
                db_log_session.close()
        # --- End Log Token Usage ---

        if not response.candidates or response.candidates[0].finish_reason != FinishReason.STOP:
            finish_reason_val = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
            finish_reason_str = finish_reason_val.name if hasattr(finish_reason_val, 'name') else str(finish_reason_val)
            logger.error(f"Gemini generation stopped unexpectedly. Reason: {finish_reason_str}")
            raise HTTPException(status_code=500, detail=f"AI generation failed. Reason: {finish_reason_str}")

        # --- Process and Validate Response ---
        raw_response_text = response.text
        logger.debug(f"Gemini raw response text: {raw_response_text}")

        cleaned_response_text = _clean_gemini_json_output(raw_response_text)

        try:
            generated_data = json.loads(cleaned_response_text)
            if "generated_questions" not in generated_data or not isinstance(generated_data["generated_questions"], list):
                 raise ValueError("LLM Response missing 'generated_questions' list.")

            validated_questions: List[schemas.GeneratedQuestion] = []
            for i, q_data in enumerate(generated_data["generated_questions"]):
                try:
                    if "question_number" not in q_data or q_data["question_number"] is None:
                         q_data["question_number"] = i + 1
                    # Ensure optional fields that are empty strings become None
                    if "explanation" in q_data and q_data["explanation"] == "": q_data["explanation"] = None
                    if "reference_section" in q_data and q_data["reference_section"] == "": q_data["reference_section"] = None
                    if "image_svg" in q_data and q_data["image_svg"] == "": q_data["image_svg"] = None
                    validated_questions.append(schemas.GeneratedQuestion(**q_data))
                except ValidationError as item_val_err:
                     logger.warning(f"Validation failed for generated question item {i}: {item_val_err}. Data: {q_data}")
                     continue
            if not validated_questions and generated_data["generated_questions"]:
                raise ValueError("No valid questions remained after validation of the AI model's output.")

            validated_response = schemas.GenerateAssignmentResponse(
                generated_questions=validated_questions,
                raw_llm_output=raw_response_text
            )
            logger.info(f"Successfully generated and validated questions for format {assignment_format.id}.")
            return validated_response

        except (json.JSONDecodeError, ValueError, ValidationError) as val_err:
            logger.error(f"Failed to parse or validate Gemini JSON response: {val_err}\nCleaned response: {cleaned_response_text}\nRaw response: {raw_response_text}")
            raise HTTPException(status_code=500, detail="AI generation service returned invalid or unexpected data format.")

    except Exception as e:
        logger.error(f"Error during Gemini generation for format {assignment_format.id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred during AI generation: {str(e)}")


async def modify_assignment_questions(
    previous_questions: List[Dict[str, Any]],
    modification_instructions: str
    # Consider adding user_id, action, session_id here if token logging is also needed for modifications
) -> schemas.ModifyAssignmentResponse:
    """
    Modifies existing assignment questions based on instructions using Gemini.
    (Token logging not yet implemented for this specific function, can be added similarly if needed)
    """
    if not vertexai_initialized or not GenerativeModel or not GenerationConfig:
        logger.error("modify_assignment_questions called but Vertex AI is not initialized/available.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI modification service is not available or configured correctly."
        )

    if not previous_questions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No previous questions provided for modification.")
    if not modification_instructions:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No modification instructions provided.")

    logger.info(f"Starting AI modification with instructions: {modification_instructions}")

    try:
        previous_questions_json = json.dumps({"generated_questions": previous_questions}, indent=2)
    except TypeError as e:
        logger.error(f"Failed to serialize previous_questions to JSON: {e}")
        raise HTTPException(status_code=500, detail="Internal error processing previous questions.")

    allowed_types_str = ', '.join([qt.value for qt in schemas.QuestionTypeEnum])
    prompt = f"""
You are tasked with modifying an existing set of assignment questions based on user instructions.

Here is the previous set of questions in JSON format:
{previous_questions_json}

Here are the modification instructions:
"{modification_instructions}"

Instructions:
1. Apply the user's modification instructions to the provided questions. This could involve changing question text, options, answers, explanation, references, adding questions, removing questions, or changing question types.
2. Ensure the output ONLY contains the modified set of questions in the exact same JSON format as the input (a single JSON object with a "generated_questions" key containing a list of question objects).
3. Each question object in the list must have the following fields: "question_number", "question_type", "question_text", and optionally "options", "correct_answer", "explanation", "reference_page", "reference_section", "image_svg". Maintain the original "question_type" unless instructed otherwise. Re-number the questions sequentially starting from 1.
4. The allowed values for "question_type" are: "{allowed_types_str}".
5. For the optional fields ("options", "correct_answer", "explanation", "reference_page", "reference_section", "image_svg"), if the information is not available or not applicable after modification, ensure the field is either omitted or set to null in the JSON output. Do not use empty strings for these optional fields unless specifically instructed.
6/ Adhere strictly to the JSON format. Do not include explanations or introductory text outside the JSON structure.

"""


    try:
        model = GenerativeModel(GEMINI_MODEL_NAME)
        generation_config = GenerationConfig(response_mime_type="application/json")
        logger.debug(f"Sending modification request to Gemini model: {GEMINI_MODEL_NAME}")
        response = await model.generate_content_async(
            [prompt],
            generation_config=generation_config
        )
        logger.debug(f"Received modification response from Gemini. Finish reason: {response.candidates[0].finish_reason if response.candidates else 'NO_CANDIDATES'}")

        # (No token logging implemented here yet, but could be added following the pattern above)

        if not response.candidates or response.candidates[0].finish_reason != FinishReason.STOP:
            finish_reason_val = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
            finish_reason_str = finish_reason_val.name if hasattr(finish_reason_val, 'name') else str(finish_reason_val)
            logger.error(f"Gemini modification stopped unexpectedly. Reason: {finish_reason_str}")
            raise HTTPException(status_code=500, detail=f"AI modification failed. Reason: {finish_reason_str}")

        raw_response_text = response.text
        logger.debug(f"Gemini raw modification response text: {raw_response_text}")
        cleaned_response_text = _clean_gemini_json_output(raw_response_text)

        try:
            modified_data = json.loads(cleaned_response_text)
            if "generated_questions" not in modified_data or not isinstance(modified_data["generated_questions"], list):
                 raise ValueError("LLM Response missing 'generated_questions' list.")

            validated_questions: List[schemas.GeneratedQuestion] = []
            for i, q_data in enumerate(modified_data["generated_questions"]):
                try:
                    if "question_number" not in q_data or q_data["question_number"] is None:
                        q_data["question_number"] = i + 1
                    validated_questions.append(schemas.GeneratedQuestion(**q_data))
                except ValidationError as item_val_err:
                     logger.warning(f"Validation failed for modified question item {i}: {item_val_err}. Data: {q_data}")
                     continue

            if not validated_questions and modified_data["generated_questions"]:
                 raise ValueError("No valid questions remained after validation of the AI model's modified output.")
            elif not validated_questions and not modified_data["generated_questions"]:
                 logger.info("AI returned an empty list of questions after modification.")

            validated_response = schemas.ModifyAssignmentResponse(
                generated_questions=validated_questions,
                raw_llm_output=raw_response_text
            )
            logger.info("Successfully modified and validated questions.")
            return validated_response

        except (json.JSONDecodeError, ValueError, ValidationError) as val_err:
            logger.error(f"Failed to parse or validate Gemini JSON modification response: {val_err}\nCleaned response: {cleaned_response_text}\nRaw response: {raw_response_text}")
            raise HTTPException(status_code=500, detail="AI modification service returned invalid or unexpected data format.")
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error during Gemini modification process: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred during AI modification: {str(e)}")