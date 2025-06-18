import unittest
from unittest.mock import patch, MagicMock, ANY

from backend.ai import ChatManager # Assuming ChatManager is directly importable
from backend.models import LLMTokenUsage # To check the instance type
# Assuming SessionLocal is used like: db = SessionLocal()
# If it's a context manager (with SessionLocal() as db:), mocking might be different

# Mock for response.usage_metadata
class MockUsageMetadata:
    def __init__(self, prompt_tokens, candidate_tokens):
        self.prompt_token_count = prompt_tokens
        self.candidates_token_count = candidate_tokens

class TestChatManagerTokenLogging(unittest.TestCase):

    def setUp(self):
        # Initialize ChatManager with dummy values as they are not critical for this specific test's focus
        # if they are not used in the token logging part of generate_answer
        self.chat_manager = ChatManager(project_id="test-project", location="test-location", model_name="test-model")

    @patch('backend.ai.SessionLocal') # Mock SessionLocal where it's used in ai.py
    @patch('vertexai.generative_models.ChatSession.send_message') # Mock the actual send_message
    def test_generate_answer_logs_token_usage(self, mock_send_message, mock_session_local):
        # A. Mock setup
        # 1. Configure mock_send_message
        mock_response = MagicMock()
        mock_response.usage_metadata = MockUsageMetadata(prompt_tokens=100, candidate_tokens=150)
        mock_response.text = "Test AI answer"
        mock_send_message.return_value = mock_response

        # 2. Configure mock_session_local (the DB session)
        mock_db_session = MagicMock()
        mock_session_local.return_value = mock_db_session

        # B. Call the method
        user_id_str = "123"
        session_id_str = "test_session_abc"
        action_str = "test_action"
        
        # For this test, files and question content don't critically affect token logging logic itself,
        # as long as send_message is mocked.
        files_data = [] 
        question_text = "What is AI?"

        # Patching self.chat_manager.get_or_create_session to return a mock ChatSession
        # that has the mocked send_message
        mock_chat_session_instance = MagicMock()
        mock_chat_session_instance.send_message.return_value = mock_response
        
        with patch.object(self.chat_manager, 'get_or_create_session', return_value=mock_chat_session_instance):
            generated_text = self.chat_manager.generate_answer(
                user_id=user_id_str,
                session_id=session_id_str,
                files=files_data,
                question=question_text,
                action=action_str
            )

        # C. Assertions
        self.assertEqual(generated_text, "Test AI answer")

        # Assert that SessionLocal was called to get a db session
        mock_session_local.assert_called_once()

        # Assert that db.add was called once
        mock_db_session.add.assert_called_once()
        
        # Inspect the object passed to db.add
        added_object = mock_db_session.add.call_args[0][0]
        self.assertIsInstance(added_object, LLMTokenUsage)
        
        # Verify attributes of the LLMTokenUsage instance
        self.assertEqual(added_object.user_id, int(user_id_str))
        self.assertEqual(added_object.session_id, session_id_str)
        self.assertEqual(added_object.action, action_str)
        self.assertEqual(added_object.model_name, self.chat_manager.model_name) # or "test-model"
        self.assertEqual(added_object.input_tokens, 100)
        self.assertEqual(added_object.output_tokens, 150)
        self.assertEqual(added_object.total_tokens, 250) # 100 + 150

        # Assert that db.commit was called once
        mock_db_session.commit.assert_called_once()

        # Assert that db.close was called
        mock_db_session.close.assert_called_once()

    @patch('backend.ai.SessionLocal')
    @patch('vertexai.generative_models.ChatSession.send_message')
    def test_generate_answer_handles_missing_usage_metadata(self, mock_send_message, mock_session_local):
        # A. Mock setup
        mock_response = MagicMock()
        # Simulate response without usage_metadata or with it being None
        # Option 1: del mock_response.usage_metadata (if it's an attribute that can be deleted)
        # Option 2: mock_response.usage_metadata = None (safer)
        mock_response.usage_metadata = None 
        mock_response.text = "Test AI answer without metadata"
        mock_send_message.return_value = mock_response

        mock_db_session = MagicMock()
        mock_session_local.return_value = mock_db_session
        
        mock_chat_session_instance = MagicMock()
        mock_chat_session_instance.send_message.return_value = mock_response

        with patch.object(self.chat_manager, 'get_or_create_session', return_value=mock_chat_session_instance):
            generated_text = self.chat_manager.generate_answer(
                user_id="user_no_meta",
                session_id="session_no_meta",
                files=[],
                question="A question?",
                action="action_no_meta"
            )
        
        self.assertEqual(generated_text, "Test AI answer without metadata")
        mock_session_local.assert_not_called() # DB Session should not be initiated for logging
        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_not_called()
        mock_db_session.close.assert_not_called() # db is not even created in this path

if __name__ == '__main__':
    unittest.main()
