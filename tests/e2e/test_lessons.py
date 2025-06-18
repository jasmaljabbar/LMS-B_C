import pytest
import requests
from fastapi import status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Assuming your app is defined in backend.main
from backend.main import app
from backend import models

BASE_URL = "http://localhost:8000"  # Adjust if your app runs on a different port

LESSON_ENDPOINT = "/lessons"

# Database URL for testing - Retrieve from environment variable
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "mysql+pymysql://root:a@localhost/cloudnative_lms")

# Create a test database engine and session
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables if they don't exist (optional, but recommended for clean tests)
models.Base.metadata.create_all(bind=engine)

# Utility function to get a token
def get_admin_token():
    login_data = {"username": "admin", "password": "Coimbatore"}  # Replace with actual admin credentials
    response = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    assert response.status_code == status.HTTP_200_OK
    return response.json()["access_token"]

# Fixture for an authenticated client
@pytest.fixture
def authenticated_client():
    token = get_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    return headers  # Return the headers directly

# Fixture to get a database session for testing
@pytest.fixture
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Fixture to get a valid subject ID from the database
@pytest.fixture
def valid_subject_id(db):
    subject = db.query(models.Subject).first()
    if subject:
        return subject.id
    else:
        # If no subjects exist, create one for testing purposes
        grade = db.query(models.Grade).first()
        if not grade:
            new_grade = models.Grade(name="Test Grade")
            db.add(new_grade)
            db.commit()
            db.refresh(new_grade)
            grade_id = new_grade.id
        else:
            grade_id = grade.id

        new_subject = models.Subject(name="Test Subject", grade_id=grade_id)  # Corrected subject creation
        db.add(new_subject)
        db.commit()
        db.refresh(new_subject)
        return new_subject.id

# Sample data
@pytest.fixture
def sample_lesson_create(valid_subject_id):
    return {"name": "Introduction to Lessons", "subject_id": valid_subject_id}

@pytest.fixture
def sample_lesson_update(valid_subject_id):
    return {"name": "Updated Lesson Name", "subject_id": valid_subject_id}

# Fixture to create a lesson and return its ID
@pytest.fixture
def created_lesson_id(authenticated_client, sample_lesson_create):
    response = requests.post(f"{BASE_URL}{LESSON_ENDPOINT}", json=sample_lesson_create, headers=authenticated_client)
    assert response.status_code == status.HTTP_201_CREATED
    lesson = response.json()
    return lesson["id"]

def test_create_lesson(authenticated_client, sample_lesson_create):
    response = requests.post(f"{BASE_URL}{LESSON_ENDPOINT}", json=sample_lesson_create, headers=authenticated_client)
    assert response.status_code == status.HTTP_201_CREATED
    lesson = response.json()
    assert "id" in lesson
    assert lesson["name"] == sample_lesson_create["name"]
    assert lesson["subject_id"] == sample_lesson_create["subject_id"]

def test_create_lesson_invalid_subject_id(authenticated_client):
    invalid_data = {"name": "Invalid Lesson", "subject_id": 9999}
    response = requests.post(f"{BASE_URL}{LESSON_ENDPOINT}", json=invalid_data, headers=authenticated_client)
    assert response.status_code == status.HTTP_400_BAD_REQUEST or response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY #Check validation status code

def test_create_lesson_missing_name(authenticated_client, valid_subject_id):
    invalid_data = {"subject_id": valid_subject_id}
    response = requests.post(f"{BASE_URL}{LESSON_ENDPOINT}", json=invalid_data, headers=authenticated_client)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

def test_read_lesson(authenticated_client, created_lesson_id, sample_lesson_create):
    response = requests.get(f"{BASE_URL}{LESSON_ENDPOINT}/{created_lesson_id}", headers=authenticated_client)
    assert response.status_code == status.HTTP_200_OK
    lesson = response.json()
    assert lesson["id"] == created_lesson_id
    assert lesson["name"] == sample_lesson_create["name"]
    assert lesson["subject_id"] == sample_lesson_create["subject_id"]

def test_read_lesson_not_found(authenticated_client):
    response = requests.get(f"{BASE_URL}{LESSON_ENDPOINT}/9999", headers=authenticated_client)
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_read_lessons(authenticated_client, sample_lesson_create):
    # Create a lesson first to ensure there's something to read
    requests.post(f"{BASE_URL}{LESSON_ENDPOINT}", json=sample_lesson_create, headers=authenticated_client)

    response = requests.get(f"{BASE_URL}{LESSON_ENDPOINT}", headers=authenticated_client)
    assert response.status_code == status.HTTP_200_OK
    lessons = response.json()
    assert isinstance(lessons, list)
    assert len(lessons) > 0

def test_update_lesson(authenticated_client, created_lesson_id, sample_lesson_update):
    response = requests.put(f"{BASE_URL}{LESSON_ENDPOINT}/{created_lesson_id}", json=sample_lesson_update, headers=authenticated_client)
    assert response.status_code == status.HTTP_200_OK
    updated_lesson = response.json()
    assert updated_lesson["id"] == created_lesson_id
    assert updated_lesson["name"] == sample_lesson_update["name"]
    assert updated_lesson["subject_id"] == sample_lesson_update["subject_id"]

def test_update_lesson_invalid_subject_id(authenticated_client, created_lesson_id):
    invalid_data = {"name": "Invalid Update", "subject_id": 9999}
    response = requests.put(f"{BASE_URL}{LESSON_ENDPOINT}/{created_lesson_id}", json=invalid_data, headers=authenticated_client)
    assert response.status_code == status.HTTP_400_BAD_REQUEST or response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY #Check validation status code

def test_delete_lesson(authenticated_client, created_lesson_id):
    response = requests.delete(f"{BASE_URL}{LESSON_ENDPOINT}/{created_lesson_id}", headers=authenticated_client)
    assert response.status_code == status.HTTP_204_NO_CONTENT

    # Verify that the lesson is actually deleted
    response = requests.get(f"{BASE_URL}{LESSON_ENDPOINT}/{created_lesson_id}", headers=authenticated_client)
    assert response.status_code == status.HTTP_404_NOT_FOUND