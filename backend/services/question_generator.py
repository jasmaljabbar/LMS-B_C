import os
import json
from typing import List, Dict, Any, Optional # Added Optional
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from datetime import datetime
from dotenv import load_dotenv
import uuid # Added for session_id generation

# Database imports for token logging
from backend.database import SessionLocal
from backend.models import LLMTokenUsage

# Load environment variables
load_dotenv()


class QuestionGenerator:
    def __init__(self):
        # Print environment variables
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("VERTEX_AI_LOCATION")
        model = os.getenv("VERTEX_AI_MODEL")

        print("\nInitializing QuestionGenerator with:")
        print(f"Project ID: {project_id}")
        print(f"Location: {location}")
        print(f"Model: {model}\n")

        # Initialize Vertex AI with project and location from env vars
        vertexai.init(
            project=project_id,
            location=location
        )
        self.model = GenerativeModel(model)

    def _create_system_prompt(self) -> str:
        """Create the system prompt for the AI model"""
        return """You are an expert educational assessment generator. Your task is to:
1. Analyze the provided lesson content
2. Generate questions based on the specified type and count
3. Return questions in a structured JSON format.
4. Include detailed explanations with references to specific sections and pages
5. Generate SVG diagrams when questions require diagrams 

Format each question based on its type:

For fill in the blanks:
{
    "question_text": "Text with ___ for blanks",
    "question_type": "fill_in_blanks",
    "blanks": [{"id": 1, "answer": "correct word"}],
    "explanation": "Why these words fit in the blanks",
    "reference": {
        "section": "Section ID or title",
        "page": "page_number"
    }
}

For match the following:
{
    "question_text": "Match the following items",
    "question_type": "match_following",
    "left_items": [{"id": "A", "text": "left item"}],
    "right_items": [{"id": "1", "text": "right item"}],
    "correct_matches": [{"left": "A", "right": "1"}],
    "explanation": "Explanation of the relationships",
    "reference": {
        "section": "Section ID or title",
        "page": "page_number"
    }
}

For single select:
{
    "question_text": "The question",
    "question_type": "single_select",
    "choices": [{"id": "A", "text": "choice text"}],
    "correct_answer": "A",
    "explanation": "Why this is the correct answer",
    "reference": {
        "section": "Section ID or title",
        "page": "page_number"
    }
}

For multi select:
{
    "question_text": "The question",
    "question_type": "multi_select",
    "choices": [{"id": "A", "text": "choice text"}],
    "correct_answers": ["A", "B"],
    "explanation": "Why these are the correct answers",
    "reference": {
        "section": "Section ID or title",
        "page": "page_number"
    }
}

For short answer:
{
    "question_text": "The question",
    "question_type": "short_answer",
    "model_answer": "The expected answer",
    "keywords": ["key1", "key2"],
    "explanation": "What constitutes a good answer",
    "reference": {
        "section": "Section ID or title",
        "page": "page_number"
    }
}"""

    def _create_question_prompt(self, question_type: str, count: int) -> str:
        """Create a specific prompt for each question type"""
        prompts = {
            "fill_in_blanks": f"Generate {count} fill-in-the-blank questions using key concepts and terminology from the lesson. Each blank should test understanding of important terms or concepts.",
            "match_following": f"Generate {count} matching questions. Create 4-6 pairs of related items that test understanding of relationships between concepts, terms, or cause-and-effect from the lesson.",
            "single_select": f"Generate {count} single-select questions. Each should have 4 options (A-D), with exactly one correct answer. Include plausible distractors based on common misconceptions.",
            "multi_select": f"Generate {count} multiple-select questions. Each should have 5-6 options (A-F), with 2-3 correct answers. Ensure options are clearly distinct and test related concepts.",
            "short_answer": f"Generate {count} short-answer questions that require concise explanations. Include key points that should be present in a good answer."
        }
        return prompts.get(question_type, "")

    async def generate_questions(
            self,
            lesson_urls: List[str],
            question_requests: List[Dict[str, Any]],
            user_id: int, # New parameter
            action: str,  # New parameter
            session_id: Optional[str] = None # New parameter
    ) -> Dict[str, Any]:
        """Generate questions based on lesson content and specified question types, and log token usage."""

        # Convert GCS URLs to Vertex AI Parts
        lesson_parts = [Part.from_uri(url, mime_type="application/pdf") for url in lesson_urls]

        # Create a combined prompt for all question types
        combined_prompt = self._create_system_prompt() + "\n\n"
        combined_prompt += "Generate the following questions:\n"

        for request in question_requests:
            question_type = request["type"]
            count = request["count"]
            combined_prompt += f"\n{self._create_question_prompt(question_type, count)}"

        combined_prompt += "\n\nAnalyze the provided lesson content and generate ALL requested questions in a single JSON array. Each question should follow the format specified above for its type."

        response_obj = None # To store the actual response object from generate_content_async
        response_text_for_error_logging = "" # To store response.text for error logging if parsing fails

        try:
            # Generate content using Vertex AI with all questions at once
            contents = [combined_prompt] + lesson_parts

            response_obj = await self.model.generate_content_async(
                contents,
                generation_config={
                    "max_output_tokens": 8192,
                    "temperature": 0.7,
                    "top_p": 0.8,
                    "top_k": 40
                }
            )

            # Log token usage
            db_log = None
            try:
                if hasattr(response_obj, 'usage_metadata') and response_obj.usage_metadata:
                    prompt_tokens = response_obj.usage_metadata.prompt_token_count
                    candidate_tokens = response_obj.usage_metadata.candidates_token_count
                    total_tokens = prompt_tokens + candidate_tokens

                    final_session_id = session_id if session_id else str(uuid.uuid4())
                    model_name_to_log = os.getenv("VERTEX_AI_MODEL", self.model.model_name if hasattr(self.model, 'model_name') else "unknown_gemini_model")


                    token_entry = LLMTokenUsage(
                        user_id=user_id,
                        session_id=final_session_id,
                        action=action,
                        model_name=model_name_to_log,
                        input_tokens=prompt_tokens,
                        output_tokens=candidate_tokens,
                        total_tokens=total_tokens
                        # timestamp is server_default
                    )
                    db_log = SessionLocal()
                    db_log.add(token_entry)
                    db_log.commit()
                else:
                    print(f"Warning: usage_metadata not found for action '{action}', user_id '{user_id}'. Skipping token logging.")
            except Exception as log_exc:
                print(f"Error logging token usage for action '{action}', user_id '{user_id}': {log_exc}")
                if db_log:
                    db_log.rollback()
            finally:
                if db_log:
                    db_log.close()
            
            response_text_for_error_logging = response_obj.text
            # Clean up response text by removing markdown code block markers
            text = response_obj.text
            text = text.replace("```json", "").replace("```", "").strip()

            # Parse the response into JSON
            questions = json.loads(text)

            all_questions = questions if isinstance(questions, list) else [questions]

            return {
                "timestamp": datetime.now().isoformat(), # This is generation timestamp, not logging timestamp
                "total_questions": len(all_questions),
                "questions": all_questions
            }

        except Exception as e:
            # Using response_text_for_error_logging which holds the raw text before parsing
            raise ValueError(f"Error generating questions for action '{action}', user_id '{user_id}': {str(e)}\n AI generated response: \n {response_text_for_error_logging}")

