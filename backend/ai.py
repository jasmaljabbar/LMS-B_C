import vertexai
from vertexai.generative_models import GenerativeModel, Part, ChatSession
from google.cloud import storage
import mimetypes
from typing import Dict, Tuple, List, Set, Optional, Union, Any, LiteralString
import threading
import hashlib
import os
from dotenv import load_dotenv
import json
import re

# Database imports for token logging
from backend.database import SessionLocal
from backend.models import LLMTokenUsage
# User model is not directly used here if user_id is passed,
# but good to keep in mind if context changes.
# from backend.models import User
# No need to import datetime if relying on server_default for timestamp in LLMTokenUsage

load_dotenv()


class ChatManager:
    """Manages chat sessions, optimizing for file reuse, system instructions, and parallel sessions per user."""

    def __init__(self, project_id: str, location: str, model_name: str):
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.model = GenerativeModel(model_name)
        # Store sessions using a tuple (user_id, session_id) as the key
        self.sessions: Dict[Tuple[str, str], ChatSession] = {}
        self.lock = threading.Lock()
        # Store file hashes per session (using (user_id, session_id) tuple as key)
        self.processed_files: Dict[Tuple[str, str], Set[str]] = {}

    def get_or_create_session(self, user_id: str, session_id: str) -> ChatSession:
        """Gets a specific chat session.  Creates it if it doesn't exist."""
        with self.lock:
            if (user_id, session_id) not in self.sessions:
                new_session = self.model.start_chat()
                self.sessions[(user_id, session_id)] = new_session
                self.processed_files[(user_id, session_id)] = set()
                return new_session
            else:
                return self.sessions[(user_id, session_id)]

    def _file_hash(self, file_bytes: bytes) -> str:
        """Calculates the SHA256 hash of file content."""
        return hashlib.sha256(file_bytes).hexdigest()

    def generate_answer(
            self,
            user_id: str,
            session_id: str,
            files: List[Dict[str, str]],  # List of dictionaries: {gs_uri: mime_type}
            question: str,
            system_instruction: str = None,
            action: str = "unknown_action",  # New parameter with a default
    ) -> str:
        """
        Generates an answer within a specific session, reusing files, and logs token usage.
        Now returns only the answer string.
        """

        chat_session = self.get_or_create_session(user_id, session_id)  # Get or create
        # No need to check chat_session for None.

        # parts = []
        # storage_client = storage.Client()

        parts = []
        if os.getenv("GCP_ENV", "false").lower() == "true":
            storage_client = storage.Client()
            print("✅ Google Cloud Storage client initialized")
        else:
            storage_client = None
            print("⚠️ Skipping GCS client initialization in local development")


        if system_instruction:
            parts.append(Part.from_text(system_instruction))

        for file_info in files:
            for gs_uri, mime_type in file_info.items():  # Iterate through the dictionary
                try:
                    path_parts = gs_uri.replace("gs://", "").split("/", 1)
                    bucket_name = path_parts[0]
                    blob_name = path_parts[1]

                    bucket = storage_client.bucket(bucket_name)
                    blob = bucket.blob(blob_name)
                    file_bytes = blob.download_as_bytes()
                    file_hash_str = self._file_hash(file_bytes)

                    with self.lock:
                        if file_hash_str not in self.processed_files[(user_id, session_id)]:
                            if not mime_type:  # If mime_type is empty
                                inferred_mime_type, _ = mimetypes.guess_type(gs_uri)
                                if inferred_mime_type is None:
                                    raise ValueError(f"MIME type is required for {gs_uri} and could not be inferred.")
                                mime_type = inferred_mime_type
                            parts.append(Part.from_data(data=file_bytes, mime_type=mime_type))
                            self.processed_files[(user_id, session_id)].add(file_hash_str)

                except Exception as e:
                    raise ValueError(f"Error processing file {gs_uri}: {e}") from e

        parts.append(Part.from_text(question))

        try:
            response = chat_session.send_message(parts)

            # Log token usage
            db = None  # Initialize db to None for finally block
            try:
                if hasattr(response, 'usage_metadata') and response.usage_metadata:
                    prompt_tokens = response.usage_metadata.prompt_token_count
                    candidates_tokens = response.usage_metadata.candidates_token_count
                    total_tokens = prompt_tokens + candidates_tokens

                    db = SessionLocal()
                    token_usage_entry = LLMTokenUsage(
                        user_id=int(user_id) if user_id.isdigit() else None, # Assuming user_id can be converted to int
                        session_id=session_id,
                        action=action,
                        model_name=self.model_name,
                        input_tokens=prompt_tokens,
                        output_tokens=candidates_tokens,
                        total_tokens=total_tokens
                        # timestamp is server_default
                    )
                    db.add(token_usage_entry)
                    db.commit()
                else:
                    # Log or handle missing usage_metadata if necessary
                    print(f"Warning: usage_metadata not found for action '{action}', user_id '{user_id}', session_id '{session_id}'. Skipping token logging.")
            except Exception as log_exc:
                # Log any exception during token logging but don't let it fail the main operation
                print(f"Error logging token usage: {log_exc}")
                if db:
                    db.rollback() # Rollback in case of error during logging
            finally:
                if db:
                    db.close()

            return response.text  # Return only the answer text

        except Exception as e:
            # It might be good to log the action that failed here too if possible
            raise ValueError(f"Vertex AI model failed to generate content for action '{action}': {e}") from e

    def clear_session(self, user_id: str, session_id: str) -> None:
        """Clears a specific chat session and its processed files."""
        with self.lock:
            if (user_id, session_id) in self.sessions:
                del self.sessions[(user_id, session_id)]
                del self.processed_files[(user_id, session_id)]
                print(f"Cleared session {session_id} for user {user_id}")

    def clear_all_sessions_for_user(self, user_id: str) -> None:
        """Clears all chat sessions for a given user."""
        with self.lock:
            keys_to_remove = [k for k in self.sessions if k[0] == user_id]
            for key in keys_to_remove:
                del self.sessions[key]
                del self.processed_files[key]
            print(f"Cleared all sessions for user {user_id}")


