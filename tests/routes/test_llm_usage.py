import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator, Any, List # Added List
from datetime import datetime, timedelta, date # Added date and timedelta

from backend.main import app # Main FastAPI app
from backend.database import Base, get_db
from backend.models import User, LLMTokenUsage # Import your models
from backend.schemas import UserInfo, LLMTokenUsageInfo # Import your Pydantic schemas
from backend.dependencies import get_current_active_user # To override

# --- Test Database Setup ---
SQLALCHEMY_DATABASE_URL_TEST = "sqlite:///./test.db" # Use SQLite for testing
engine_test = create_engine(SQLALCHEMY_DATABASE_URL_TEST, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

# Create tables in the test database
Base.metadata.create_all(bind=engine_test)

# --- Dependency Override for DB Session ---
def override_get_db() -> Generator[Session, Any, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# --- Test Client ---
client = TestClient(app)

# --- Mock User Data ---
mock_user_normal = User(id=1, username="testuser", email="test@example.com", user_type="student", is_active=True)
mock_user_admin = User(id=2, username="adminuser", email="admin@example.com", user_type="admin", is_active=True)
mock_user_other = User(id=3, username="otheruser", email="other@example.com", user_type="student", is_active=True)


# --- Fixture for Test DB Cleanup ---
@pytest.fixture(autouse=True)
def cleanup_db():
    # Run before each test
    Base.metadata.create_all(bind=engine_test) # Ensure tables are created
    # Run test
    yield
    # Run after each test
    Base.metadata.drop_all(bind=engine_test) # Drop all tables to clean up


# --- Helper to create token usage entries ---
def create_token_usage_entry(db: Session, user_id: int, timestamp: datetime, action: str = "test_action", input_tokens: int = 10, output_tokens: int = 20):
    entry = LLMTokenUsage(
        user_id=user_id,
        timestamp=timestamp,
        action=action,
        model_name="test_model",
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        session_id=f"session_for_user_{user_id}"
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

# --- Tests for /llm-usage/me/ ---

def test_read_own_llm_token_usage_unauthorized():
    response = client.get("/llm-usage/me/")
    assert response.status_code == 401 # Expecting 401 Unauthorized

def test_read_own_llm_token_usage_no_data():
    def override_get_current_active_user_normal():
        return mock_user_normal
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user_normal
    
    response = client.get("/llm-usage/me/")
    assert response.status_code == 200
    assert response.json() == []
    
    app.dependency_overrides.pop(get_current_active_user) # Clean up override

def test_read_own_llm_token_usage_with_data():
    db = TestingSessionLocal()
    # Create data for the current user
    now = datetime.utcnow()
    entry1 = create_token_usage_entry(db, mock_user_normal.id, now - timedelta(days=1), action="action1")
    entry2 = create_token_usage_entry(db, mock_user_normal.id, now, action="action2")
    # Create data for another user (should not be returned)
    create_token_usage_entry(db, mock_user_other.id, now, action="action_other_user")
    db.close()

    def override_get_current_active_user_normal():
        return mock_user_normal
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user_normal

    response = client.get("/llm-usage/me/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    # Results are ordered by timestamp desc
    assert data[0]["action"] == "action2"
    assert data[1]["action"] == "action1"
    assert data[0]["user_id"] == mock_user_normal.id
    
    app.dependency_overrides.pop(get_current_active_user)

def test_read_own_llm_token_usage_with_date_filters():
    db = TestingSessionLocal()
    user_id = mock_user_normal.id
    # Data points
    # Dates are important here. The API expects 'date' objects for start/end_date queries.
    # Timestamps in DB are datetime.
    # API converts query param 'date' to datetime at midnight for comparison.
    # end_date filter is exclusive of the next day ( < end_date + 1 day at 00:00:00 )
    
    # today = date.today() -> This uses local time, API uses UTC. Better to use specific dates.
    date_minus_2 = datetime(2024, 1, 1, 10, 0, 0) # Jan 1st
    date_minus_1 = datetime(2024, 1, 2, 10, 0, 0) # Jan 2nd
    date_today = datetime(2024, 1, 3, 10, 0, 0)   # Jan 3rd
    
    entry1 = create_token_usage_entry(db, user_id, date_minus_2, action="action_jan1") # Should be included by start_date=2024-01-01
    entry2 = create_token_usage_entry(db, user_id, date_minus_1, action="action_jan2") # Should be included by start_date=2024-01-01, end_date=2024-01-02
    entry3 = create_token_usage_entry(db, user_id, date_today, action="action_jan3")   # Should be included by end_date=2024-01-03
    db.close()

    def override_get_current_active_user_normal():
        return mock_user_normal
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user_normal

    # Test 1: Filter by start_date
    response_start = client.get("/llm-usage/me/?start_date=2024-01-02")
    assert response_start.status_code == 200
    data_start = response_start.json()
    assert len(data_start) == 2 # entry2 and entry3
    actions_start = {item['action'] for item in data_start}
    assert "action_jan2" in actions_start
    assert "action_jan3" in actions_start

    # Test 2: Filter by end_date
    response_end = client.get("/llm-usage/me/?end_date=2024-01-02")
    assert response_end.status_code == 200
    data_end = response_end.json()
    assert len(data_end) == 2 # entry1 and entry2
    actions_end = {item['action'] for item in data_end}
    assert "action_jan1" in actions_end
    assert "action_jan2" in actions_end
    
    # Test 3: Filter by start_date and end_date
    response_both = client.get("/llm-usage/me/?start_date=2024-01-02&end_date=2024-01-02")
    assert response_both.status_code == 200
    data_both = response_both.json()
    assert len(data_both) == 1
    assert data_both[0]["action"] == "action_jan2"

    app.dependency_overrides.pop(get_current_active_user)


# --- Tests for /llm-usage/user/{user_id}/ ---

def test_read_user_llm_token_usage_by_admin_unauthorized_non_admin():
    def override_get_current_active_user_normal():
        return mock_user_normal # Non-admin user
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user_normal
    
    response = client.get(f"/llm-usage/user/{mock_user_other.id}/")
    assert response.status_code == 403 # Expecting 403 Forbidden
    
    app.dependency_overrides.pop(get_current_active_user)

def test_read_user_llm_token_usage_by_admin_no_data():
    def override_get_current_active_user_admin():
        return mock_user_admin # Admin user
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user_admin
    
    response = client.get(f"/llm-usage/user/{mock_user_other.id}/") # User has no data
    assert response.status_code == 200
    assert response.json() == []
    
    app.dependency_overrides.pop(get_current_active_user)

def test_read_user_llm_token_usage_by_admin_with_data():
    db = TestingSessionLocal()
    target_user_id = mock_user_other.id
    now = datetime.utcnow()
    entry1 = create_token_usage_entry(db, target_user_id, now - timedelta(days=1), action="action_other1")
    entry2 = create_token_usage_entry(db, target_user_id, now, action="action_other2")
    # Data for the admin user (should not interfere)
    create_token_usage_entry(db, mock_user_admin.id, now, action="action_admin")
    db.close()

    def override_get_current_active_user_admin():
        return mock_user_admin
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user_admin

    response = client.get(f"/llm-usage/user/{target_user_id}/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["action"] == "action_other2" # Ordered by timestamp desc
    assert data[1]["action"] == "action_other1"
    assert data[0]["user_id"] == target_user_id
    
    app.dependency_overrides.pop(get_current_active_user)

def test_read_user_llm_token_usage_by_admin_with_date_filters():
    db = TestingSessionLocal()
    target_user_id = mock_user_other.id
    
    date_minus_2 = datetime(2024, 2, 1, 10, 0, 0) # Feb 1st
    date_minus_1 = datetime(2024, 2, 2, 10, 0, 0) # Feb 2nd
    date_today = datetime(2024, 2, 3, 10, 0, 0)   # Feb 3rd
    
    create_token_usage_entry(db, target_user_id, date_minus_2, action="action_feb1")
    create_token_usage_entry(db, target_user_id, date_minus_1, action="action_feb2")
    create_token_usage_entry(db, target_user_id, date_today, action="action_feb3")
    db.close()

    def override_get_current_active_user_admin():
        return mock_user_admin
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user_admin

    # Filter by start_date and end_date
    response = client.get(f"/llm-usage/user/{target_user_id}/?start_date=2024-02-01&end_date=2024-02-02")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    actions = {item['action'] for item in data}
    assert "action_feb1" in actions
    assert "action_feb2" in actions
    
    app.dependency_overrides.pop(get_current_active_user)