async def main():
    """Test the question generator with sample data"""
    try:
        # Initialize the generator
        generator = QuestionGenerator()

        # Actual lesson URLs from GCS bucket
        lesson_urls = [
            "gs://lms-ai/pdfs/geography_010-Europe.pdf",
            "gs://lms-ai/pdfs/geography_011-Australia.pdf"
        ]

        # Geography-focused question requests
        question_requests = [
            {"type": "fill_in_blanks", "count": 3},  # For capitals, countries, landmarks
            {"type": "match_following", "count": 2},  # For matching countries with features
            {"type": "single_select", "count": 3},  # For testing geographical knowledge
            {"type": "multi_select", "count": 2},  # For multiple correct features/characteristics
            {"type": "short_answer", "count": 2}  # For explaining geographical concepts
        ]

        print("Generating questions...")
        # Example usage for generate_questions - user_id, action, session_id added
        result = await generator.generate_questions(
            lesson_urls, 
            question_requests,
            user_id=1, # Example user_id
            action="generate_questions_main_test", # Example action
            session_id=str(uuid.uuid4()) # Example session_id
        )

        print("\nGenerated Questions:")
        print(f"Timestamp: {result['timestamp']}")
        print(f"Total Questions: {result['total_questions']}")

        # Print each question with nice formatting
        for i, question in enumerate(result['questions'], 1):
            print(f"\nQuestion {i}:")
            print(f"Type: {question['question_type']}")
            print(f"Question: {question['question_text']}")

            if question['question_type'] == 'math':
                print("Steps Required:")
                for step in question['steps_required']:
                    print(f"- {step}")
                print(f"Answer: {question['correct_answer']}")
                if question.get('diagram_svg'):
                    print("(Contains diagram)")

            elif question['question_type'] == 'fill_in_blanks':
                print("Blanks:")
                for blank in question['blanks']:
                    print(f"- Blank {blank['id']}: {blank['answer']}")

            elif question['question_type'] == 'match_following':
                print("Matching Items:")
                for left, right in zip(question['left_items'], question['right_items']):
                    print(f"- {left['text']} → {right['text']}")

            elif question['question_type'] in ['single_select', 'multi_select']:
                print("Choices:")
                for choice in question['choices']:
                    print(f"- {choice['id']}: {choice['text']}")
                print(f"Correct Answer(s): {question.get('correct_answer') or question.get('correct_answers')}")

            elif question['question_type'] == 'short_answer':
                print(f"Model Answer: {question['model_answer']}")
                print("Keywords:", ", ".join(question['keywords']))

            print(f"Reference: Section {question['reference']['section']}, Page {question['reference']['page']}")
            print("-" * 80)

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    import asyncio

    # Set environment variables for testing
    os.environ["GOOGLE_CLOUD_PROJECT"] = "vipin-workspace"
    os.environ["VERTEX_AI_LOCATION"] = "us-central1"
    os.environ["VERTEX_AI_MODEL"] = "gemini-2.5-pro-exp-03-25"

    # Run the async main function
    asyncio.run(main())