class VirtualTeacherClient:
    """Client class for interacting with the virtual teacher functionality."""

    def __init__(self, project_id: str, location: str, model_name: str = "gemini-1.5-pro-002"):
        self.project_id = project_id
        self.location = location
        self.model_name = model_name
        self.chat_manager = ChatManager(project_id, location, model_name)
        vertexai.init(project=project_id, location=location)

    def ask_question(
            self,
            user_id: str,
            session_id: str,  # Session ID is now *required*
            question: str,
            files: Optional[List[Dict[str, str]]] = None,  # Now expects List[Dict[str, str]]
            system_instruction: Optional[str] = None,
            action: str = "ask_question_via_client", # Default action for this method
    ) -> str:
        """
        Asks a question, automatically creating or reusing a session, and logs token usage.
        """
        files = files or []
        answer = self.chat_manager.generate_answer(
            user_id, session_id, files, question, system_instruction, action=action
        )
        return answer

    def get_or_create_session(self, user_id: str, session_id: str) -> ChatSession:
        """Gets a specific chat session.  Creates it if it doesn't exist."""
        return self.chat_manager.get_or_create_session(user_id, session_id)

    def clear_session(self, user_id: str, session_id: str) -> None:
        """Clears a specific session."""
        self.chat_manager.clear_session(user_id, session_id)

    def clear_all_sessions_for_user(self, user_id: str) -> None:
        """Clears all sessions for a user."""
        self.chat_manager.clear_all_sessions_for_user(user_id)


####################################
# Initialize Virtual Teacher Client
####################################
project_id = os.environ.get("PROJECT_ID")
location = os.environ.get("LOCATION")
model_name = os.environ.get("MODEL_NAME", "gemini-1.5-pro-002")
bucket_name = os.environ.get("BUCKET_NAME")  # Still needed for file access

if not all([project_id, location]):
    raise ValueError(
        "Please set PROJECT_ID and LOCATION in your .env file."
    )

# --- Initialize the client ---
client = VirtualTeacherClient(project_id, location, model_name)


def ask_question(
        user_id: str,
        session_id: str,
        question: str,
        files: List[Dict[str, str]]
):
    system_instruction = """
        You are an Expert Teacher. 
        Use the information in the given context to answer the questions.
    """
    answer = client.ask_question(user_id, session_id, question, files, system_instruction, action="ask_question")

    return answer


def generate_teacher_notes(
        user_id: str,
        session_id: str,
        user_prompt: str,
        files: List[Dict[str, str]]
):
    system_instruction = """
        Use the information in the given context.
        Generate a detailed notes for the teacher.
        Teacher will use this notes to conduct the training for the students.
    """
    answer = client.ask_question(user_id, session_id, user_prompt, files, system_instruction, action="generate_teacher_notes")

    return answer


def generate_bulk_assessment_questions(
        user_id: str,
        session_id: str,
        user_instruction: str,
        number_of_questions: int,
        files: List[Dict[str, str]]
):
    system_instruction = f"""
        Based on the given context, generate {number_of_questions} questions. 
        Questions can be mix of multi-choice and/or multi-selection questions.
        There must be 4 choices.
    """
    answer = client.ask_question(user_id, session_id, user_instruction, files, system_instruction, action="generate_bulk_assessment_questions")

    return answer


def json_markdown_to_dict(markdown_string):
    """
    Converts a JSON markdown string (enclosed in ```json ... ```) to a Python dictionary.

    Args:
        markdown_string: The string containing the JSON data within markdown code blocks.

    Returns:
        A Python dictionary representing the parsed JSON, or None if:
            - No JSON block is found.
            - The extracted content is not valid JSON.
    """
    # Extract the JSON string using a regular expression
    match = re.search(r"```json\s*([\s\S]*?)\s*```", markdown_string)
    if not match:
        return None  # No JSON block found

    json_string = match.group(1).strip()

    # Parse the JSON string and handle potential errors
    try:
        data = json.loads(json_string)
        return data
    except json.JSONDecodeError:
        return None  # Invalid JSON


def json_markdown_to_string(markdown_string):
    """
    Converts a JSON markdown string (enclosed in ```json ... ```) to a Python String.

    Args:
        markdown_string: The string containing the JSON data within markdown code blocks.

    Returns:
        A Python dictionary representing the parsed JSON, or None if:
            - No JSON block is found.
            - The extracted content is not valid JSON.
    """
    # Extract the JSON string using a regular expression
    match = re.search(r"```json\s*([\s\S]*?)\s*```", markdown_string)
    if not match:
        return None  # No JSON block found

    json_string = match.group(1).strip()
    return json_string


def generate_assessment_question(
        user_id: str,
        session_id: str,
        previous_question_answer: str,
        files: List[Dict[str, str]],
        total_question_count: int,
        current_question_count: int
):
    system_instruction = f"""
        Based on the given context, generate question. 
        Questions can be mix of multi-choice and/or multi-selection questions.
        There must be 4 choices.

        If previous question's answer is incorrect, generate little easier question.
        If it is correct, generate little harder question.
        """
    user_prompt = f"""
        The question format must be in JSON format with following fields:
          "question": "generated question goes here",
          "choices": [FOUR choices must go here],
          "choice_type": "multi-choice or multi-select",
          "correct_answer": "correct answer for this question",
          "correct_answer_for_previous_question": "correct answer of previous question",,
          "your_previous_answer": "{previous_question_answer}"
    """
    answer = client.ask_question(user_id, session_id, user_prompt, files, system_instruction, action="generate_assessment_question")

    return json_markdown_to_dict(answer)


def generate_question_paper(
        question_format_gcs_url: str,
        lesson_gcs_urls: List[str],
        user_id: str,
        session_id: str,
        project_id: str = os.getenv("PROJECT_ID"),
        location: str = os.getenv("LOCATION")
) -> LiteralString | None:
    """
    Generate a question paper in JSON format based on the provided question format and lessons PDFs.
    Uses ChatManager to handle the conversation with Gemini.

    Args:
        question_format_gcs_url (str): GCS URL for the question format PDF
        lesson_gcs_urls (List[str]): List of GCS URLs for the lesson PDFs
        user_id (str): User ID for the chat session
        session_id (str): Session ID for the chat session
        project_id (str, optional): Google Cloud project ID. Defaults to PROJECT_ID env var.
        location (str, optional): Google Cloud location. Defaults to LOCATION env var.

    Returns:
        Dict[str, Any]: JSON formatted question paper
    """
    # Initialize ChatManager
    chat_manager = ChatManager(
        project_id=project_id,
        location=location,
        model_name=model_name
    )

    #####################################
    # Generate question format json.
    #######################################

    # Prepare files list in the format expected by ChatManager
    files = [
        {question_format_gcs_url: "application/pdf"}
    ]

    # Prepare prompt
    prompt = """
    Use the given pdf as sample Question Paper format. 
    When I provide lesson(s), generate question paper for the provided lessons.
    Generate a structured JSON output containing questions that follow the question paper format provided.
    If question requires an image, include it in svg format. 
    Provide answer for the given question.
    Also provide question type such as math, fill_in_the_blanks, match_the_following, multiple choice, multiple select, short answer, etc
    The output must be valid JSON that can be parsed by Python's json.loads().
    """
    response = chat_manager.generate_answer( # This is the first call in generate_question_paper
        user_id=user_id,
        session_id=session_id,
        files=files,
        question=prompt,
        action="generate_question_paper_format_prompt" 
    )

    # Prepare files list in the format expected by ChatManager
    files = [
        {url: "application/pdf"} for url in lesson_gcs_urls
    ]

    # Prepare prompt
    prompt = """
    Generate question paper for these lessons.
    """

    # Generate question paper using ChatManager
    response = chat_manager.generate_answer( # This is the second call in generate_question_paper
        user_id=user_id,
        session_id=session_id,
        files=files,
        question=prompt,
        action="generate_question_paper_main_prompt"
    )

    try:
        # Parse the response and ensure it's valid JSON
        return json_markdown_to_string(response)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Failed to generate valid JSON question paper")


def generate_question_paper2(
        question_format_gcs_url: str,
        lesson_gcs_urls: List[str],
        user_id: str,
        session_id: str,
        project_id: str = os.getenv("PROJECT_ID"),
        location: str = os.getenv("LOCATION")
) -> LiteralString | None:
    """
    Generate a question paper in JSON format based on the provided question format and lessons PDFs.
    Uses ChatManager to handle the conversation with Gemini.

    Args:
        question_format_gcs_url (str): GCS URL for the question format PDF
        lesson_gcs_urls (List[str]): List of GCS URLs for the lesson PDFs
        user_id (str): User ID for the chat session
        session_id (str): Session ID for the chat session
        project_id (str, optional): Google Cloud project ID. Defaults to PROJECT_ID env var.
        location (str, optional): Google Cloud location. Defaults to LOCATION env var.

    Returns:
        Dict[str, Any]: JSON formatted question paper
    """
    # Initialize ChatManager
    chat_manager = ChatManager(
        project_id=project_id,
        location=location,
        model_name=model_name
    )

    # Prepare files list in the format expected by ChatManager
    files = [
        {url: "application/pdf"} for url in lesson_gcs_urls
    ]

    # Prepare prompt
    prompt = """
    Providing you lessons in a PDF file. Analyze the PDF and generate questions in the below format.
    I need to add the questions array that you generate in my application to render in UI.
    Format:
    const allQuestions = [
    { id: 'fill-2', type: 'fill',
    question: "____ is the largest planet in our solar system, while ____ is the smallest.",
    blanks: [{ id: 'b2-1', answer: "Jupiter" },
    { id: 'b2-2', answer: "Mercury" }],
    },
    { id: 'image-1',
    type: 'image',
    imageUrl: '/images/question1.svg',
    question: "The speed-time graph shows information about a bus journey. Calculate the total distance travelled by the bus (in meters).",
    answer: "2325"
    },
    { id: 'match-1', type: 'match', title: 'Match the Biological Processes', prompt: 'Drag the description to the corresponding term.', pairs: [{ id: 'term-m1-1', text: 'Photosynthesis', correctMatchId: 'item-m1-2' }, { id: 'term-m1-2', text: 'Respiration', correctMatchId: 'item-m1-3' }, { id: 'term-m1-3', text: 'Osmosis', correctMatchId: 'item-m1-1' }, { id: 'term-m1-4', text: 'Diffusion', correctMatchId: 'item-m1-4' }], items: [{ id: 'item-m1-1', text: 'Movement of water molecules' }, { id: 'item-m1-2', text: 'Production of glucose' }, { id: 'item-m1-3', text: 'Release of energy from food' }, { id: 'item-m1-4', text: 'Movement of particles' }] },
    { id: 'fill-3', type: 'fill',
    question: "____ is the capital of France and ____ invented the telephone.",
    blanks: [{ id: 'b3-1', answer: "Paris" }, { id: 'b3-2', answer: "Alexander Graham Bell" }],
    },
    { id: 'image-2', type: 'image', imageUrl: '/images/question20.png', question: "Calculate the area of triangle ABC (in cm², rounded to 1 decimal place).", answer: "5.4" },
    { id: 'match-2', type: 'match', title: 'Match the Countries and Capitals', prompt: 'Drag the capital city to the corresponding country.', pairs: [{ id: 'term-m2-1', text: 'France', correctMatchId: 'item-m2-1' }, { id: 'term-m2-2', text: 'Japan', correctMatchId: 'item-m2-2' }, { id: 'term-m2-3', text: 'Egypt', correctMatchId: 'item-m2-3' }, { id: 'term-m2-4', text: 'Canada', correctMatchId: 'item-m2-4' }], items: [{ id: 'item-m2-1', text: 'Paris' }, { id: 'item-m2-2', text: 'Tokyo' }, { id: 'item-m2-3', text: 'Cairo' }, { id: 'item-m2-4', text: 'Ottawa' }] },
    { id: 'fill-4', type: 'fill', question: "The process of photosynthesis converts light energy into ____ energy.", blanks: [{ id: 'b4-1', answer: "chemical" }], },
    ];
    Understand the format , give me same format of questions.
    For now, generate below question types:
    Fill ups
    Match the following
    image based
    """

    # Generate question paper using ChatManager
    response = chat_manager.generate_answer(
        user_id=user_id,
        session_id=session_id,
        files=files,
        question=prompt,
        action="generate_question_paper_v2"
    )

    try:
        # Parse the response and ensure it's valid JSON
        return json_markdown_to_string(response)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("Failed to generate valid JSON question paper")

if __name__ == "__main__":
    math_qp3 = generate_question_paper2(
        question_format_gcs_url="gs://lms-ai/pdfs/qp_geography.pdf",
        lesson_gcs_urls=[
            "gs://lms-ai/pdfs/geography_010-Europe.pdf",
            "gs://lms-ai/pdfs/geography_011-Australia.pdf"
        ],
        user_id="1",
        session_id="2"
    )

    math_qp2 = generate_question_paper(
        question_format_gcs_url="gs://lms-ai/pdfs/qp_geography.pdf",
        lesson_gcs_urls=[
            "gs://lms-ai/pdfs/geography_010-Europe.pdf",
            "gs://lms-ai/pdfs/geography_011-Australia.pdf"
        ],
        user_id="1",
        session_id="2"
    )

    math_qp1 = generate_question_paper(
        question_format_gcs_url="gs://lms-ai/pdfs/0580_m24_qp_22 jan feb.pdf",
        lesson_gcs_urls=["gs://lms-ai/pdfs/Trignometry.pdf", "gs://lms-ai/pdfs/Circles.pdf"],
        user_id="1",
        session_id="1"
    )

    files2 = [
        {
            "gs://lms-ai/books/igcse/math/jemh101.pdf": "application/pdf"
        }
    ]

    notes1 = generate_teacher_notes(
        "user1",
        "session1",
        "Summarize the lesson, ",
        files2
    )

    question1 = generate_assessment_question(
        "user1",
        "session1",
        "",
        files2,
        10,
        1
    )
    question2 = generate_assessment_question(
        "user1",
        "session1",
        "2",
        files2,
        10,
        2

    )

    questions = generate_bulk_assessment_questions(
        "user1",
        "session1",
        "Summarize the lesson, ",
        10,
        files2
    )

    answer2 = ask_question(
        "user1",
        "session1",
        "Summarize the lesson, ",
        files2
    )

    print(answer2)

    answer3 = ask_question(
        "user1",
        "session1",
        "Explain Euclid’s division algorithm in detail with examples",
        files2
    )

    print(answer3)

    files1 = [
        {
            "gs://lms-ai/videos/math/O level Math - Angle properties of Circles Part 1.mp4": "video/mp4"
        }
    ]

    answer1 = ask_question(
        "user1",
        "session1",
        "Summarize the lesson, ",
        files1
    )

    print(answer1)
